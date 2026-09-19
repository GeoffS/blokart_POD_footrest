import csv
import numpy as np
import cv2
from PIL import Image, ImageDraw

masked = np.array(Image.open(r'20260917_175649_masked.png').convert('RGB'))
orig = Image.open(r'20260917_175649.jpg').convert('RGB')
R, G, B = masked[:, :, 0], masked[:, :, 1], masked[:, :, 2]

# Grid lines are blue on pale gray.
grid = ((B > G + 15) & (B > R + 15) & (B > 120)).astype(np.uint8)
kernel = np.ones((3, 3), np.uint8)
grid = cv2.morphologyEx(grid, cv2.MORPH_OPEN, kernel)
grid = cv2.morphologyEx(grid, cv2.MORPH_CLOSE, kernel)

# Path is dark gray, excluding grid pixels.
path = ((R < 220) & (G < 220) & (B < 220)).astype(np.uint8)
path = cv2.bitwise_and(path, cv2.bitwise_not(grid))
path = cv2.morphologyEx(path, cv2.MORPH_OPEN, kernel)
path = cv2.morphologyEx(path, cv2.MORPH_CLOSE, kernel)

# Use the dominant periodic grid-line peaks, then keep only stronger peaks separated by realistic spacing.
def local_grid_lines(signal, min_val=25, gap=28):
    if len(signal) < 3:
        return []
    idx = []
    for i in range(1, len(signal) - 1):
        if signal[i] >= signal[i - 1] and signal[i] >= signal[i + 1] and signal[i] > min_val:
            idx.append(i)
    if not idx:
        return []
    out = [idx[0]]
    for v in idx[1:]:
        if abs(v - out[-1]) > gap:
            out.append(v)
    return out

x_lines = local_grid_lines(grid.sum(axis=0), min_val=35, gap=30)
y_lines = local_grid_lines(grid.sum(axis=1), min_val=35, gap=30)

# A true intersection must have path pixels on both sides of a grid line within a narrow band.
def find_crossings_on_vertical(x_coord, band=2):
    xs0 = max(0, x_coord - band)
    xs1 = min(masked.shape[1], x_coord + band + 1)
    band_img = path[:, xs0:xs1]
    rows = np.where(band_img.sum(axis=1) > 0)[0]
    if len(rows) == 0:
        return []
    crossings = []
    current = []
    for r in rows:
        left = band_img[r, :max(1, band)]
        right = band_img[r, min(band_img.shape[1], band + 1):]
        if left.sum() > 0 and right.sum() > 0:
            current.append(r)
        else:
            if current:
                crossings.append((min(current), max(current)))
                current = []
    if current:
        crossings.append((min(current), max(current)))
    result = []
    for y0, y1 in crossings:
        result.append((x_coord, int(round(0.5 * (y0 + y1)))))
    return result


def find_crossings_on_horizontal(y_coord, band=2):
    ys0 = max(0, y_coord - band)
    ys1 = min(masked.shape[0], y_coord + band + 1)
    band_img = path[ys0:ys1, :]
    cols = np.where(band_img.sum(axis=0) > 0)[0]
    if len(cols) == 0:
        return []
    crossings = []
    current = []
    for c in cols:
        up = band_img[:max(1, band), c].sum() > 0
        down = band_img[min(band_img.shape[0], band + 1):, c].sum() > 0
        if up and down:
            current.append(c)
        else:
            if current:
                crossings.append((min(current), max(current)))
                current = []
    if current:
        crossings.append((min(current), max(current)))
    result = []
    for x0, x1 in crossings:
        result.append((int(round(0.5 * (x0 + x1))), y_coord))
    return result

# Build the candidate intersection list using the actual path crossing logic.
points = []
for x in x_lines:
    points.extend(find_crossings_on_vertical(x, band=2))
for y in y_lines:
    points.extend(find_crossings_on_horizontal(y, band=2))

# Remove near-duplicates from different passes.
unique = []
for p in points:
    if all(abs(p[0] - q[0]) > 2 or abs(p[1] - q[1]) > 2 for q in unique):
        unique.append(p)

# Draw the refined points on the original image.
img_overlay = orig.copy()
d = ImageDraw.Draw(img_overlay)
for x, y in unique:
    d.ellipse((x - 4, y - 4, x + 4, y + 4), fill=(255, 0, 0), outline=(255, 0, 0))

out_path = r'20260917_175649_intersections_overlay_secondpass.jpg'
img_overlay.save(out_path)

with open(r'20260917_175649_intersections_secondpass.csv', 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['x_px', 'y_px'])
    for x, y in sorted(unique):
        w.writerow([x, y])

print('x_lines', x_lines[:10], '...', x_lines[-10:])
print('y_lines', y_lines[:10], '...', y_lines[-10:])
print('refined points', len(unique))
print('saved overlay', out_path)
print('saved csv', r'20260917_175649_intersections_secondpass.csv')
