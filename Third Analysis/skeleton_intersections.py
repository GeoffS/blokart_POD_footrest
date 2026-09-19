import csv
import numpy as np
from PIL import Image
import cv2
from skimage.morphology import skeletonize

# Load the masked image
img = np.array(Image.open(r'20260917_175649_masked.png').convert('RGB'))
R, G, B = img[:, :, 0], img[:, :, 1], img[:, :, 2]

# Determine the graph-paper grid line mask once and subtract it from the path.
blue_grid = ((B > G + 15) & (B > R + 15) & (B > 120)).astype(np.uint8)
blue_grid = cv2.morphologyEx(blue_grid, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
blue_grid = cv2.morphologyEx(blue_grid, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))

# Path is dark gray line on the paper, but not blue grid.
path = ((R < 220) & (G < 220) & (B < 220)).astype(np.uint8)
path = cv2.bitwise_and(path, cv2.bitwise_not(blue_grid))

# Thicken a little to make the path a more continuous stroke if needed.
path = cv2.morphologyEx(path, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))

# Skeletonize to centerline to get the actual trace and avoid all nearby pixels.
path_bin = path > 0
skeleton = skeletonize(path_bin.astype(bool)).astype(np.uint8)

# Collect all pixels that lie on the centerline.
ys, xs = np.nonzero(skeleton)
print('skeleton pixels', len(xs))

# The grid-line coordinates should be on a regular lattice. Estimate them from the strong blue grid mask.
col_sums = blue_grid.sum(axis=0)
row_sums = blue_grid.sum(axis=1)
# Use strong local maxima separated by a realistic gap.

def strong_peaks(signal, min_val=35, gap=25):
    peaks = []
    for i in range(1, len(signal) - 1):
        if signal[i] >= signal[i - 1] and signal[i] >= signal[i + 1] and signal[i] > min_val:
            if not peaks or abs(i - peaks[-1]) > gap:
                peaks.append(i)
    return peaks

x_grid = strong_peaks(col_sums, min_val=35, gap=25)
y_grid = strong_peaks(row_sums, min_val=35, gap=25)
print('x grid lines', len(x_grid), 'y grid lines', len(y_grid))
print('sample x', x_grid[:20])
print('sample y', y_grid[:20])

# For every grid line, traverse the skeleton and keep points where the path is present on both sides.
points = set()
for x in x_grid:
    # find x positions in a narrow band around x
    x0 = max(0, x - 1)
    x1 = min(skeleton.shape[1], x + 2)
    band = skeleton[:, x0:x1]
    rows = np.where(band.sum(axis=1) > 0)[0]
    for y in rows:
        left = skeleton[y, max(0, x - 4):x].sum() > 0
        right = skeleton[y, x + 1:min(skeleton.shape[1], x + 5)].sum() > 0
        if left and right:
            points.add((x, int(y)))

for y in y_grid:
    y0 = max(0, y - 1)
    y1 = min(skeleton.shape[0], y + 2)
    band = skeleton[y0:y1, :]
    cols = np.where(band.sum(axis=0) > 0)[0]
    for x in cols:
        up = skeleton[max(0, y - 4):y, x].sum() > 0
        down = skeleton[y + 1:min(skeleton.shape[0], y + 5), x].sum() > 0
        if up and down:
            points.add((int(x), y))

# Save to CSV for download.
with open(r'20260917_175649_intersections_skeleton.csv', 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['x_px', 'y_px'])
    for p in sorted(points):
        w.writerow(p)

print('saved points', len(points))
print('first points', sorted(points)[:20])

# Save an overlay image by drawing these points on the original image.
from PIL import ImageDraw
orig = Image.open(r'20260917_175649.jpg').convert('RGB')
img2 = orig.copy()
d = ImageDraw.Draw(img2)
for x, y in sorted(points):
    d.ellipse((x - 3, y - 3, x + 3, y + 3), fill=(255, 0, 0), outline=(255, 0, 0))
img2.save(r'20260917_175649_intersections_overlay_skeleton.jpg')
print('saved overlay', r'20260917_175649_intersections_overlay_skeleton.jpg')
