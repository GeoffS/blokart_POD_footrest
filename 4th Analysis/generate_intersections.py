"""
End-to-end pipeline: detect the graph-paper grid lines in the unmasked photo,
extract the traced pencil path from the masked photo, and compute the
grid-unit coordinates of every point where the path crosses a grid line.

Usage:
    .venv\\Scripts\\python.exe generate_intersections.py

Outputs:
    intersections.csv           - one row per detected crossing: x,y (grid units)
    debug_crossings_overlay.png - the unmasked photo with detected crossings marked,
                                   for visual verification.

Method summary
--------------
1. Grid calibration (from the unmasked PNG):
   - Grid lines are light-blue; a "blueness" channel (B-R) isolates them from the
     gray pencil path.
   - A white top-hat removes the thicker pencil path, leaving only the thin grid
     mesh.
   - The image is divided into bands (horizontal bands for vertical lines,
     vertical bands for horizontal lines). In each band, a 1-D peak search finds
     the pixel position of every grid line crossing that band.
   - Each physical grid line is tracked band-to-band (nearest-neighbour match) to
     assign it a single, consistent integer index, and a piecewise-linear
     lookup table is built giving that line's pixel position as a function of
     position along the band direction. This tolerates the camera's rotation and
     mild perspective distortion without assuming a single global transform.
2. Path extraction (from the masked PNG):
   - A black top-hat highlights the pencil stroke's local contrast against the
     paper regardless of absolute brightness, and blue grid-line pixels are
     excluded.
   - Small grid-crossing gaps are closed, the result is skeletonized to a 1px
     wide curve, and each connected fragment is ordered into a polyline by
     nearest-neighbour chaining. Small stray marks (bounding box smaller than
     one grid cell) are discarded.
3. Every ordered polyline is mapped through the grid calibration to continuous
   (column, row) grid coordinates, and each point where a coordinate crosses an
   integer value is recorded as an intersection: the crossed coordinate is
   exact (integer), the other is linearly interpolated between the two nearest
   path samples.
"""
import csv
import pickle
from pathlib import Path

import cv2
import numpy as np
from scipy.signal import find_peaks
from scipy.spatial import cKDTree
from skimage.morphology import skeletonize

BASE = Path(__file__).resolve().parent
PNG_PATH = BASE / "20260917_175649.png"
MASKED_PATH = BASE / "20260917_175649_masked.png"
OUT_CSV = BASE / "intersections.csv"
OUT_OVERLAY = BASE / "debug_crossings_overlay.png"

BAND = 100          # px, size of each calibration band
MIN_DIST = 35        # px, minimum spacing between detected grid-line peaks
TOL = 25.0            # px, band-to-band line-tracking match tolerance
MIN_COMPONENT_PX = 30  # minimum skeleton fragment size to consider
MIN_COMPONENT_SPAN = 55  # px, minimum bounding-box span to avoid stray tick marks


# ---------------------------------------------------------------------------
# 1. Grid calibration
# ---------------------------------------------------------------------------
def detect_peaks_in_bands(mask, axis):
    H, W = mask.shape
    bands = []
    if axis == 1:  # horizontal bands -> vertical line x positions
        n = H // BAND
        for k in range(n):
            y0, y1 = k * BAND, min((k + 1) * BAND, H)
            prof = mask[y0:y1, :].sum(axis=0)
            peaks, _ = find_peaks(prof, distance=MIN_DIST, height=BAND * 0.15)
            refined = []
            for p in peaks:
                lo, hi = max(0, p - 4), min(W, p + 5)
                w = prof[lo:hi]
                cx = (np.arange(lo, hi) * w).sum() / w.sum() if w.sum() > 0 else p
                refined.append(cx)
            bands.append(((y0 + y1) / 2, np.array(sorted(refined))))
    else:  # vertical bands -> horizontal line y positions
        n = W // BAND
        for k in range(n):
            x0, x1 = k * BAND, min((k + 1) * BAND, W)
            prof = mask[:, x0:x1].sum(axis=1)
            peaks, _ = find_peaks(prof, distance=MIN_DIST, height=BAND * 0.15)
            refined = []
            for p in peaks:
                lo, hi = max(0, p - 4), min(H, p + 5)
                w = prof[lo:hi]
                cy = (np.arange(lo, hi) * w).sum() / w.sum() if w.sum() > 0 else p
                refined.append(cy)
            bands.append(((x0 + x1) / 2, np.array(sorted(refined))))
    return bands


