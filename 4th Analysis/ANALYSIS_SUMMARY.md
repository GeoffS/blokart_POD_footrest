# Grid-Path Intersection Extraction — Summary

## Goal
Given a photo of a path traced in gray pencil on graph paper (`20260917_175649.jpg` /
`.png`), plus a manually-masked copy with everything except the path (and a band of
grid around it) erased to white (`20260917_175649_masked.png`), produce a CSV listing
every point where the path crosses a grid line, in grid-square units (one square = 1
unit).

## Result
- **`intersections.csv`** — 230 rows of `x,y` grid-unit coordinates. For every row,
  one of the two values is an exact integer (the index of the grid line crossed) and
  the other is linearly interpolated from the surrounding grid lines.
- **`debug_crossings_overlay.png`** — the original photo with every detected
  intersection marked as a red dot, for visual QA.
- **`generate_intersections.py`** — the full pipeline, reproducible end-to-end by
  running it from the project's `.venv`.

Visual inspection of the overlay showed essentially every visible grid crossing along
the entire traced path was found, well above the 90% target. A few extra hits came
from small pencil marks near the bottom corners that survived the masking step (not
part of the main traced path) — left in for you to filter out as mentioned.

## Approach

### 1. Grid calibration (from the unmasked `20260917_175649.png`)
The grid lines are light blue; the pencil path is gray. A **"blueness" channel**
(`B - R`) cleanly separates the two. A **white top-hat** (subtract a morphological
opening from the blueness channel) strips out the thicker pencil path, leaving just
the thin grid mesh.

Because the camera wasn't perfectly parallel to the page, line spacing drifts
slightly across the image. Rather than fit one global transform (homography), the
image was divided into **bands** (horizontal strips to find vertical-line
x-positions, vertical strips to find horizontal-line y-positions). Within each band,
a 1-D peak search on the summed grid mask locates every line crossing that band.

Each physical grid line was then **tracked band-to-band** via nearest-neighbor
matching to assign it one consistent integer index across the whole image (handling
lines that appear/disappear where the paper's irregular/notched edge enters or leaves
a band). This produces, per line index, a piecewise-linear function of its pixel
position — the calibration used to convert any pixel coordinate to continuous
`(column, row)` grid coordinates.

### 2. Path extraction (from `20260917_175649_masked.png`)
A fixed brightness threshold didn't work well because pencil pressure/darkness
varies across the stroke. Instead, a **black top-hat** (morphological closing minus
the grayscale image) highlights the path's *local contrast* against the paper,
regardless of absolute brightness. Blue-tinted grid-line pixels (still present in the
kept band around the path) are excluded via the same blueness test.

Small gaps in the mask — mostly where the path crosses a grid line — are closed
morphologically, then the mask is **skeletonized** to a 1px-wide curve. Each
connected fragment is turned into an ordered polyline via nearest-neighbor chaining
(starting from an endpoint). Fragments with a bounding box smaller than one grid
cell are discarded as stray marks rather than the traced path.

### 3. Crossing detection
Every ordered polyline is mapped through the grid calibration to continuous
`(column, row)` coordinates. Walking along consecutive points, whenever one
coordinate crosses an integer value, that's recorded as an intersection: the crossed
coordinate is set to that exact integer, and the other coordinate is linearly
interpolated between the two bracketing path samples. Near-duplicate crossings
(within 0.05 grid units) are merged.

## Files
| File | Purpose |
|---|---|
| `20260917_175649.jpg` / `.png` | Original photo (unmasked), used for grid calibration |
| `20260917_175649_masked.png` | Manually masked photo, used for path extraction |
| `generate_intersections.py` | End-to-end pipeline script |
| `intersections.csv` | Final output: intersection coordinates in grid units |
| `debug_crossings_overlay.png` | Visual QA — detected crossings drawn on the photo |
| `.venv/` | Python virtual environment (numpy, opencv-python-headless, scikit-image, scipy) |
