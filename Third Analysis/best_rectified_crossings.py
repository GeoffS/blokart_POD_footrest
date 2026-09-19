import csv
import numpy as np
import cv2
from PIL import Image, ImageDraw
from skimage.morphology import skeletonize
from collections import deque

# Load image and rectify by manual perspective points tuned to the visible paper corners.
orig = cv2.imread(r'20260917_175649.jpg')
source = np.array([
    [150, 150],
    [3850, 180],
    [110, 2850],
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

# Build path mask and skeleton in rectified image.
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
sk = skeletonize(path > 0).astype(np.uint8)

# Detect grid lines in rectified space using periodic peaks.
def strong_peaks(signal, min_val=18, gap=10):
    peaks = []
    for i in range(1, len(signal) - 1):
        if signal[i] >= signal[i - 1] and signal[i] >= signal[i + 1] and signal[i] > min_val:
            if not peaks or abs(i - peaks[-1]) > gap:
                peaks.append(i)
    return peaks

col_hits = blue.sum(axis=0)
row_hits = blue.sum(axis=1)
x_lines = strong_peaks(col_hits, min_val=20, gap=15)
y_lines = strong_peaks(row_hits, min_val=20, gap=15)

# Connected-component grouping for skeleton pixels along each grid line.
def neighbors(px, py):
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            x2 = px + dx
            y2 = py + dy
            if 0 <= x2 < sk.shape[1] and 0 <= y2 < sk.shape[0] and sk[y2, x2]:
                yield x2, y2

# For each grid line, find connected components of skeleton pixels touching the line.
points = []

# Vertical lines
for x in x_lines:
    visited = set()
    line_pixels = []
    for y in range(sk.shape[0]):
        if sk[y, x]:
            line_pixels.append((x, y))
    for px, py in line_pixels:
        if (px, py) in visited:
            continue
        q = deque([(px, py)])
        comp = []
        visited.add((px, py))
        while q:
            cx, cy = q.popleft()
            comp.append((cx, cy))
            for nx, ny in neighbors(cx, cy):
                if (nx, ny) not in visited and abs(nx - x) <= 1:
                    visited.add((nx, ny))
                    q.append((nx, ny))
        if len(comp) == 0:
            continue
        # Only accept real crossings where there is path continuity on both sides of the line.
        left = any(sk[y, x2] for y in range(max(0, min(cy for _,cy in comp)-2), min(sk.shape[0], max(cy for _,cy in comp)+3)) for x2 in range(max(0, x-6), x))
        right = any(sk[y, x2] for y in range(max(0, min(cy for _,cy in comp)-2), min(sk.shape[0], max(cy for _,cy in comp)+3)) for x2 in range(x+1, min(sk.shape[1], x+7)))
        if left and right:
            cx = sum(p[0] for p in comp) / len(comp)
            cy = sum(p[1] for p in comp) / len(comp)
            points.append((float(cx), float(cy)))

# Horizontal lines
for y in y_lines:
    visited = set()
    line_pixels = []
    for x in range(sk.shape[1]):
        if sk[y, x]:
            line_pixels.append((x, y))
    for px, py in line_pixels:
        if (px, py) in visited:
            continue
        q = deque([(px, py)])
        comp = []
        visited.add((px, py))
        while q:
            cx, cy = q.popleft()
            comp.append((cx, cy))
            for nx, ny in neighbors(cx, cy):
                if (nx, ny) not in visited and abs(ny - y) <= 1:
                    visited.add((nx, ny))
                    q.append((nx, ny))
        if len(comp) == 0:
            continue
        up = any(sk[y2, x2] for y2 in range(max(0, min(cy for _,cy in comp)-2), y) for x2 in range(max(0, min(cx for cx,_ in comp)-2), min(sk.shape[1], max(cx for cx,_ in comp)+3)))
        down = any(sk[y2, x2] for y2 in range(y+1, min(sk.shape[0], max(cy for _,cy in comp)+3)) for x2 in range(max(0, min(cx for cx,_ in comp)-2), min(sk.shape[1], max(cx for cx,_ in comp)+3)))
        if up and down:
            cx = sum(p[0] for p in comp) / len(comp)
            cy = sum(p[1] for p in comp) / len(comp)
            points.append((float(cx), float(cy)))

# Deduplicate by proximity in the rectified plane.
unique = []
for p in points:
    if all(abs(p[0] - q[0]) > 3 or abs(p[1] - q[1]) > 3 for q in unique):
        unique.append(p)

# Keep only the best grid-aligned points by sorting and filtering to those on or near the lines.
final = []
for x, y in unique:
    if any(abs(x - gx) <= 2 for gx in x_lines) or any(abs(y - gy) <= 2 for gy in y_lines):
        final.append((x, y))

# Save the corrected CSV in rectified image coordinates.
with open('20260917_175649_rectified_points_best.csv', 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['x_px', 'y_px'])
    for x, y in sorted(final):
        w.writerow([x, y])

# Draw the final points on the rectified image.
rect_rgb = cv2.cvtColor(rect, cv2.COLOR_BGR2RGB)
img2 = Image.fromarray(rect_rgb)
d = ImageDraw.Draw(img2)
for x, y in final:
    d.ellipse((x - 3, y - 3, x + 3, y + 3), fill=(255, 0, 0), outline=(255, 0, 0))
img2.save('20260917_175649_rectified_overlay_best.jpg')

print('x lines', len(x_lines), 'y lines', len(y_lines))
print('candidate points', len(unique))
print('final points', len(final))
print('saved to 20260917_175649_rectified_points_best.csv and 20260917_175649_rectified_overlay_best.jpg')