def track_indices(bands):
    result = []
    prev_positions = None
    prev_indices = None
    for center, positions in bands:
        positions = np.asarray(positions)
        if prev_positions is None or len(prev_positions) == 0:
            idxs = list(range(len(positions)))
        else:
            idxs = [None] * len(positions)
            used_prev = set()
            for i, x in enumerate(positions):
                diffs = np.abs(prev_positions - x)
                j = int(np.argmin(diffs))
                if diffs[j] < TOL and j not in used_prev:
                    idxs[i] = prev_indices[j]
                    used_prev.add(j)
            known = [(i, idxs[i]) for i in range(len(idxs)) if idxs[i] is not None]
            if known:
                i0, k0 = known[0]
                for i in range(len(idxs)):
                    if idxs[i] is None:
                        idxs[i] = k0 + (i - i0)
            else:
                idxs = list(range(len(positions)))
        result.append((center, positions, np.array(idxs)))
        prev_positions = positions
        prev_indices = idxs
    return result


def build_lut(tracked):
    lut = {}
    for center, vals, idxs in tracked:
        for v, idx in zip(vals, idxs):
            lut.setdefault(int(idx), []).append((center, v))
    for idx in lut:
        pts = sorted(lut[idx])
        lut[idx] = (np.array([p[0] for p in pts]), np.array([p[1] for p in pts]))
    return lut


def calibrate_grid(png):
    b = png[..., 0].astype(np.int16)
    r = png[..., 2].astype(np.int16)
    blueness = np.clip(b - r, 0, 255).astype(np.uint8)

    th_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    opened = cv2.morphologyEx(blueness, cv2.MORPH_OPEN, th_kernel)
    tophat = cv2.subtract(blueness, opened)
    grid_mask = (tophat > 6).astype(np.float32)

    v_bands = detect_peaks_in_bands(grid_mask, axis=1)
    h_bands = detect_peaks_in_bands(grid_mask, axis=0)
    v_tracked = track_indices(v_bands)
    h_tracked = track_indices(h_bands)
    v_lut = build_lut(v_tracked)  # vertical line idx -> (y_centers, x_positions)
    h_lut = build_lut(h_tracked)  # horizontal line idx -> (x_centers, y_positions)
    return v_lut, h_lut


def to_grid(px, py, v_lut, h_lut):
    """Map a pixel coordinate to continuous (col, row) grid-unit coordinates."""
    xs = []
    for idx, (centers, vals) in v_lut.items():
        if len(centers) == 0 or py < centers.min() - 150 or py > centers.max() + 150:
            continue
        xs.append((idx, np.interp(py, centers, vals)))
    xs.sort(key=lambda t: t[1])
    frac_col = _bracket(px, xs)

    ys = []
    for idx, (centers, vals) in h_lut.items():
        if len(centers) == 0 or px < centers.min() - 150 or px > centers.max() + 150:
            continue
        ys.append((idx, np.interp(px, centers, vals)))
    ys.sort(key=lambda t: t[1])
    frac_row = _bracket(py, ys)
    return frac_col, frac_row


def _bracket(value, indexed_positions):
    """Given [(index, position), ...] sorted by position, return the fractional
    index corresponding to `value` via linear interpolation/extrapolation."""
    pts = indexed_positions
    if len(pts) < 2:
        return None
    for k in range(len(pts) - 1):
        i0, x0 = pts[k]
        i1, x1 = pts[k + 1]
        if x0 <= value <= x1 and x1 > x0:
            return i0 + (value - x0) / (x1 - x0)
    if value < pts[0][1]:
        i0, x0 = pts[0]
        i1, x1 = pts[1]
    else:
        i0, x0 = pts[-2]
        i1, x1 = pts[-1]
    return i0 + (value - x0) / (x1 - x0)


# ---------------------------------------------------------------------------
# 2. Path extraction
# ---------------------------------------------------------------------------
def extract_path_mask(masked):
    b = masked[..., 0].astype(np.int16)
    g = masked[..., 1].astype(np.int16)
    r = masked[..., 2].astype(np.int16)
    blueness = b - r
    gray_u8 = np.clip((b.astype(np.float32) + g + r) / 3, 0, 255).astype(np.uint8)

    bth_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (21, 21))
    closed_gray = cv2.morphologyEx(gray_u8, cv2.MORPH_CLOSE, bth_kernel)
    black_tophat = cv2.subtract(closed_gray, gray_u8)

    not_blue = blueness < 12
    dark_contrast = black_tophat > 15
    path_mask = (dark_contrast & not_blue).astype(np.uint8) * 255

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    path_mask = cv2.morphologyEx(path_mask, cv2.MORPH_OPEN, kernel)
    close_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (21, 21))
    path_mask = cv2.morphologyEx(path_mask, cv2.MORPH_CLOSE, close_kernel)
    return path_mask


