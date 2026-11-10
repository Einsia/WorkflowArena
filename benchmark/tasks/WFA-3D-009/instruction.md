# WFA-3D-009 — Forum Romanum

## Task
Build an Imperial-era Roman forum in Blender and render it at sunset.

The forum is a long north–south paved rectangle:
- At the north end stands the main temple on a high podium, flanked by honorific columns.
- Along the east and west long sides, temples alternate with colonnades (porticus segments) to form continuous rows of columns.
- Outside the long sides stand two basilicas, one to the east and one to the west. Two triumphal arches mark the south end, and a round temple (tholos) stands in the south-west corner.
- A speaker's platform (rostra) and several statue bases occupy the plaza.

The style is classical Roman: travertine and marble, terracotta tiled roofs. A low sun from the west throws long column shadows across the paving, and the colonnades read clearly as rows.

The scene has **28 construction units**. The unit list, anchor coordinates and facings are given in `input/site/units.csv` and `input/site/site-plan.png`; symbols are explained in `input/legend.png`. Each unit is defined by its sheet in `input/sheets/`. The change order in `input/changes/` takes precedence over the original sheets.

## Global rules

### 1. Coordinates and units
- Units are metres, with Z up. The origin is the centre of the plaza; x points east and y points north.
- The top of the plaza paving is at z = 0 and covers x ∈ [−32, 32], y ∈ [−80, 72]. All anchors lie at z = 0.

### 2. Anchors and facing
"Facing" is the direction that the front or entrance faces. The anchor for each unit type is:

| Unit type | Anchor |
|---|---|
| Rectangular temple | Intersection of the front-row column axis line with the temple's centre axis |
| Tholos | Circle centre |
| Basilica | Centre of the rectangular body, excluding any apse. Facing = the long side that has the entrances. |
| Arch | Centre of the central passage. Passages run north–south. |
| Rostra | Midpoint of the platform's front chord. Facing = the direction of the front. |
| Statue base | Plan centre |
| Honorific column | Column axis |

Porticus segments have no anchor; they are placed by rule 5.

### 3. Order module
- **Column height:** the full column height H, measured from the bottom of the base to the top of the capital, is H = k·D. D is the lower shaft diameter, and k depends on the order: Doric 7, Ionic 9, Corinthian 10. Doric columns have no base.
- **Order:** identified from the capital symbol on the sheet (see the legend).
- **Scope:** this rule applies to every column in the scene, including temples, porticus segments, basilica interiors, arch columns and honorific columns.
- **Entablature and pediment:** the entablature of temples and porticus segments is H/4 high. A temple's pediment base width equals the outer width of the front colonnade, (n−1)·a + D, where n is the number of front columns and a is the axial spacing. The pediment slope is given on the sheet.

### 4. Temple podium and stairs
- **Podium overhang:** the podium projects D beyond the front column axis line and D beyond the corner column axes on each side.
- **Front stair:** the front stair rises from the paving to the podium top with equal risers and 0.35 m treads. The number of steps equals the number of risers. Stair width is shown on the plan.
- **Tholos:** the tholos has steps all round its podium, also with 0.35 m treads.

### 5. Porticus segments
- **Column line:** each porticus stands on the column line of its side: x = −32 on the west, x = +32 on the east and y = +72 on the north. Its columns stand directly on the paving.
- **Values from the followed temple:** each porticus follows one temple (column `follows` in units.csv). It takes that temple's order, D and axial spacing a, as they stand after the change order.
- **Start point and direction:** the first porticus column axis is at distance a from the axis of the followed temple's nearest front corner column. Further columns continue in the `extends` direction.
- **Relation to the temple:** the temple's front row and the adjacent porticus front row share one column axis line, forming a continuous colonnade.
- **Second row and back wall:** a second row, if present, stands one a behind the front row, on the side away from the plaza. The distance d from the column line to the inner face of the back wall is given on the sheet.
- **Roof:** the roof eave at the column line is at H + H/4. The roof form is shown on the sheet.

### 6. Openings
Basilica doors and windows, and arch passages, must be real through-openings in the walls.

### 7. Naming contract
- **Collections:** each unit has its own Collection, named exactly with the unit ID, e.g. `T03` or `P05`. Global items (paving, lights, cameras, sky) go in a `SITE` collection. There must be no other top-level collections.
- **Columns:** every column, including its base and capital, is a separate object whose name starts with `<ID>_COL`, e.g. `T03_COL_07`. Use this prefix for columns only.
- **Figures:** statues and column-top figures are separate objects whose names start with `<ID>_FIG`. Simplified human or equestrian figures are acceptable.
- **Prows:** each rostra prow is a separate object whose name starts with `<ID>_PROW`.

## Environment
- Offline container with Blender 4.3 (`blender -b --python` available), Python 3.11 and no GPU.
- Any renderer may be used: Cycles at low samples with denoising, Eevee or Workbench.
- Total budget: 3600 s.

## Deliverables (under `output/`)
1. **`scene.blend`**: the complete scene, in metres with Z up. Collections follow rule 7, and all 28 units are included.
2. **`renders/`**: three 1920×1080 PNGs, all lit by a sunset sun from the west at an elevation of 5°–15°.
   - `overview.png`: an elevated view from above the south-east corner of the plaza, looking north-west over the whole forum. All six site zones must be visible.
   - `west_colonnade.png`: eye height, standing in the south-west part of the plaza and looking north along the west column line. T02, T03 and the west porticus segments must be visible.
   - `north_temple.png`: on the main axis, slightly above eye height, looking north at T01. C01, C02 and R01 must be visible.
3. **`manifest.json`**: an array with one entry per unit: `{"id", "collection", "built": true/false, "params": {...}}`. `params` holds the final values you read from the sheets and the change order, using the fields below. Orders are `doric`, `ionic` or `corinthian`; lengths are in metres.

   | Type | `params` fields |
   |---|---|
   | Temple | `order, D, a, front_columns, flank_columns, plan (prostyle/peripteral), podium_h, steps` |
   | Tholos | `order, D, columns, radius, roof (dome/cone), steps` |
   | Porticus | `follows, order, D, a, rows, columns_per_row, depth, roof (shed/gable)` |
   | Basilica | `order, D, colonnade_rows, columns_per_row, apses, windows_per_side, doors` |
   | Arch | `order, D, passages, columns_per_face, width, height` |
   | Rostra | `prows, front (straight/curved), rear_steps` |
   | Statue base | `shape (square/round/oblong), tiers, figure (standing/equestrian)` |
   | Honorific column | `order, D, base_steps, crown (statue/none)` |

   `flank_columns` is the number of columns along one side of a temple, including the front corner column. For a prostyle temple, this is the number of columns along the depth of the porch.
