import csv
from PIL import Image, ImageDraw

img = Image.open(r'20260917_175649.jpg').convert('RGB')
pts = []
with open(r'20260917_175649_intersections_test.csv', newline='') as f:
    reader = csv.DictReader(f)
    for row in reader:
        pts.append((float(row['x']), float(row['y'])))

# Approximate calibration from the masked image: graph area spans roughly 4000x3000 with grid lines
# around x 270..3741 and y 254..2741. We use a rough origin and cell spacing from the earlier detection.
img2 = img.copy()
d = ImageDraw.Draw(img2)
for x, y in pts:
    px = 300 + x * 282.25
    py = 2700 - y * 282.25
    d.ellipse((px - 6, py - 6, px + 6, py + 6), fill=(255, 0, 0), outline=(255, 0, 0))

img2.save(r'20260917_175649_intersections_overlay.jpg')
print('saved overlay with', len(pts), 'points')
