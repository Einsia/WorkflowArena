# WFA-3D-002 — Concentric Fortress on the Ridge

## Task
Build, in Blender, a medieval concentric fortress on hilly terrain from a set of drawings, and deliver the scene file, renders and a manifest.

The fortress has two rings of walls:
- **Inner ring**: an inner gatehouse, five towers and six curtain-wall segments around the inner ward. The inner ward holds the keep, the chapel and the well.
- **Outer ring**: an outer gatehouse, seven towers and eight curtain-wall segments. The space between the two rings is the outer ward; a range of lean-to stables stands against its west wall.
- **South gate**: a ditch runs in front of the outer gatehouse and is crossed by a drawbridge.

Style: 13th-century masonry military architecture — rough ashlar, crenellated parapets, arrow slits, timber roofs and a timber drawbridge. Mood: the fortress crowning its hill in low afternoon sun.

## Inputs
- `input/site/heightmap.png`: terrain height map. 16-bit greyscale, 641×641 px, covering x, y ∈ [−160, 160] m at 0.5 m per pixel.
  - Row 0 is y = +160; column 0 is x = −160.
  - Elevation is linear in pixel value: 0 → 0.0 m, 65535 → 48.0 m. Interpolate bilinearly between pixels.
- `input/site/site-plan.png`: site plan with contours, unit positions and IDs.
- `input/site/anchors.csv`: reference point `x_m, y_m` and orientation `facing_deg` for every unit except the curtain walls and the drawbridge.
  - For S01, the reference point is the midpoint of the stables' back wall projected onto the axis of W12.
- `input/site/links.csv`: the two nodes each curtain wall connects, and what the drawbridge and the stables attach to.
- `input/sheets/<UNIT_ID>.png`: one drawing sheet per unit (33 sheets).
- `input/legend.png`: symbol legend.
- `input/changes/CO-01.png`: change order.

Each unit is governed by its sheet in `input/sheets/`; the change order in `input/changes/` takes precedence over the original sheets.

## Global rules
1. **Coordinates and units**
   - Metres, Z up, +Y is north.
   - The scene origin is the fortress centre (0, 0). Elevations are absolute and match the height map.
2. **Terrain**
   - In collection `SITE`, create a mesh named `TERRAIN` that reproduces the height map at a grid spacing of no more than 1.0 m, covering the full extent.
   - The terrain is the height map: do not cut, fill or level it for buildings. Only foundations may go below ground.
3. **Placing units**
   - A unit's "reference ground" is the elevation of `TERRAIN` at its reference point (x, y). The ±0.00 datum and all levels on a sheet are relative to that elevation.
   - `facing_deg` is measured counter-clockwise from +X, in degrees.
   - For towers and gatehouses, facing is the outward normal of the outer face. The reference point is the circle centre for round towers, the geometric centre for square towers, the centre of the semicircle for D-shaped towers, and the centre of the plan rectangle for gatehouses. The meaning of facing for the keep, chapel, well and stables is given on their sheets.
4. **Curtain walls**
   - In plan, the wall axis passes through the reference points of both end nodes.
   - At each end, the wall body meets the node's outer surface tightly: no gap, and no protrusion through the node's inner face.
   - The wall-walk surface at each end is at the absolute elevation of that node's wall-walk door (node reference ground + the walk-door level on the node's sheet). Between the ends, the walk is a single continuous plane at constant grade.
   - Along its full length, the wall body reaches down from the walk to the terrain; no part of the wall base may hang above ground.
5. **Grounding**
   - Every unit (except the drawbridge deck) must sit on or into the terrain everywhere; nothing may float.
6. **Attachments**
   - The outer face of the stables' back wall lies against the inner face of W12.
   - The drawbridge follows sheet B01: when lowered, the far end of the deck rests on the counterscarp abutment, which stands on the ground on the outer side of the ditch.
7. **Real construction**
   - Every floor of a tower or of the keep, including the top platform, is a real slab.
   - Arrow slits, windows, gate passages and bell openings are real openings through the masonry.
   - Crenels between merlons are real gaps.
   - Counts such as storeys, merlons, slits and bays refer to these physical elements.

## Animation
- 24 fps; scene frame range 1–120.
- The movable deck of drawbridge B01 is an object named `B01_DECK`. It rotates about the hinge defined on the sheet:
  - frame 1: raised, deck vertical;
  - frames 1–72: lowers monotonically;
  - from frame 72 to frame 120: horizontal and resting on the abutment.
- On every frame, each of the two chains connects the far end of the deck to the outer face of G01.
- All other units are static.

## Deliverables
1. **`output/scene.blend`** (Blender 4.3)
   - One collection per unit, named exactly with the unit ID, including any unit added by the change order. Global items go in collection `SITE`, which contains `TERRAIN`.
   - Metric scene units, metres, unit scale 1.0.
2. **`output/renders/`**: three 1920×1080 PNGs, all rendered at frame 120:
   - `overview.png`: high oblique view from the south-east, with both rings and every unit fully in frame.
   - `gate.png`: near eye height, standing south of the ditch and looking north; G01 and the lowered B01 are the main subject.
   - `traverse.png`: near eye height from inside the outer ward, looking at W15 and the towers at both its ends, with both wall-to-tower joints clearly visible.
3. **`output/manifest.json`**
   - An array with one entry per unit: `{"id","collection","built":true|false,"params":{...}}`.
   - Fill `params` according to unit type, using the values read from the sheets (and the change order):

| Type | params fields |
|---|---|
| tower | `shape` (round/square/D), `storeys`, `merlons`, `slits_per_storey`, `roof` (platform/cone/pyramid), `walk_level`, `platform_level` |
| curtain wall | `merlons`, `slits`, `buttresses`, `thickness` |
| gatehouse | `portcullises`, `arch` (pointed/round), `flank_towers` (round/square), `merlons`, `walk_level` |
| drawbridge | `planks`, `deck_length` |
| keep | `storeys`, `turrets`, `roof` (platform/pyramid), `windows_per_long_side` |
| chapel | `bays`, `apse` (semicircular/polygonal/flat), `bell_openings` |
| stables | `stall_doors`, `loft_openings` |
| well | `posts`, `roof` (gable/pyramid) |

   - The manifest is your own declaration only; assessment is based on the actual geometry in `scene.blend`.

## Environment
- Offline container: Blender 4.3 (`blender -b --python` available), Python 3.11, no GPU.
- Any render engine may be used, e.g. low-sample Cycles with denoising, Eevee or Workbench.
- Wall-clock budget: 3600 s. Save a valid `scene.blend` early, then keep improving it.
- No network access and no downloaded assets.

Architectural terms have their usual meaning for medieval castles: curtain wall, merlon, crenel, parapet, arrow slit, buttress, portcullis, drawbridge, abutment, apse, bell-cote.
