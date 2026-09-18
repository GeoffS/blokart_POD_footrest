# Path/Grid Intersection Analysis — Summary

## Goal
Given a photo of a hand-drawn pencil path on light-blue graph paper
(`20260917_175649.jpg`, plus `20260917_175649_masked.png` isolating the
path and nearby grid), produce a CSV of all points where the path
crosses the grid lines.

## Approach
A Python venv (`.venv`) was created with numpy, opencv, scipy,
pillow, and scikit-image. Processing is split into three scripts, run
in order:

1. **`grid_lines.py`** — Detects the grid on the *full* original photo
   (more complete than the masked crop, so line fits are better
   constrained). Grid lines are picked out via the blue-red color
   channel difference. Rather than a single global Hough transform
   (too fragile against the mild perspective/lens distortion), each
   line's position is tracked band-by-band down the image, and a
   quadratic polynomial is fit per line: `x(y)` for vertical lines,
   `y(x)` for horizontal lines. Lines are assigned integer grid
   indices (accounting for the rare undetected/missing line). Result
   saved to `grid_lines.npz`.

2. **`path_extract.py`** — Isolates the gray pencil stroke from the
   masked image (darker/less-blue than the grid), skeletonizes it, and
   for each disconnected skeleton fragment finds its true centerline
   (the longest shortest-path through the skeleton graph, which
   ignores small spurious branches from noise). The 2–3 real path
   fragments (split by pencil-lift gaps) are then chained together
   end-to-end into one continuous ordered polyline, bridging the gaps
   with straight-line interpolation. Saved to `path_polyline.npy`.

3. **`intersect.py`** — Resamples the polyline to a uniform arc-length
   spacing and lightly smooths it (edge-padded moving average, to
   avoid boundary artifacts). At every point along the path, the
   fractional grid coordinate is computed using **only the two nearest
   bracketing grid lines** (local interpolation), not a single
   whole-image homography — this was requested specifically to
   minimize the effect of perspective/alignment errors. Crossings of
   integer grid-line boundaries are detected with a small hysteresis
   margin, which prevents spurious repeated "crossings" in the stretch
   where the path runs nearly parallel to a grid line. Output written
   to `intersections.csv`.

## Output
`intersections.csv` contains 176 rows:

| column | meaning |
|---|---|
| `seq` | order along the path (start to end) |
| `pixel_x`, `pixel_y` | crossing location in the original photo's pixel coordinates |
| `grid_col`, `grid_row` | fractional grid-square coordinates; whichever axis was just crossed is (near) an exact integer |
| `crossing_type` | `col` (crossed a vertical line) or `row` (crossed a horizontal line) |

`grid_col`/`grid_row` are **relative** grid-square units — index 0 is
an arbitrarily chosen reference line near the image edge, not tied to
any printed axis on the paper, and no physical (mm) scale was applied
since the real-world square size wasn't specified.

A visual check, `intersections_preview.png`, overlays the detected
crossings (red = column crossings, blue = row crossings) on the
original photo for verification.

## Known limitations
- Two visible gaps in the pencil path (where the pencil was lifted)
  were bridged with straight-line interpolation; crossings inside
  those gaps are estimated, not directly measured.
- Grid indices are relative, not absolute/physical.
- Coordinates rely on the fitted per-line polynomials remaining
  locally accurate; far from any detected grid line (largely irrelevant
  here since the path stays within the densely-gridded region) accuracy
  would degrade.
