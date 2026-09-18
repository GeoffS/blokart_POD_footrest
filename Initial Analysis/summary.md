# Grid-Path Intersection Extraction — Summary

## Input
`20260917_175649.jpg` — a photo of a hand-drawn path in gray pencil across two
taped-together sheets of light-blue graph paper, with some gaps in the pencil line.

## Output
- **intersections.csv** — one row per point where the pencil path crosses a grid line.
  - `order`: sequence of the point along the path (nearest-neighbor traversal order)
  - `grid_x`, `grid_y`: fractional grid-square coordinates (unit = one grid square,
    counted from the first detected grid line; real-world square size is unknown)
  - `pixel_x`, `pixel_y`: location in the original photo
  - `crossed_line_type`: which grid line(s) were crossed at that point
    (`vertical_line`, `horizontal_line`, or both)
- **verify_full.png** — the photo with every detected point circled in red, for
  visual QA against the CSV.

## Method
1. Separated grid lines (light blue) and pencil path (neutral gray, darker than the
   paper) using color/darkness thresholds on the RGB image.
2. Found the grid's true spacing (~57 px) via FFT/peak analysis, then tracked each
   grid line's pixel position in bands across the photo to compensate for slight
   camera-perspective warp (grid lines were not perfectly straight in the photo).
3. Scanned the pencil mask along every grid line to find crossing points; small
   pixel-scale gaps in the pencil were bridged automatically via mask dilation.
4. Converted pixel crossing locations to fractional grid coordinates by
   interpolating against the tracked grid-line positions.
5. Removed false positives from: paper edges/margins (deckle edge, top/bottom
   margins), a paper crease, tape smudges, and a handwritten annotation — verified
   by cropping and visually inspecting each flagged region.
6. Deduplicated near-coincident points (vertical- and horizontal-line crossings
   detected at the same location) and ordered the final list along the path.

## Result
82 intersection points written to `intersections.csv`.

## Known caveats
- Coordinates are in grid-square units, not real-world units.
- A few points near the taped bottom-right corner are close together and may
  include a slight duplicate from tape shadow overlapping the line.
- A genuine gap in the pencil spanning an entire grid-line crossing (not just a
  pixel or two) would not be detected, since there's no mark there to find.
