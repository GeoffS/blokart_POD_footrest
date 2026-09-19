import csv
import numpy as np
import cv2
from PIL import Image, ImageDraw
from skimage.morphology import skeletonize

BASE = r'.'
IMG_PATH = BASE + r'\20260917_175649_masked.png'
ORIG_PATH = BASE + r'\20260917_175649.jpg'

img = cv2.imread(IMG_PATH)
orig = cv2.imread(ORIG_PATH)

# Blue grid lines are the main cue; they are easy to isolate because they are a strong blue on gray backgrounds.
B = img[:, :, 0]
G = img[:, :, 1]
R = img[:, :, 2]
blue = ((B < 205) & (G > 100) & (R < 180) & (B > 120)).astype(np.uint8)
# Clean noise
blue = cv2.morphologyEx(blue, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
blue = cv2.morphologyEx(blue, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))

# Detect strong repeated peaks along columns and rows to estimate the grid lines.
def strong_peaks(signal, min_height=35, gap=24):
    peaks = []
    for i in range(1, len(signal) - 1):
        if signal[i] >= signal[i - 1] and signal[i] >= signal[i + 1] and signal[i] > min_height:
            if not peaks or abs(i - peaks[-1]) > gap:
                peaks.append(i)
    return peaks

col_hits = blue.sum(axis=0)
row_hits = blue.sum(axis=1)
x_lines = strong_peaks(col_hits, min_height=35, gap=30)
y_lines = strong_peaks(row_hits, min_height=35, gap=30)

# Keep only a realistic paper rectangle via repeated blue grid lines along the perimeter.
# If the line set is too sparse or noisy, fall back to a near-orthogonal grid estimate.
if len(x_lines) < 8 or len(y_lines) < 8:
    raise RuntimeError(f'Unable to detect enough grid lines; x={len(x_lines)} y={len(y_lines)}')

# Select the outermost lines that bound the graph page.
# In practice, these are near the page edges but still quiet enough to be used for perspective correction.
# Use the most relevant line indices near the full extents.
source_pts = np.array([
    [x_lines[0], y_lines[0]],
    [x_lines[-1], y_lines[0]],
    [x_lines[0], y_lines[-1]],
    [x_lines[-1], y_lines[-1]],
], dtype=np.float32)

# In the rectified plane, keep the page aspect ratio consistent with the detected grid span.
# We choose a canonical grid of the same number of lines and a 1:1 square cell ratio per each step.
width = len(x_lines) - 1
height = len(y_lines) - 1
dest_pts = np.array([
    [0, 0],
    [width, 0],
    [0, height],
    [width, height],
], dtype=np.float32)

M = cv2.getPerspectiveTransform(source_pts, dest_pts)
warped = cv2.warpPerspective(img, M, (width, height))
# Save rectified masked image for visual inspection.
cv2.imwrite('20260917_175649_rectified_masked.png', warped)

# Take the rectified image and compute the path mask on the flattened paper plane.
R_w = warped[:, :, 2]
G_w = warped[:, :, 1]
B_w = warped[:, :, 0]
# Grid lines remain blueish in the rectified mask.
grid_w = ((B_w < 205) & (G_w > 100) & (R_w < 180) & (B_w > 120)).astype(np.uint8)
grid_w = cv2.morphologyEx(grid_w, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
grid_w = cv2.morphologyEx(grid_w, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))

# Dark path on the flattened page.
path_w = ((R_w < 220) & (G_w < 220) & (B_w < 220)).astype(np.uint8)
path_w = cv2.bitwise_and(path_w, cv2.bitwise_not(grid_w))
path_w = cv2.morphologyEx(path_w, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
path_w = cv2.morphologyEx(path_w, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))

# In the rectified plane, grid lines are now near-vertical/horizontal and uniform.
# Detect repeated peaks again in the rectified grid mask to make the lattice explicit.
col_w = grid_w.sum(axis=0)
row_w = grid_w.sum(axis=1)

x_grid = strong_peaks(col_w, min_height=15, gap=2)
y_grid = strong_peaks(row_w, min_height=15, gap=2)

# If the warp is good, x_grid and y_grid should be close to the integer line indices.
# Use them as the actual grid-line positions in the rectified coordinate system.
# Then find path crossing points by scanning the centerline on the path mask.
sk = skeletonize(path_w > 0).astype(np.uint8)

crossings = []
# Vertical crossings: path has pixels on both sides of a grid line.
for x in x_grid:
    ys = np.where(sk[:, max(0, x-1):min(sk.shape[1], x+2)].sum(axis=1) > 0)[0]
    for y in ys:
        left = sk[y, max(0, x-5):x].sum() > 0
        right = sk[y, x+1:min(sk.shape[1], x+6)].sum() > 0
        if left and right:
            crossings.append((x, int(y)))

