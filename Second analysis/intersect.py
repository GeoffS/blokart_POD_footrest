"""Find the points where the extracted path polyline crosses the grid
lines, using LOCAL interpolation between only the nearest bracketing
grid lines at each crossing (as requested), rather than a single global
homography. Writes intersections.csv.
"""
import numpy as np
import csv

grid = np.load("grid_lines.npz", allow_pickle=True)
vcoefs = grid["vcoefs"]   # x(y) polynomials, one per vertical line
hcoefs = grid["hcoefs"]   # y(x) polynomials, one per horizontal line
vindex = grid["vindex"]
hindex = grid["hindex"]

chain = np.load("path_polyline.npy")  # (x,y) pixel points, ordered


def resample_and_smooth(chain, step=4.0, smooth_win=11):
    d = np.hypot(np.diff(chain[:, 0]), np.diff(chain[:, 1]))
    s = np.concatenate([[0], np.cumsum(d)])
    total = s[-1]
    n = int(total // step)
    snew = np.linspace(0, total, n)
    xnew = np.interp(snew, s, chain[:, 0])
    ynew = np.interp(snew, s, chain[:, 1])
    if smooth_win > 1:
        k = np.ones(smooth_win) / smooth_win
        pad = smooth_win // 2
        xpad = np.pad(xnew, pad, mode="edge")
        ypad = np.pad(ynew, pad, mode="edge")
        xnew = np.convolve(xpad, k, mode="valid")
        ynew = np.convolve(ypad, k, mode="valid")
    return np.stack([xnew, ynew], axis=1)


def col_row_at(x, y):
    """Local bracketing interpolation: col from the two nearest vertical
    lines (by x at this y), row from the two nearest horizontal lines
    (by y at this x)."""
    vx = np.array([np.polyval(c, y) for c in vcoefs])
    order = np.argsort(vx)
    vx_s = vx[order]
    vidx_s = vindex[order]
    j = np.searchsorted(vx_s, x)
    j = np.clip(j, 1, len(vx_s) - 1)
    x_left, x_right = vx_s[j - 1], vx_s[j]
    i_left, i_right = vidx_s[j - 1], vidx_s[j]
    frac = (x - x_left) / (x_right - x_left) if x_right != x_left else 0.0
    col = i_left + frac * (i_right - i_left)

    hy = np.array([np.polyval(c, x) for c in hcoefs])
    order2 = np.argsort(hy)
    hy_s = hy[order2]
    hidx_s = hindex[order2]
    k = np.searchsorted(hy_s, y)
    k = np.clip(k, 1, len(hy_s) - 1)
    y_top, y_bot = hy_s[k - 1], hy_s[k]
    it, ib = hidx_s[k - 1], hidx_s[k]
    fracy = (y - y_top) / (y_bot - y_top) if y_bot != y_top else 0.0
    row = it + fracy * (ib - it)
    return col, row


def main():
    pts = resample_and_smooth(chain)
    print("resampled points:", len(pts))

    cols = np.empty(len(pts))
    rows = np.empty(len(pts))
    for i, (x, y) in enumerate(pts):
        c, r = col_row_at(x, y)
        cols[i] = c
        rows[i] = r

    crossings = []  # (pixel_x, pixel_y, col, row, kind)
    # Schmitt-trigger style hysteresis to avoid chattering when the path
    # runs nearly parallel/along a grid line (pixel-level noise would
    # otherwise register many spurious back-and-forth crossings there).
    margin = 0.15
    cur_col_cell = np.floor(cols[0])
    cur_row_cell = np.floor(rows[0])
    for i in range(len(pts) - 1):
        c0, c1 = cols[i], cols[i + 1]
        r0, r1 = rows[i], rows[i + 1]
        events = []
        if c1 > cur_col_cell + 1 + margin:
            target = cur_col_cell + 1
            t = (target - c0) / (c1 - c0) if c1 != c0 else 0.0
            events.append((t, "col", target))
            cur_col_cell += 1
        elif c1 < cur_col_cell - margin:
            target = cur_col_cell
            t = (target - c0) / (c1 - c0) if c1 != c0 else 0.0
            events.append((t, "col", target))
            cur_col_cell -= 1
        if r1 > cur_row_cell + 1 + margin:
            target = cur_row_cell + 1
            t = (target - r0) / (r1 - r0) if r1 != r0 else 0.0
            events.append((t, "row", target))
            cur_row_cell += 1
        elif r1 < cur_row_cell - margin:
            target = cur_row_cell
            t = (target - r0) / (r1 - r0) if r1 != r0 else 0.0
            events.append((t, "row", target))
            cur_row_cell -= 1
        for t, kind, target in events:
            if not (0 <= t <= 1):
                t = min(max(t, 0.0), 1.0)
            x = pts[i, 0] + t * (pts[i + 1, 0] - pts[i, 0])
            y = pts[i, 1] + t * (pts[i + 1, 1] - pts[i, 1])
            c = cols[i] + t * (cols[i + 1] - cols[i])
            r = rows[i] + t * (rows[i + 1] - rows[i])
            crossings.append((x, y, c, r, kind))

    # merge near-duplicate crossings (corner: col & row cross almost together)
    merged = []
    for cr in crossings:
        if merged and np.hypot(cr[0] - merged[-1][0], cr[1] - merged[-1][1]) < 6:
            continue
        merged.append(cr)

    print("num crossings:", len(merged))
    with open("intersections.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["seq", "pixel_x", "pixel_y", "grid_col", "grid_row", "crossing_type"])
        for i, (x, y, c, r, kind) in enumerate(merged):
            w.writerow([i, f"{x:.1f}", f"{y:.1f}", f"{c:.3f}", f"{r:.3f}", kind])

    import cv2
    im = cv2.imread("20260917_175649.jpg")
    for (x, y, c, r, kind) in merged:
        color = (0, 0, 255) if kind == "col" else (255, 0, 0)
        cv2.circle(im, (int(x), int(y)), 6, color, -1)
    cv2.imwrite("dbg_crossings.png", im)


if __name__ == "__main__":
    main()
