import csv
import numpy as np
from PIL import Image
import cv2
from skimage.morphology import skeletonize
from PIL import ImageDraw

# Load image and compute path skeleton
img = np.array(Image.open(r'20260917_175649_masked.png').convert('RGB'))
R, G, B = img[:, :, 0], img[:, :, 1], img[:, :, 2]

# grid mask: blue lines
blue = ((B > G + 15) & (B > R + 15) & (B > 120)).astype(np.uint8)
blue = cv2.morphologyEx(blue, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
blue = cv2.morphologyEx(blue, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))

# isolated path mask: dark gray minus grid
path = ((R < 220) & (G < 220) & (B < 220)).astype(np.uint8)
path = cv2.bitwise_and(path, cv2.bitwise_not(blue))
path = cv2.morphologyEx(path, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
path = cv2.morphologyEx(path, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))

# skeletonize path to a single-pixel centerline
sk = skeletonize(path > 0).astype(np.uint8)

# robust grid line positions from the blue mask
col_sums = blue.sum(axis=0)
row_sums = blue.sum(axis=1)


def strong_peaks(signal, min_val=35, gap=25):
    peaks = []
    for i in range(1, len(signal) - 1):
        if signal[i] >= signal[i - 1] and signal[i] >= signal[i + 1] and signal[i] > min_val:
            if not peaks or abs(i - peaks[-1]) > gap:
                peaks.append(i)
    return peaks

x_lines = strong_peaks(col_sums, min_val=35, gap=25)
y_lines = strong_peaks(row_sums, min_val=35, gap=25)
print('x lines', len(x_lines), 'y lines', len(y_lines))

# Vertical crossings: true crossing means skeleton pixels near x line have both left and right neighbors
crossings = []
for x in x_lines:
    # gather nearby skeleton pixels at x +/- 1
    ys = np.where((sk[:, max(0, x-1):min(sk.shape[1], x+2)] > 0).any(axis=1))[0]
    for y in ys:
        # need evidence of both left and right path continuity through x
        left = sk[max(0,y-1):min(sk.shape[0],y+2), max(0,x-4):x].sum()
        right = sk[max(0,y-1):min(sk.shape[0],y+2), x+1:min(sk.shape[1],x+5)].sum()
        if left > 0 and right > 0:
            crossings.append((x, int(y)))

# Horizontal crossings: path crosses a y line with observed both-up/down continuity
for y in y_lines:
    xs = np.where((sk[max(0,y-1):min(sk.shape[0],y+2), :] > 0).any(axis=0))[0]
    for x in xs:
        up = sk[max(0,y-4):y, max(0,x-1):min(sk.shape[1],x+2)].sum()
        down = sk[y+1:min(sk.shape[0],y+5), max(0,x-1):min(sk.shape[1],x+2)].sum()
        if up > 0 and down > 0:
            crossings.append((int(x), y))

# dedup and keep only near-unique crossings
unique = []
for p in crossings:
    if all(abs(p[0]-q[0]) > 2 or abs(p[1]-q[1]) > 2 for q in unique):
        unique.append(p)

# Save CSV and overlay
with open(r'20260917_175649_intersections_final.csv', 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['x_px', 'y_px'])
    for p in sorted(unique):
        w.writerow(p)

orig = Image.open(r'20260917_175649.jpg').convert('RGB')
img2 = orig.copy()
d = ImageDraw.Draw(img2)
for x,y in unique:
    d.ellipse((x-3, y-3, x+3, y+3), fill=(255,0,0), outline=(255,0,0))
img2.save(r'20260917_175649_intersections_overlay_final.jpg')

print('unique crossings', len(unique))
print('first 20', sorted(unique)[:20])
print('saved csv', r'20260917_175649_intersections_final.csv')
print('saved overlay', r'20260917_175649_intersections_overlay_final.jpg')
