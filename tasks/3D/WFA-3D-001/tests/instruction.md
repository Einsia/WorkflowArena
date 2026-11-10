# WFA-3D-001 — Axial Palace Compound: 36 Construction Units

## Scene
Build a palace compound in Blender in the Ming–Qing official style. The compound unfolds along a north–south central axis. From south to north it consists of: the Main Gate; the Golden Water River and its three bridges; a pair of stone lions in front of the Second Gate; the Second Gate; the outer-court imperial way; the three great halls (Main, Middle and Rear Hall); the Inner Gate; the inner-court imperial way; the Sleeping Hall; and the Rear Sleeping Hall. Along the east and west sides stand side halls, wing halls, warm halls and stele pavilions, linked by covered corridors (langwu) into a cloister. The courtyards hold a sundial, a jialiang standard measure, ding cauldrons and a bronze vat. The ensemble should feel solemn and clearly ranked: the higher a building's grade, the higher its platform and the more senior its roof form.

The site has 36 construction units. Their IDs and names are listed in `input/site/units.csv`, `input/site/corridors.csv` and `input/site/roads.csv`; their layout is shown in `input/site/site_plan.png`. **Each unit follows its own drawing in `input/sheets/`. The change order in `input/changes/` overrides the original drawings.** Drawing symbols are explained in `input/legend.png`.

## Global rules
1. **Coordinates and units**: metres, Z up, X east, Y north. The origin is the centre of MN01 at outdoor ground level, and outdoor ground is at elevation 0. The site extends over x −100…100 and y −30…380.
2. **Unit placement**:
   - Halls, gates, side halls and pavilions: the unit centre is the centre of the outline of the bottom platform tier.
   - Bridges: the unit centre is the centre of the deck.
   - Lions, sundial, jialiang, cauldrons and vat: the unit centre is the centre of the base.
   - `units.csv` gives the plan coordinates of each unit centre and the direction its front faces (S/E/W). For buildings whose front faces E or W, the frontage (面阔) runs along Y.
3. **Gables and frontage**: the two ends of a building along its frontage are its gable sides. `end_*_gable` in `corridors.csv` gives the side (N/S/E/W) of the connected unit at which each corridor end attaches.
4. **Corridor junctions**:
   - The end face of a corridor platform meets the outer edge of the connected unit's bottom platform tier, with no gap and no overlap.
   - The corridor centreline is collinear with that unit's centreline parallel to its frontage.
   - The turning point of an L-shaped corridor is the intersection of the two segment centrelines; its coordinates are in `corridors.csv`.
   - All corridor lengths on the drawings are centreline lengths.
   - A corridor platform (taiming) extends 0.60 m beyond the column centrelines on each side, i.e. it is w + 1.20 m wide, where w is the column spacing across the corridor shown on its section; at an L-shaped turn the platform continues to the outer corner.
5. **Imperial ways**: the centreline is at x = 0. The south and north ends meet the outer edges of the bottom platform tiers of the units listed in `roads.csv`.
6. **Axial symmetry**:
   - Units paired in the `mirror_pair` columns are mirror images of each other across the plane x = 0.
   - Units whose centre lies on x = 0 are themselves left–right symmetric.
   - Exceptions apply only where the change order says so.
7. **Grade and platform**:
   - `units.csv` gives each unit's grade (1 is the highest); corridors count as grade 4.
   - Platform-top elevation strictly decreases with grade: the platform top of any unit of a higher grade is above that of any unit of the next lower grade.
   - Glazed roof tiles are yellow for grades 1–3 and green for grade 4. Columns and doors/windows are vermilion; platforms and stonework are light stone.
8. **Golden Water River**: model the channel in `SITE` as shown on the site plan, matching its position, width and bed depth. All three bridges must span it.

## Naming contract
- Create one Collection per unit, named **exactly** with the unit ID (e.g. `DN01`, `LW05`). Put every object of the unit in that collection, with object names starting with `ID_`. Put global items such as the ground and the river in a `SITE` collection.
- The following parts must be separate objects with these names (`k` starts at 1; `###` is a 3-digit index):

| Unit type | Required separate objects |
|---|---|
| Halls / gates / side halls (DN/MN/PD) | One `ID_platform_k` per platform tier (k=1 = bottom tier); one `ID_col_###` per eave (outer-ring) column; one `ID_roof_k` per eave layer, including its ridges (k=1 = lowest); one `ID_door_###` per bay used as a door; bracket sets, if any, named `ID_dougong_###` |
| Stele pavilion (TT) | `ID_platform_1`; `ID_col_###` per column; `ID_roof_k` per eave layer; stele `ID_stele` |
| Corridor (LW) | `ID_platform_1`; `ID_col_###` per column; `ID_roof_1`; solid walls of a single-sided gallery `ID_wall_###` |
| Bridge (QL) | `ID_deck`; `ID_post_###` per baluster post |
| Lion (SS) | `ID_base_k` per pedestal tier; `ID_lion`; `ID_head`; `ID_ball` or `ID_cub` |
| Imperial way (YD) | `ID_road`; `ID_slab_###` per carved central slab; `ID_curb_###` if kerbs are present |
| Sundial / jialiang (RG) | `ID_base_k` per tier; sundial: `ID_dial`, `ID_gnomon`; jialiang: `ID_vessel`, `ID_ear_###` |
| Cauldron / vat (DL) | `ID_base_k`; `ID_body`; `ID_leg_###` per leg; `ID_ear_###` per handle; `ID_ring_###` per knocker ring |

- Ridge ornaments are optional; put them in `ID_orn_###`, and they do not count as roof. Other details are free, as long as their names start with `ID_`.
- The "ridge top / finial top" elevation on a drawing is the highest point of the roof objects.

## Deliverables
1. `output/scene.blend`: opens directly in Blender 4.3. Use the metric unit system with metres and unit scale 1.0.
2. `output/renders/`, each a 1920×1080 PNG:
   - `overview.png`: a high oblique view from the south-east showing the whole compound;
   - `axis_south.png`: a low view from the central axis south of MN01, looking north along the axis;
   - `east_wing.png`: a high view from the east over the east wing (PD01, PD03 and the corridors connected to them).
3. `output/manifest.json`: an array with one entry per unit, `{"id", "collection", "built": true/false, "params": {...}}`. The `params` fields depend on the unit type:
   - DN/MN/PD: `bays_front`, `bays_depth`, `platform_tiers`, `platform_top_m`, `roof`, `eaves`, `dougong`, `door_bays`, `ridge_top_m`
   - TT: `plan` (`square`/`octagon`), `columns`, `roof`, `eaves`, `platform_top_m`
   - LW: `segments` (an array of `{"length_m", "bays"}`, starting from end A), `gallery` (`single`/`double`), `roof`, `platform_top_m`
   - QL: `arches`, `posts_per_side`, `deck_length_m`; SS: `sex` (`male`/`female`), `base_tiers`, `height_m`
   - YD: `length_m`, `width_m`, `slabs`, `curb`; RG: `base_tiers`, plus `dial_tilt_deg` (sundial) or `vessel_shape` (jialiang)
   - DL: `legs`, `ears`, `rings`
   - `roof` takes one of `wudian`/`xieshan`/`xuanshan`/`yingshan`/`cuanjian`/`juanpeng`/`jianshan`.

`manifest.json` is only a declaration; review is based on measurements of `scene.blend`.

## Environment
Offline container with Blender 4.3 (`blender -b --python` available) and Python 3.11. **No GPU, no network.** Any renderer may be used (Cycles at low samples with denoising, Eevee or Workbench). The wall-clock budget is 3600 s; save a valid set of deliverables early, then keep improving.