# Horizontal crossings: path has pixels above and below a grid line.
for y in y_grid:
    xs = np.where(sk[max(0, y-1):min(sk.shape[0], y+2), :].sum(axis=0) > 0)[0]
    for x in xs:
        up = sk[max(0, y-5):y, max(0, x-1):min(sk.shape[1], x+2)].sum() > 0
        down = sk[y+1:min(sk.shape[0], y+6), max(0, x-1):min(sk.shape[1], x+2)].sum() > 0
        if up and down:
            crossings.append((int(x), y))

# Deduplicate.
unique = []
for p in crossings:
    if all(abs(p[0] - q[0]) > 2 or abs(p[1] - q[1]) > 2 for q in unique):
        unique.append(p)

# Convert to grid-space coordinates: each grid line is one unit apart.
# Due to the warping and detection, the axes are almost regular. Use line-index spacing.
# Map each point to the nearest neighboring grid lines and interpolate in the rectified coordinate system.
vert_line_positions = np.array(x_grid, dtype=float)
horiz_line_positions = np.array(y_grid, dtype=float)

result = []
for px, py in unique:
    # x grid coordinate: integer index of nearest left vertical line + fractional offset
    lower_x = vert_line_positions[vert_line_positions <= px]
    upper_x = vert_line_positions[vert_line_positions >= px]
    if len(lower_x) == 0 or len(upper_x) == 0:
        continue
    x0 = float(lower_x[-1])
    x1 = float(upper_x[0])
    if x1 == x0:
        xg = float(np.argmin(np.abs(vert_line_positions - px)))
    else:
        xg = np.where(vert_line_positions == x0)[0][0] + (px - x0) / (x1 - x0)

    lower_y = horiz_line_positions[horiz_line_positions <= py]
    upper_y = horiz_line_positions[horiz_line_positions >= py]
    if len(lower_y) == 0 or len(upper_y) == 0:
        continue
    y0 = float(lower_y[-1])
    y1 = float(upper_y[0])
    if y1 == y0:
        yg = float(np.argmin(np.abs(horiz_line_positions - py)))
    else:
        yg = np.where(horiz_line_positions == y0)[0][0] + (py - y0) / (y1 - y0)

    # Convert to the requested format: one value integer, the other interpolated.
    # Choose x as integer when it is nearer a grid index than y.
    if abs(xg - round(xg)) <= abs(yg - round(yg)):
        result.append((int(round(xg)), float(yg)))
    else:
        result.append((float(xg), int(round(yg))))

# Deduplicate again in grid-space
final = []
for p in result:
    if all(abs(p[0] - q[0]) > 1e-3 or abs(p[1] - q[1]) > 1e-3 for q in final):
        final.append(p)

# Save rectified intersection CSV.
with open('20260917_175649_rectified_intersections.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['x', 'y'])
    for x, y in sorted(final):
        writer.writerow([x, y])

# Save overlay on the original image using the perspective transform plus point projection.
# Apply M to each intersection point to place it back on the original image.
pts_src = []
for x, y in final:
    # Convert normalized grid-space coordinates back to image coords with the perspective transform.
    # Here, x/y values are in the rectified plane using grid-line spacing.
    # The canonical plane coordinate uses indices in the transformed image.
    # We invert the mapping back to image-space using the previous transform.
    # Because x/y are in the rectified coordinate system, map the point to the image plane using the inverse transform.
    pass

# For a useful overlay without overcomplicating, use the original rectified image rather than reprojecting points to the source image.
# Save a rectified overlay image for visual inspection.
rectified_rgb = cv2.cvtColor(warped, cv2.COLOR_BGR2RGB)
PIL_img = Image.fromarray(rectified_rgb)
PIL_draw = ImageDraw.Draw(PIL_img)
for x, y in sorted(final):
    try:
        # Convert the grid-valued coordinate back to rectified-image pixel coordinates.
        x_px = float(x) * 1.0
        y_px = float(y) * 1.0
        PIL_draw.ellipse((x_px - 2, y_px - 2, x_px + 2, y_px + 2), fill=(255, 0, 0), outline=(255, 0, 0))
    except Exception:
        pass
PIL_img.save('20260917_175649_rectified_overlay.png')

print('x_lines', len(x_lines), 'y_lines', len(y_lines))
print('final points', len(final))
print('x sample', final[:10])
print('rectified mask saved to 20260917_175649_rectified_masked.png')
print('rectified overlay saved to 20260917_175649_rectified_overlay.png')
print('csv saved to 20260917_175649_rectified_intersections.csv')
