import csv
import cv2
import numpy as np
from PIL import Image, ImageDraw
from skimage.morphology import skeletonize

orig = cv2.imread(r'20260917_175649.jpg')
# Approximate page corners from the visible graph-paper rectangle.
# These are tuned to the image content rather than the raw pixel border.
source = np.array([
    [160, 150],
    [3850, 180],
    [120, 2860],
    [3900, 2890],
], dtype=np.float32)

# Canonical rectified plane: width/height chosen to preserve the paper aspect ratio.
W = 1200
H = 900
# Use a rectified square-ish page so the grid is easier to interpret.
dest = np.array([
    [0, 0],
    [W - 1, 0],
    [0, H - 1],
    [W - 1, H - 1],
], dtype=np.float32)

M = cv2.getPerspectiveTransform(source, dest)
rect = cv2.warpPerspective(orig, M, (W, H))
cv2.imwrite('20260917_175649_manual_rectified.jpg', rect)

# Detect grid and path in the rectified image.
B = rect[:, :, 0]
G = rect[:, :, 1]
R = rect[:, :, 2]
blue = ((B > 100) & (G > 120) & (R < 200)).astype(np.uint8)
blue = cv2.morphologyEx(blue, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
blue = cv2.morphologyEx(blue, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))

# Estimate grid line positions by repeated peaks in the projection.
def strong_peaks(signal, min_val=20, gap=10):
    pts = []
    for i in range(1, len(signal) - 1):
        if signal[i] > min_val and signal[i] >= signal[i - 1] and signal[i] >= signal[i + 1]:
            if not pts or abs(i - pts[-1]) > gap:
                pts.append(i)
    return pts

x_lines = strong_peaks(blue.sum(axis=0), min_val=20, gap=10)
y_lines = strong_peaks(blue.sum(axis=1), min_val=20, gap=10)
print('x_lines count', len(x_lines), 'first/last', x_lines[:20], x_lines[-20:])
print('y_lines count', len(y_lines), 'first/last', y_lines[:20], y_lines[-20:])

# Build a path mask and skeleton.
path = ((R < 220) & (G < 220) & (B < 220)).astype(np.uint8)
path = cv2.bitwise_and(path, cv2.bitwise_not(blue))
path = cv2.morphologyEx(path, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
path = cv2.morphologyEx(path, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
sk = skeletonize(path > 0).astype(np.uint8)

# Collect crossings on vertical and horizontal grid lines.
pts = set()
for x in x_lines:
    band = sk[:, max(0, x - 2):min(sk.shape[1], x + 3)]
    ys = np.where(band.sum(axis=1) > 0)[0]
    for y in ys:
        left = sk[y, max(0, x - 8):x].sum() > 0
        right = sk[y, x + 1:min(sk.shape[1], x + 9)].sum() > 0
        if left and right:
            pts.add((int(x), int(y)))

for y in y_lines:
    band = sk[max(0, y - 2):min(sk.shape[0], y + 3), :]
    xs = np.where(band.sum(axis=0) > 0)[0]
    for x in xs:
        up = sk[max(0, y - 8):y, x].sum() > 0
        down = sk[y + 1:min(sk.shape[0], y + 9), x].sum() > 0
        if up and down:
            pts.add((int(x), int(y)))

# Deduplicate by proximity.
final = []
for p in sorted(pts):
    if all(abs(p[0] - q[0]) > 3 or abs(p[1] - q[1]) > 3 for q in final):
        final.append(p)

# Save output CSV in grid-space-like rectified coordinates.
with open('20260917_175649_rectified_points.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['x', 'y'])
    for x, y in final:
        writer.writerow([x, y])

# draw on the rectified image
img2 = Image.fromarray(cv2.cvtColor(rect, cv2.COLOR_BGR2RGB))
d = ImageDraw.Draw(img2)
for x, y in final:
    d.ellipse((x - 3, y - 3, x + 3, y + 3), fill=(255, 0, 0), outline=(255, 0, 0))
img2.save('20260917_175649_rectified_overlay.jpg')

print('final points', len(final))
print('csv', '20260917_175649_rectified_points.csv')
print('overlay', '20260917_175649_rectified_overlay.jpg')
