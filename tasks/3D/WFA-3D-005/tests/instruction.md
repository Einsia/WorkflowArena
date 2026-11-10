# WFA-3D-005 — Old Harbour Town Block

## Task
Build, in Blender 4.3, one complete block of an old North Sea harbour town: the quay edge, Quay Street, Market Street running inland at right angles to the quay, Ropewalk Lane behind it, 30 lots of terraced shop-houses along these streets, plus street lamps, mooring bollards and three small boats moored in the harbour basin. The character is that of a 17th–19th century harbour mixing brick and render: narrow-fronted deep terraced houses, front gables, side-gable roofs, mansards, arcades and warehouses side by side; every facade has its own colour, ground-floor shops carry fascia signs, and evening harbour light with reflections on the water makes the block feel lived in.

Each unit follows its sheet in `input/sheets/`; the change order in `input/changes/` takes precedence over the original sheets.

## Inputs
- `input/site/site-plan.png`, `input/site/rows.csv`: site plan. For each of the six rows of lots (A–F): street, building line, facade orientation, start/end coordinate along the street and lot order.
- `input/site/furniture.csv`: positions and specifications of lamps, bollards and moored boats.
- `input/sheets/<lot>.png`: one sheet per lot (front elevation, side elevation, roof plan, title block).
- `input/legend.png`: roof-form symbols R1–R5, gable-style symbols G-a/G-b/G-c, component symbols and facade colour card.
- `input/changes/CO-01.png`: change order.

## Global rules
1. **Coordinates and units**: metres, Z up; +X east, +Y north; street level and quay deck are z = 0 (±0.00 on the sheets). The quay edge is y = 0; the harbour basin lies south of it with the water surface at z = −1.20.
2. **Lots and building lines**: each row is laid out from `start` to `end` in the direction given by rows.csv, lot widths taken from the sheets, lots abutting end to end. Each building's main street facade lies on its row's building line and the building extends away from the street by its sheet depth. The left end of a sheet's front elevation is the lot's start end in the row direction.
3. **Continuous street frontage, uniform setback**: all main facades on one building line are coplanar. Only signs, balconies, hoist beams, eaves and roof overhangs, sills and door/window surrounds may cross the building line; arcade columns stand on the building line.
4. **Shared gable walls**: adjacent buildings in a row share the party wall on the lot boundary — the walls meet on the boundary with neither overlap nor gap; where heights differ, the taller building closes its own exposed gable.
5. **Signs**: sign text matches the sheet character for character (case, spaces, punctuation, digits) and reads correctly from the street.
6. **Facade colour**: each building's main facade material uses the sRGB colour of the colour code on its sheet.

## Naming contract
- One collection per lot, named exactly as the lot number (`A01` … `F05`); global items (streets, quay, water, lamps, bollards, boats) go into collection `SITE`.
- Objects inside a lot collection (`<ID>` = lot number; floor `f` counted from ground floor = 1; axis `a` = sheet axis number):
  - `<ID>_BODY`: the wall mass below the eaves (z = 0 up to eave level), a single closed mesh; its main material is named after the facade colour code (of the form `HC-xx`).
  - `<ID>_ROOF`: everything above the eaves (roof surfaces, gable pediment, stepped or bell gable, parapet), a single mesh.
  - `<ID>_WIN_<f>_<a>`: one window on floor f at axis a, one object per window. Ground-floor shop windows do not use this name.
  - `<ID>_DOOR`: ground-floor entrance door (not for arcade shophouses); `<ID>_LOAD_<f>`: loading door on floor f; `<ID>_HOIST`: hoist beam.
  - `<ID>_DORM_<k>`: dormer (k from 1); `<ID>_COL_<k>`: arcade column; `<ID>_BALC`: balcony.
  - `<ID>_SIGN`: the sign lettering, kept as a Blender Text object whose body is the sign text.
  - Further decorative objects are free, named with prefix `<ID>_`.
- If the change order merges lots, the merged building is named with the lot number the change order specifies and placed in that collection; the collections of absorbed lots must still exist and contain no objects.
- Global items: `SITE_LAMP_xx`, `SITE_BOLLARD_xx`, `SITE_BOAT_k`, matching the `id` column of furniture.csv. Lamp `height` is ground to lamp-head centre, bollard `height` is the top of the post, boat `length` is overall hull length.

## Animation
Timeline frames 1–240 at 24 fps. The three moored boats roll in place about their own longitudinal axis: amplitude `roll_amp_deg`, period `roll_period_s`, roll(t) = amplitude × sin(2π·t / period + φ) with φ the angle given by `roll_phase_deg`, t in seconds from frame 1, positive roll heeling the hull to starboard; boats do not translate. Everything else is static.

## Deliverables
1. `output/scene.blend` (Blender 4.3) following the collection and naming contract, units in metres.
2. `output/renders/`, each a 1920×1080 PNG rendered from the camera of the same name, cameras kept in scene.blend:
   - `overview.png` (camera `CAM_OVERVIEW`): high oblique aerial from south-east of the block; all built lots, the basin and the three boats in frame.
   - `quay.png` (`CAM_QUAY`): from above the basin water looking north at Quay Street; all facades of rows A and B fully in frame.
   - `market.png` (`CAM_MARKET`): at the south mouth of Market Street, eye height 1.6 m, looking north along the street; facades of rows E and F and the Ropewalk Lane buildings at the street's end visible.
3. `output/manifest.json`: an array with one entry per lot:
   `{"id": "A01", "collection": "A01", "built": true, "params": {"width", "depth", "storeys", "eave", "top", "roof", "gable", "gable_steps", "dormers", "arcade_bays", "windows", "door_axis", "load_axis", "sign_text", "colour"}}`
   - `roof` is `R1`–`R5`; `gable` is `G-a`/`G-b`/`G-c` or null; `windows` is a list of `"f_a"` strings; `eave` and `top` are eave level and highest point (m); fields that do not apply are null.
   - A lot no longer built after a merge: `"built": false, "params": {"merged_into": "<lot>"}`.
   - The content must agree with scene.blend.
4. Optional: `output/preview.mp4`, 640×360, showing the boats rolling.

## Environment
Offline container: Blender 4.3 (`blender -b --python` available), Python 3.11, no GPU, no network. Renderer and sampling are your choice. Total time limit 3600 s.
