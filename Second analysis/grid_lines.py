"""Detect grid lines on the full original photo using band-wise peak
tracking (robust to the mild perspective curvature), then fit a smooth
polynomial per line: x(y) for vertical lines, y(x) for horizontal lines.
Saves the fitted lines to grid_lines.npz for later use.
"""
import cv2
import numpy as np
from scipy.signal import find_peaks

ORIG = "20260917_175649.jpg"
SPACING = 57.0  # approx grid spacing in px, from earlier analysis


def grid_mask(im):
    im = im.astype(np.int16)
    B, G, R = im[:, :, 0], im[:, :, 1], im[:, :, 2]
    diff = B - R
    mask = (diff > 10).astype(np.uint8) * 255
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    return mask


def track_lines(mask, axis, band=75, match_tol=20, min_pts=8):
    """axis='v' -> vertical lines, tracked across horizontal bands (rows).
    axis='h' -> horizontal lines, tracked across vertical bands (cols)."""
    H, W = mask.shape
    if axis == 'v':
        n_bands = H // band
        def get_profile(b0, b1):
            return (mask[b0:b1, :] > 0).sum(axis=0).astype(float)
    else:
        n_bands = W // band
        def get_profile(b0, b1):
            return (mask[:, b0:b1] > 0).sum(axis=1).astype(float)

    tracks = []  # each: list of (center, peak_pos)
    active = []  # list of (track_index, last_peak)

    for bi in range(n_bands):
        b0, b1 = bi * band, (bi + 1) * band
        center = (b0 + b1) / 2.0
        profile = get_profile(b0, b1)
        maxval = profile.max()
        if maxval < band * 0.15:
            continue
        peaks, _ = find_peaks(profile, height=maxval * 0.35, distance=int(SPACING * 0.55))
        used = set()
        new_active = []
        for ti, last_peak in active:
            cand = [(abs(p - last_peak), p) for p in peaks if p not in used]
            cand.sort()
            if cand and cand[0][0] <= match_tol:
                p = cand[0][1]
                used.add(p)
                tracks[ti].append((center, p))
                new_active.append((ti, p))
            else:
                new_active.append((ti, last_peak))  # keep alive across gap
        active = new_active
        for p in peaks:
            if p not in used:
                tracks.append([(center, p)])
                active.append((len(tracks) - 1, p))

    fits = []
    for tr in tracks:
        if len(tr) < min_pts:
            continue
        arr = np.array(tr)
        c, p = arr[:, 0], arr[:, 1]
        deg = 2 if len(tr) >= 12 else 1
        coef = np.polyfit(c, p, deg)
        fits.append({"coef": coef, "n": len(tr), "cmin": c.min(), "cmax": c.max(),
                     "pmean": p.mean()})
    fits.sort(key=lambda d: d["pmean"])
    return fits


def merge_and_index(fits, spacing):
    """Merge near-duplicate line tracks and assign integer grid indices,
    allowing for the occasional undetected line (larger gap -> skip index)."""
    fits = sorted(fits, key=lambda d: d["pmean"])
    merged = [fits[0]]
    for f in fits[1:]:
        if f["pmean"] - merged[-1]["pmean"] < spacing * 0.6:
            # duplicate/spurious split -> keep the one with more support
            if f["n"] > merged[-1]["n"]:
                merged[-1] = f
        else:
            merged.append(f)
    idx = 0
    merged[0]["index"] = idx
    for prev, cur in zip(merged, merged[1:]):
        gap = cur["pmean"] - prev["pmean"]
        step = max(1, round(gap / spacing))
        idx += step
        cur["index"] = idx
    return merged


def main():
    im = cv2.imread(ORIG)
    mask = grid_mask(im)
    H, W = mask.shape

    vfits = track_lines(mask, 'v')
    hfits = track_lines(mask, 'h')
    print("vertical lines found (raw):", len(vfits))
    print("horizontal lines found (raw):", len(hfits))

    vfits = merge_and_index(vfits, SPACING)
    hfits = merge_and_index(hfits, SPACING)
    print("vertical lines (merged):", len(vfits))
    print("horizontal lines (merged):", len(hfits))
    print("v indices", [f["index"] for f in vfits])
    print("h indices", [f["index"] for f in hfits])

    vmeans = [f["pmean"] for f in vfits]
    hmeans = [f["pmean"] for f in hfits]
    print("v spacing", np.diff(vmeans))
    print("h spacing", np.diff(hmeans))

    np.savez("grid_lines.npz",
             vcoefs=np.array([f["coef"] for f in vfits], dtype=object),
             hcoefs=np.array([f["coef"] for f in hfits], dtype=object),
             vindex=np.array([f["index"] for f in vfits]),
             hindex=np.array([f["index"] for f in hfits]),
             allow_pickle=True)

    vis = im.copy()
    ys = np.linspace(0, H - 1, 200)
    for f in vfits:
        xs = np.polyval(f["coef"], ys)
        for x, y in zip(xs, ys):
            if 0 <= x < W:
                cv2.circle(vis, (int(x), int(y)), 2, (0, 0, 255), -1)
        xm, ym = np.polyval(f["coef"], H / 2), H / 2
        cv2.putText(vis, str(f["index"]), (int(xm), int(ym)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    xs2 = np.linspace(0, W - 1, 200)
    for f in hfits:
        ysf = np.polyval(f["coef"], xs2)
        for x, y in zip(xs2, ysf):
            if 0 <= y < H:
                cv2.circle(vis, (int(x), int(y)), 2, (0, 255, 0), -1)
        xm2, ym2 = W / 2, np.polyval(f["coef"], W / 2)
        cv2.putText(vis, str(f["index"]), (int(xm2), int(ym2)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    cv2.imwrite("dbg_fitted_lines.png", vis)


if __name__ == "__main__":
    main()

