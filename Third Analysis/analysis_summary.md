# Graph-path intersection analysis summary

## Goal

The task was to recover the coordinates of all points where the drawn pencil path crosses the graph-paper grid, expressed in graph-square units, with one coordinate as an integer grid index and the other interpolated between adjacent grid lines.

## Inputs

The analysis used the following files from this folder:

- `20260917_175649.jpg` — original photo of the graph paper and path
- `20260917_175649.png` — PNG copy used during masking work
- `20260917_175649_masked.png` — masked image with the non-path background removed and the path simplified

## Overall approach

The workflow was designed around the actual geometry of the graph paper and the pencil trace:

1. Separate the blue graph-grid lines from the gray pencil path.
2. Estimate the repeating grid-line positions in the image.
3. Rectify the perspective-distorted paper into a flattened, front-parallel plane.
4. Detect the path centerline in the rectified image.
5. Identify only genuine crossings where the path passes across a grid line.
6. Deduplicate nearby hits and convert the result into a grid-coordinate CSV.

## Image processing steps

### 1. Grid detection

The grid lines are blue on a light-gray background. A blue-dominance mask was used to isolate them, then morphological opening/closing was applied to remove noise and repair short gaps.

The grid-line positions were inferred from the repeated peaks in the horizontal and vertical projections of the blue mask. This gave a stable estimate of where the graph lines sit in the image.

### 2. Path detection

The pencil path is drawn in gray/dark values. A dark-gray mask was created and then intersected with the inverse of the grid mask so that grid lines were excluded from the path candidate region.

The path was then skeletonized to keep the centerline rather than every nearby stroke pixel. This reduced the chance of counting adjacent path pixels as separate crossings.

### 3. Perspective rectification

Because the camera was not perfectly parallel to the paper, the graph paper was distorted. A projective transform was fitted to the visible paper rectangle and used to warp the image into a front-parallel plane.

This step is important because raw image-pixel coordinates do not correspond to true graph distances unless the page is flattened.

### 4. Crossing detection

In the rectified image, grid lines became near-vertical and near-horizontal, with consistent spacing. The algorithm then examined the skeletonized path and recorded points where the path had continuous support on both sides of a grid line, which is a much stricter criterion than simply detecting nearby dark pixels.

This reduced false positives substantially.

### 5. Deduplication and grid conversion

Nearby points originating from the same path segment were merged. Then each crossing was converted into a grid coordinate system using the nearest grid lines and interpolation between them.

The final output stores one value as the near-integer grid index and the other as the interpolated fractional offset between adjacent grid lines.

## Output file

The resulting intersection list was saved as:

- `20260917_175649_true_intersections.csv`

This file is the current cleaned candidate list in the requested coordinate format.

## Notes

- The analysis is automatic and should be considered a strong candidate set rather than a guaranteed perfect ground-truth tracing.
- Some ambiguous or masked intersections may still be absent, which is acceptable under the original instructions.
- The goal was to recover the majority of visible path-grid intersections while accepting that a small number may be missed or misidentified.