def order_component(coords):
    """coords: (N,2) array of (y,x). Order into a polyline via nearest-neighbour chaining."""
    n_pts = len(coords)
    if n_pts <= 2:
        return coords
    tree = cKDTree(coords)
    neighbour_counts = tree.query_ball_point(coords, r=1.5, return_length=True)
    start = int(np.argmin(neighbour_counts))
    visited = np.zeros(n_pts, dtype=bool)
    order = [start]
    visited[start] = True
    current = start
    for _ in range(n_pts - 1):
        dists, idxs = tree.query(coords[current], k=min(9, n_pts))
        idxs = np.atleast_1d(idxs)
        nxt = None
        for i in idxs:
            if i != current and not visited[i]:
                nxt = i
                break
        if nxt is None:
            remaining = np.where(~visited)[0]
            if len(remaining) == 0:
                break
            rdists = np.linalg.norm(coords[remaining] - coords[current], axis=1)
            nxt = remaining[np.argmin(rdists)]
        order.append(nxt)
        visited[nxt] = True
        current = nxt
    return coords[order]


# ---------------------------------------------------------------------------
# 3. Crossing detection
# ---------------------------------------------------------------------------
def find_crossings(path_mask, v_lut, h_lut):
    skel = skeletonize(path_mask > 0)
    skel_u8 = skel.astype(np.uint8) * 255
    n, labels = cv2.connectedComponents(skel_u8, connectivity=8)

    crossings = []  # (col, row, px, py)
    for comp_id in range(1, n):
        ys, xs_ = np.where(labels == comp_id)
        if len(ys) < MIN_COMPONENT_PX:
            continue
        if max(xs_.max() - xs_.min(), ys.max() - ys.min()) < MIN_COMPONENT_SPAN:
            continue  # stray tick-mark / annotation remnant, not the traced path

        coords = np.stack([ys, xs_], axis=1).astype(np.float64)
        ordered = order_component(coords)

        grid_pts = []
        for y, x in ordered:
            fc, fr = to_grid(x, y, v_lut, h_lut)
            grid_pts.append((fc, fr, x, y))

        for k in range(len(grid_pts) - 1):
            fc0, fr0, px0, py0 = grid_pts[k]
            fc1, fr1, px1, py1 = grid_pts[k + 1]
            if None in (fc0, fc1, fr0, fr1):
                continue

            lo_col, hi_col = sorted((fc0, fc1))
            if fc1 != fc0:
                for i in range(int(np.floor(lo_col)) + 1, int(np.ceil(hi_col))):
                    t = (i - fc0) / (fc1 - fc0)
                    if 0 <= t <= 1:
                        row_i = fr0 + t * (fr1 - fr0)
                        crossings.append((float(i), float(row_i),
                                           px0 + t * (px1 - px0), py0 + t * (py1 - py0)))

            lo_row, hi_row = sorted((fr0, fr1))
            if fr1 != fr0:
                for j in range(int(np.floor(lo_row)) + 1, int(np.ceil(hi_row))):
                    t = (j - fr0) / (fr1 - fr0)
                    if 0 <= t <= 1:
                        col_i = fc0 + t * (fc1 - fc0)
                        crossings.append((float(col_i), float(j),
                                           px0 + t * (px1 - px0), py0 + t * (py1 - py0)))

    # de-duplicate near-identical crossings (within 0.05 grid units)
    dedup = []
    for c in crossings:
        if not any(abs(c[0] - d[0]) < 0.05 and abs(c[1] - d[1]) < 0.05 for d in dedup):
            dedup.append(c)
    return dedup


# ---------------------------------------------------------------------------
def main():
    png = cv2.imread(str(PNG_PATH), cv2.IMREAD_COLOR)
    masked = cv2.imread(str(MASKED_PATH), cv2.IMREAD_COLOR)

    print("Calibrating grid from", PNG_PATH.name, "...")
    v_lut, h_lut = calibrate_grid(png)
    print(f"  {len(v_lut)} vertical lines, {len(h_lut)} horizontal lines detected.")

    print("Extracting path from", MASKED_PATH.name, "...")
    path_mask = extract_path_mask(masked)

    print("Finding grid-line crossings along the path...")
    crossings = find_crossings(path_mask, v_lut, h_lut)
    print(f"  {len(crossings)} intersections found.")

    with open(OUT_CSV, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["x", "y"])
        for c in sorted(crossings, key=lambda t: (t[0], t[1])):
            w.writerow([round(c[0], 3), round(c[1], 3)])
    print("Wrote", OUT_CSV)

    vis = png.copy()
    for c in crossings:
        cv2.circle(vis, (int(round(c[2])), int(round(c[3]))), 6, (0, 0, 255), -1)
    cv2.imwrite(str(OUT_OVERLAY), vis)
    print("Wrote", OUT_OVERLAY)


if __name__ == "__main__":
    main()
