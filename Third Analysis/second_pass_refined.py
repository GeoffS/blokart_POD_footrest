import csv
import numpy as np
import cv2
from PIL import Image, ImageDraw

masked = np.array(Image.open(r'20260917_175649_masked.png').convert('RGB'))
orig = Image.open(r'20260917_175649.jpg').convert('RGB')
R, G, B = masked[:, :, 0], masked[:, :, 1], masked[:, :, 2]

# Grid lines: blue on pale gray background.
grid = ((B > G + 15) & (B > R + 15) & (B > 120)).astype(np.uint8)
# Remove tiny noise.
kernel = np.ones((3, 3), np.uint8)
grid = cv2.morphologyEx(grid, cv2.MORPH_OPEN, kernel)
grid = cv2.morphologyEx(grid, cv2.MORPH_CLOSE, kernel)

# Path: dark gray stroke only, excluding grid pixels.
path = ((R < 220) & (G < 220) & (B < 220)).astype(np.uint8)
path = cv2.bitwise_and(path, cv2.bitwise_not(grid))
path = cv2.morphologyEx(path, cv2.MORPH_OPEN, kernel)
path = cv2.morphologyEx(path, cv2.MORPH_CLOSE, kernel)

# Find strong grid lines by periodic peaks in the blue-mask projection.
def detect_grid_lines(signal, min_val, gap):
    peaks = []
    for i in range(1, len(signal) - 1):
        if signal[i] >= signal[i - 1] and signal[i] >= signal[i + 1] and signal[i] > min_val:
            peaks.append(i)
    if not peaks:
        return []
    out = [peaks[0]]
    for p in peaks[1:]:
        if abs(p - out[-1]) > gap:
            out.append(p)
    return out

x_lines = detect_grid_lines(grid.sum(axis=0), min_val=35, gap=30)
y_lines = detect_grid_lines(grid.sum(axis=1), min_val=35, gap=30)

# Use crossing logic: a true intersection requires path on both sides of a grid line at the same row/column.
def find_vertical_crossings(grid_x, band=5):
    x0 = max(0, grid_x - band)
    x1 = min(masked.shape[1], grid_x + band + 1)
    pts = []
    for y in range(masked.shape[0]):
        if path[y, grid_x] == 0:
            continue
        left = path[y, x0:grid_x].sum()
        right = path[y, grid_x + 1:x1].sum()
        if left > 0 and right > 0:
            pts.append((grid_x, y))
    return pts


def find_horizontal_crossings(grid_y, band=5):
    y0 = max(0, grid_y - band)
    y1 = min(masked.shape[0], grid_y + band + 1)
    pts = []
    for x in range(masked.shape[1]):
        if path[grid_y, x] == 0:
            continue
        up = path[y0:grid_y, x].sum()
        down = path[grid_y + 1:y1, x].sum()
        if up > 0 and down > 0:
            pts.append((x, grid_y))
    return pts

pts = []
for x in x_lines:
    pts.extend(find_vertical_crossings(x, band=4))
for y in y_lines:
    pts.extend(find_horizontal_crossings(y, band=4))

# Deduplicate points close together.
unique = []
for p in pts:
    if all(abs(p[0] - q[0]) > 3 or abs(p[1] - q[1]) > 3 for q in unique):
        unique.append(p)

# Draw the final points on the original image.
img_overlay = orig.copy()
d = ImageDraw.Draw(img_overlay)
for x, y in unique:
    d.ellipse((x - 4, y - 4, x + 4, y + 4), fill=(255, 0, 0), outline=(255, 0, 0))

out_img = r'20260917_175649_intersections_overlay_secondpass_refined.jpg'
img_overlay.save(out_img)

with open(r'20260917_175649_intersections_secondpass_refined.csv', 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['x_px', 'y_px'])
    for x, y in sorted(unique):
        w.writerow([x, y])

print('x lines count', len(x_lines), 'first/last', x_lines[:10], x_lines[-10:])
print('y lines count', len(y_lines), 'first/last', y_lines[:10], y_lines[-10:])
print('refined points', len(unique))
print('saved', out_img)
