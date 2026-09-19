import csv
import numpy as np
import cv2
from PIL import Image, ImageDraw
from skimage.morphology import skeletonize

# 1) Rectify the original photo to a front-parallel paper plane.
orig = cv2.imread(r'20260917_175649.jpg')
source = np.array([
    [150, 150],
    [3850, 180],
    [120, 2860],
    [3920, 2885],
], dtype=np.float32)
W, H = 1200, 900
dest = np.array([
    [0, 0],
    [W - 1, 0],
    [0, H - 1],
    [W - 1, H - 1],
], dtype=np.float32)
M = cv2.getPerspectiveTransform(source, dest)
rect = cv2.warpPerspective(orig, M, (W, H))

# 2) Build grid and path masks in rectified image.
B = rect[:, :, 0]
G = rect[:, :, 1]
R = rect[:, :, 2]
blue = ((B > 100) & (G > 120) & (R < 200)).astype(np.uint8)
blue = cv2.morphologyEx(blue, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
blue = cv2.morphologyEx(blue, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
path = ((R < 220) & (G < 220) & (B < 220)).astype(np.uint8)
path = cv2.bitwise_and(path, cv2.bitwise_not(blue))
path = cv2.morphologyEx(path, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
path = cv2.morphologyEx(path, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))

# 3) Detect grid lines using repeated peaks in the blue mask projections.
def strong_peaks(signal, min_val=18, gap=10):
    peaks = []
    for i in range(1, len(signal) - 1):
        if signal[i] >= signal[i - 1] and signal[i] >= signal[i + 1] and signal[i] > min_val:
            if not peaks or abs(i - peaks[-1]) > gap:
                peaks.append(i)
    return peaks

x_lines = strong_peaks(blue.sum(axis=0), min_val=25, gap=15)
y_lines = strong_peaks(blue.sum(axis=1), min_val=25, gap=15)
# keep only the lines most likely to be actual grid lines in the page interior
x_lines = sorted(set(x_lines))
y_lines = sorted(set(y_lines))

# 4) Skeletonize the path and form a graph from adjacent skeleton pixels.
sk = skeletonize(path > 0).astype(np.uint8)
# Build set of all skeleton edges: adjacent pair of pixels
edges = set()
for y in range(sk.shape[0]):
    for x in range(sk.shape[1]):
        if not sk[y, x]:
            continue
        for dx, dy in [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < sk.shape[1] and 0 <= ny < sk.shape[0] and sk[ny, nx]:
                a = (x, y)
                b = (nx, ny)
                if a < b:
                    edges.add((a, b))
                else:
                    edges.add((b, a))

# 5) For each segment, detect whether it crosses a vertical or horizontal grid line.
#    Keep one crossing per line per segment, then dedupe by a tight tolerance.
true_points = []

for (x1, y1), (x2, y2) in edges:
    # Vertical line crossings.
    for xg in x_lines:
        x_min, x_max = sorted((float(x1), float(x2)))
        if not (x_min <= xg <= x_max):
            continue
        # If the segment is nearly vertical, it may be exactly on the line; skip those cases.
        if abs(x2 - x1) < 1e-6:
            continue
        y_cross = y1 + (xg - x1) * (y2 - y1) / (x2 - x1)
        # Accept only if crossing point is within the endpoint range of the segment.
        if min(y1, y2) - 1 <= y_cross <= max(y1, y2) + 1:
            true_points.append((xg, y_cross, 'V'))
    # Horizontal line crossings.
    for yg in y_lines:
        y_min, y_max = sorted((float(y1), float(y2)))
        if not (y_min <= yg <= y_max):
            continue
        if abs(y2 - y1) < 1e-6:
            continue
        x_cross = x1 + (yg - y1) * (x2 - x1) / (y2 - y1)
        if min(x1, x2) - 1 <= x_cross <= max(x1, x2) + 1:
            true_points.append((x_cross, yg, 'H'))

# 6) Deduplicate by a small proximity threshold in rectified image space.
clean = []
for p in true_points:
    x, y, kind = p
    if all(abs(x - q[0]) > 2 or abs(y - q[1]) > 2 for q in clean):
        clean.append((x, y, kind))

# 7) Convert rectified image coordinates to grid-unit coordinates.
#    Each grid line gets an integer index according to its order in the rectified plane.
#    One component is integer (line index), the other interpolated between neighboring lines.
#    We use the sorted grid-line positions to index them.

def grid_coord_from_line(line_positions, value):
    arr = np.asarray(line_positions, dtype=float)
    if len(arr) == 0:
        return 0.0
    # find nearest lower and upper lines
    lo = arr[arr <= value]
    hi = arr[arr >= value]
    if len(lo) == 0:
        return float(np.argmin(np.abs(arr - value)))
    if len(hi) == 0:
        return float(len(arr) - 1)
    lo_val = float(lo[-1])
    hi_val = float(hi[0])
    lo_idx = int(np.where(arr == lo_val)[0][0])
    hi_idx = int(np.where(arr == hi_val)[0][0])
    if hi_val == lo_val:
        return float(lo_idx)
    frac = (value - lo_val) / (hi_val - lo_val)
    return float(lo_idx) + frac

arr_x = np.array(x_lines, dtype=float)
arr_y = np.array(y_lines, dtype=float)

final = []
for x, y, kind in clean:
    if kind == 'V':
        # x is on a vertical line; use x-grid index integer, y interpolated by nearby horizontal lines
        x_idx = int(np.argmin(np.abs(arr_x - x)))
        y_lo = arr_y[arr_y <= y]
        y_hi = arr_y[arr_y >= y]
        if len(y_lo) == 0 or len(y_hi) == 0:
            continue
        y0 = float(y_lo[-1])
        y1 = float(y_hi[0])
        if y1 == y0:
            y_grid = float(np.argmin(np.abs(arr_y - y)))
        else:
            y_grid = float(np.where(arr_y == y0)[0][0]) + (y - y0) / (y1 - y0)
        final.append((x_idx, y_grid))
    else:
        # y is on a horizontal line; use y-grid index integer, x interpolated by nearby vertical lines
        y_idx = int(np.argmin(np.abs(arr_y - y)))
        x_lo = arr_x[arr_x <= x]
        x_hi = arr_x[arr_x >= x]
        if len(x_lo) == 0 or len(x_hi) == 0:
            continue
        x0 = float(x_lo[-1])
        x1 = float(x_hi[0])
        if x1 == x0:
            x_grid = float(np.argmin(np.abs(arr_x - x)))
        else:
            x_grid = float(np.where(arr_x == x0)[0][0]) + (x - x0) / (x1 - x0)
        final.append((x_grid, y_idx))

# Deduplicate in grid-space.
final2 = []
for p in final:
    if all(abs(p[0] - q[0]) > 1e-3 or abs(p[1] - q[1]) > 1e-3 for q in final2):
        final2.append(p)

# Write final CSV in the requested grid-unit format: one entry integer, the other interpolated.
with open(r'20260917_175649_true_intersections.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['x', 'y'])
    for x, y in sorted(final2):
        # ensure exactly one component is integer-like.
        if abs(x - round(x)) < abs(y - round(y)):
            writer.writerow([int(round(x)), float(y)])
        else:
            writer.writerow([float(x), int(round(y))])

# Also save an overlay in the rectified image with the cleaned points.
rect_img = Image.fromarray(cv2.cvtColor(rect, cv2.COLOR_BGR2RGB))
d = ImageDraw.Draw(rect_img)
for x, y in sorted(final2):
    # map back to pixel coordinates roughly using the line positions in the rectified plane.
    x_px = float(x) * 10.0
    y_px = float(y) * 10.0
    d.ellipse((x_px - 2, y_px - 2, x_px + 2, y_px + 2), fill=(255, 0, 0), outline=(255, 0, 0))
rect_img.save(r'20260917_175649_true_intersections_overlay.jpg')

print('x_lines', len(x_lines), 'y_lines', len(y_lines))
print('raw crossings', len(clean))
print('final points', len(final2))
print('first 20', sorted(final2)[:20])
print('output csv', r'20260917_175649_true_intersections.csv')
