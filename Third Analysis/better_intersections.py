import csv
import math
import numpy as np
import cv2
from PIL import Image

img = np.array(Image.open(r'20260917_175649_masked.png').convert('RGB'))
H, W = img.shape[:2]
R, G, B = img[:, :, 0], img[:, :, 1], img[:, :, 2]

def cluster_sorted(vals, tol):
    if not vals:
        return []
    vals = sorted(float(v) for v in vals)
    groups = []
    cur = [vals[0]]
    for v in vals[1:]:
        if abs(v - cur[-1]) <= tol:
            cur.append(v)
        else:
            groups.append(cur)
            cur = [v]
    groups.append(cur)
    return [float(np.median(g)) for g in groups]

# Grid line detection using blue hue dominance.
grid = ((B > G + 10) & (B > R + 10) & (B > 120)).astype(np.uint8)
grid = cv2.morphologyEx(grid, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
lines = cv2.HoughLinesP(grid, 1, np.pi / 180, threshold=35, minLineLength=80, maxLineGap=10)

x_lines = []
y_lines = []
if lines is not None:
    for candidate in lines:
        line = candidate[0] if candidate.ndim == 2 else candidate
        if len(line) < 4:
            continue
        x1, y1, x2, y2 = [int(v) for v in line[:4]]
        length = math.hypot(x2 - x1, y2 - y1)
        if length < 30:
            continue
        if abs(y2 - y1) < 0.25 * abs(x2 - x1):
            y_lines.append((y1 + y2) / 2.0)
        elif abs(x2 - x1) < 0.25 * abs(y2 - y1):
            x_lines.append((x1 + x2) / 2.0)

x_lines = cluster_sorted(x_lines, tol=10)
y_lines = cluster_sorted(y_lines, tol=10)

# Keep the regular lattice by using the median spacing and removing lines that are too sparse.
if len(x_lines) > 1:
    x_d = np.median(np.diff(np.sort(x_lines)))
else:
    x_d = 28.0
if len(y_lines) > 1:
    y_d = np.median(np.diff(np.sort(y_lines)))
else:
    y_d = 28.0

cell = float(np.median([x_d, y_d]))
print('x_lines', len(x_lines), 'y_lines', len(y_lines), 'cell', cell)
print('x first/last', x_lines[:10], x_lines[-10:])
print('y first/last', y_lines[:10], y_lines[-10:])

# Path mask: dark gray pixels minus grid.
path = ((R < 220) & (G < 220) & (B < 220)).astype(np.uint8)
path = cv2.bitwise_and(path, cv2.bitwise_not(grid))
path = cv2.morphologyEx(path, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))

# Intersections: for each grid line, find pixels of path on that line and convert to grid coordinates.
out = []
# Use the first detected vertical or horizontal line as origin.
# x index: based on x_lines order
x_sorted = np.sort(x_lines)
y_sorted = np.sort(y_lines)

# vertical intersections: store (x_idx, y_coord)
for idx, x0 in enumerate(x_sorted):
    xs = max(0, int(round(x0)) - 2)
    xe = min(W, int(round(x0)) + 3)
    linevals = path[:, xs:xe].sum(axis=1) > 0
    ys = np.where(linevals)[0]
    if len(ys) == 0:
        continue
    # group continuous runs of path pixels on this line
    starts = [0]
    for i in range(1, len(ys)):
        if ys[i] - ys[i - 1] > 2:
            starts.append(i)
    segments = []
    for j in range(len(starts)):
        s = starts[j]
        e = len(ys) if j == len(starts) - 1 else starts[j + 1]
        segments.append((ys[s], ys[e - 1]))
    for y0, y1 in segments:
        ymid = 0.5 * (y0 + y1)
        # horizontal line interpolation using nearest horizontal grid lines
        if len(y_sorted) >= 2:
            lower = y_sorted[y_sorted <= ymid][-1]
            upper = y_sorted[y_sorted >= ymid][0]
            if upper == lower:
                frac = 0.0
            else:
                frac = (ymid - lower) / (upper - lower)
            y_idx = np.where(y_sorted == lower)[0][0]
            y_coord = y_idx + frac
            x_coord = idx
        else:
            y_coord = (ymid - y_sorted[0]) / cell
            x_coord = idx
        out.append((x_coord, y_coord))

# horizontal intersections: store (x_coord, y_idx)
for jdx, y0 in enumerate(y_sorted):
    ys = max(0, int(round(y0)) - 2)
    ye = min(H, int(round(y0)) + 3)
    linevals = path[ys:ye, :].sum(axis=0) > 0
    xs = np.where(linevals)[0]
    if len(xs) == 0:
        continue
    starts = [0]
    for i in range(1, len(xs)):
        if xs[i] - xs[i - 1] > 2:
            starts.append(i)
    segments = []
    for j in range(len(starts)):
        s = starts[j]
        e = len(xs) if j == len(starts) - 1 else starts[j + 1]
        segments.append((xs[s], xs[e - 1]))
    for x0, x1 in segments:
        xmid = 0.5 * (x0 + x1)
        if len(x_sorted) >= 2:
            lower = x_sorted[x_sorted <= xmid][-1]
            upper = x_sorted[x_sorted >= xmid][0]
            if upper == lower:
                frac = 0.0
            else:
                frac = (xmid - lower) / (upper - lower)
            x_idx = np.where(x_sorted == lower)[0][0]
            x_coord = x_idx + frac
            y_coord = jdx
        else:
            x_coord = (xmid - x_sorted[0]) / cell
            y_coord = jdx
        out.append((x_coord, y_coord))

# Deduplicate near-identical candidates
uniq = []
for pt in out:
    found = False
    for q in uniq:
        if abs(pt[0] - q[0]) < 0.25 and abs(pt[1] - q[1]) < 0.25:
            found = True
            break
    if not found:
        uniq.append(pt)

print('num candidates', len(out), 'uniq', len(uniq))
for i, p in enumerate(sorted(uniq)[:20]):
    print(i, p)

with open('20260917_175649_intersections_test.csv', 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['x', 'y'])
    for p in sorted(uniq):
        w.writerow(p)
print('saved', '20260917_175649_intersections_test.csv')
