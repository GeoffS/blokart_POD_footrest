import csv
import numpy as np
import cv2
from PIL import Image

img = np.array(Image.open(r'20260917_175649_masked.png').convert('RGB'))
H, W = img.shape[:2]
R, G, B = img[:, :, 0], img[:, :, 1], img[:, :, 2]

# Blue grid lines in the graph paper.
grid_mask = ((B > 140) & (G > 100) & (R < 220)).astype(np.uint8)
# Clean up a bit so single-pixel antialiasing does not break the line detection.
kernel = np.ones((3, 3), np.uint8)
grid_mask = cv2.morphologyEx(grid_mask, cv2.MORPH_OPEN, kernel)

col_sums = grid_mask.sum(axis=0)
row_sums = grid_mask.sum(axis=1)

# Keep only columns/rows that contain line pixels.
col_thresh = max(20, int(col_sums.max() * 0.08))
row_thresh = max(20, int(row_sums.max() * 0.08))

# Build contiguous runs of active columns/rows for each grid line.
col_active = np.where(col_sums > col_thresh)[0]
row_active = np.where(row_sums > row_thresh)[0]


def contiguous_runs(values):
    runs = []
    if len(values) == 0:
        return runs
    start = int(values[0])
    prev = int(values[0])
    for v in values[1:]:
        iv = int(v)
        if iv - prev > 2:
            runs.append((start, prev))
            start = iv
        prev = iv
    runs.append((start, prev))
    return runs

col_runs = contiguous_runs(col_active)
row_runs = contiguous_runs(row_active)

# Use the median center-to-center spacing as the graph cell size.
centers_x = np.array([(a + b) / 2.0 for a, b in col_runs], dtype=float)
centers_y = np.array([(a + b) / 2.0 for a, b in row_runs], dtype=float)

if len(centers_x) > 1:
    x_diffs = np.diff(np.sort(centers_x))
    if len(x_diffs) > 0:
        cell_size_x = float(np.median(x_diffs))
    else:
        cell_size_x = 1.0
else:
    cell_size_x = 1.0

if len(centers_y) > 1:
    y_diffs = np.diff(np.sort(centers_y))
    if len(y_diffs) > 0:
        cell_size_y = float(np.median(y_diffs))
    else:
        cell_size_y = 1.0
else:
    cell_size_y = 1.0

cell_size = float(np.median([cell_size_x, cell_size_y]))

# Use the first grid line as the origin. This is enough to express coordinates in grid units.
left_x = float(np.min(centers_x))
top_y = float(np.min(centers_y))

# Path mask: gray pencil lines, excluding blue grid lines.
# Light gray white background has values around 250; path is darker than that.
path_mask = ((R < 220) & (G < 220) & (B < 220)) & (~grid_mask.astype(bool))
path_mask = cv2.morphologyEx(path_mask.astype(np.uint8), cv2.MORPH_OPEN, kernel)
path_mask = cv2.morphologyEx(path_mask.astype(np.uint8), cv2.MORPH_CLOSE, kernel)

# Helper to group adjacent row indices into continuous segments.
def group_adjacent(indices, gap=2):
    if len(indices) == 0:
        return []
    groups = []
    start = int(indices[0])
    prev = int(indices[0])
    for i in indices[1:]:
        ii = int(i)
        if ii - prev > gap:
            groups.append((start, prev))
            start = ii
        prev = ii
    groups.append((start, prev))
    return groups

# Record intersections with vertical grid lines: integer x-index, fractional y.
points = []

for start, end in col_runs:
    x_line = int(round((start + end) / 2.0))
    x_index = round((x_line - left_x) / cell_size)
    line_pixels = np.where(path_mask[:, max(0, x_line - 2):min(W, x_line + 3)].sum(axis=1) > 0)[0]
    if len(line_pixels) == 0:
        continue
    # Segment into contiguous runs of occupied rows. This approximates the path crossing a vertical line.
    for y0, y1 in group_adjacent(line_pixels):
        y_mid = 0.5 * (y0 + y1)
        y_coord = (H - y_mid) / cell_size  # origin at lower-left, y increasing upward
        points.append((float(x_index), float(y_coord)))

# Record intersections with horizontal grid lines: fractional x, integer y-index.
for start, end in row_runs:
    y_line = int(round((start + end) / 2.0))
    y_index = round((y_line - top_y) / cell_size)
    line_pixels = np.where(path_mask[max(0, y_line - 2):min(H, y_line + 3), :].sum(axis=0) > 0)[0]
    if len(line_pixels) == 0:
        continue
    for x0, x1 in group_adjacent(line_pixels):
        x_mid = 0.5 * (x0 + x1)
        x_coord = (x_mid - left_x) / cell_size
        points.append((float(x_coord), float(y_index)))

# De-duplicate points that are essentially the same crossing, and sort by x then y.
unique = []
for p in points:
    px, py = p
    matched = False
    for uq in unique:
        if abs(px - uq[0]) < 0.25 and abs(py - uq[1]) < 0.25:
            matched = True
            break
    if not matched:
        unique.append(p)

# Normalize to a consistent integer/fraction pair: one coordinate integer, other interpolated.
# For each point, if x is close to an integer value, keep x as the integer and y as fractional.
# Otherwise, keep y as the integer and x as fractional.
normalized = []
for px, py in sorted(unique):
    if abs(px - round(px)) < 0.1:
        normalized.append((int(round(px)), float(py)))
    elif abs(py - round(py)) < 0.1:
        normalized.append((float(px), int(round(py))))
    else:
        # Fallback: use x as integer if one of the two coordinates is closer to an integer.
        if abs(px - round(px)) < abs(py - round(py)):
            normalized.append((int(round(px)), float(py)))
        else:
            normalized.append((float(px), int(round(py))))

# Write CSV
csv_path = r'20260917_175649_intersections.csv'
with open(csv_path, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['x', 'y'])
    for x, y in normalized:
        writer.writerow([x, y])

print('grid cell size', cell_size)
print('vertical lines', len(col_runs), 'horizontal lines', len(row_runs))
print('unique candidates before normalizing', len(points))
print('written to', csv_path)
print('output sample', normalized[:10])
