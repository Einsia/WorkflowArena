# WFA-3D-004 — Cathedral of the Assumption (High Gothic, Latin cross)

## Task
Use Blender 4.3 to build a complete High Gothic cathedral from a set of construction sheets. The plan is a Latin cross, oriented west to east. From west to east the building has:

- a west front with twin towers and a rose window;
- an eight-bay nave with aisles and flying buttresses;
- a crossing with a lantern tower;
- north and south transept arms, each ending in a rose-window front;
- a three-bay choir;
- a polygonal apse ringed by radiating chapels.

The building is masonry: tall, light-filled High Gothic with pointed arches, rib vaults, and clerestories glazed with stained glass. The exterior has rows of flying buttresses and pinnacles.

The cathedral is divided into 34 construction units. Build each unit as shown on its sheet in `input/sheets/`. The change order in `input/changes/` takes precedence over the original sheets.

## Inputs
- `input/site/site-plan.png` and `input/site/units.csv`: the site plan, structural grid, and zoning. They give each unit's id, zone, type (`type` code and `type_name`) and placement anchor.
- `input/sheets/<UNIT>.png`: one construction sheet per unit, with plans, elevations, sections, dimensions and counts.
- `input/legend.png`: the symbol legend and counting conventions.
- `input/changes/CO-01.png`: the change order.

## Global rules
1. **Coordinates and units.**
   - Units are metres. Z is up, and the nave floor is at z = 0.
   - +X points east along the building axis, with the apse at +X. +Y points north.
   - The origin is the centre of the crossing.
2. **Grid.**
   - The module is 7.00 m.
   - Grid lines 1–9 are at x = −63.00 + 7.00·(k−1).
   - Nave arcade axes are at y = ±7.00. Aisle outer-wall axes are at y = ±14.00.
3. **Ownership.** Every element belongs to exactly one unit. Do not build any element twice.
   - Nave bay N01–N08 owns:
     - the two arcade piers on its west grid line;
     - its arcade arches and triforium;
     - both clerestory walls and their windows;
     - its high vault and its roof.
   - The four crossing piers on grid line 9 belong to X01.
   - Aisle segment L01–L04 owns the aisle vaults, the outer wall, the windows, the door, the outer-wall buttresses and the aisle roof.
   - Flyer group F01–F04 owns the culees standing on the aisle buttresses, the flying arches and the pinnacles.
   - Transept bays, choir bays and the apse each own their own walls, windows, vaults and roofs.
   - R01 is the rose window set into the west face of P01. The opening it sits in belongs to P01.
4. **Interfaces.**
   - Pier grid continuity: each pier position has exactly one pier. Adjacent units must not duplicate a pier or leave one out.
   - The high-vault crowns of the nave, crossing, transepts, choir and apse are all at one level. Where two adjacent bays share a grid line, their transverse arches coincide.
   - Each flyer's culee stands on the top face of the aisle buttress on the same grid line. The lower end of each flying arch lands on the culee. The upper end abuts the outer face of the nave clerestory wall.
   - The two west towers have mirror-symmetric footprints about the building axis, and their spire tips are at the same height; all other tower details follow each tower's own sheet. The centre of the west rose lies on the building axis, in the plane of P01's west face.
5. **Openings and materials.**
   - Every window, triforium opening and rose window is a real opening through its wall.
   - Glass uses a transmissive or emissive material that is distinct from the stone material.
6. **Naming contract for countable elements.**
   - Each countable element is a single object named `<UNIT>_<CODE>_<nn>`, for example `N05_LIGHT_03` or `F02_FLY_04`. Counting follows the conventions in the legend.

     | Code | Element |
     |---|---|
     | `PIER` | pier |
     | `RIB` | rib segment |
     | `TRI` | triforium opening |
     | `WIN` | window opening |
     | `LIGHT` | glazed light |
     | `DOOR` | door |
     | `NICHE` | blind-arcade niche |
     | `KING` | gallery niche |
     | `PORTAL` | portal |
     | `BUTT` | aisle buttress |
     | `CULEE` | culee |
     | `FLY` | flying arch |
     | `PINN` | pinnacle |
     | `SPIRE` | spire or flèche |
     | `ROSE` | rose-window light |
     | `TURRET` | stair turret |

   - Name other elements (walls, roofs, vault webs, mouldings, floors) as you like, but start every name with the unit id.
   - The ground, the parvis and the cameras go in the `SITE` collection.

## Deliverables
1. `output/scene.blend` (Blender 4.3):
   - one collection per unit, named exactly with the unit id (for example `N03` or `R02`);
   - one additional `SITE` collection;
   - no unit element may sit in any other collection.
2. `output/renders/`, each image a 1920×1080 PNG:
   - `overview.png`, taken with camera `CAM_OVERVIEW`: a high view from the north-west of the whole cathedral. The west front, the north flyers, the transept and the apse must all be visible.
   - `nave_push.png`, taken with camera `CAM_NAVE`: the camera stands at the west end of the nave, on the axis, at about 1.7 m eye height, looking east along the axis. The continuous high vault and the crossing at the far end must be visible.
   - `chevet.png`, taken with camera `CAM_CHEVET`: an exterior view from due east of the apse, looking west. The apse, the radiating chapels and the crossing tower must be visible.
   - All three cameras go in the `SITE` collection.
3. `output/manifest.json`:
   - The top level is `{"units":[…]}`. Each unit has one entry of the form `{"id","collection","built","params"}`.
   - In `params`, enter the values you read from the sheets and the change order and actually built. Use these fields:

     | Unit type | `params` fields |
     |---|---|
     | Nave bay (N) | `arch_form` (`pointed`/`round`), `pier_type` (`CYL`/`OCT`/`CMP4`/`CMP8`), `triforium_openings_per_side`, `clerestory_lights`, `vault` (`quadripartite`/`tierceron`/`lierne_star`/`groin`), `rib_count` |
     | Aisle segment (L) | `bay_lights` (4 integers, west→east), `bay_heads` (west→east; `TREFOIL`/`QUATREFOIL`/`SEXFOIL`/`PLAIN`), `door_bay` (1–4), `buttress_top_z` |
     | Flyer group (F) | `flyers`: a list of `{grid_line, tiers, pinnacles}` entries, one for each grid line actually built |
     | West tower (T) | `storeys`, `belfry_lancets_per_face`, `spire_pinnacles`, `portal_orders`, `spire_tip_z` |
     | West-front central block (P01) | `portal_orders`, `gallery_niches`, `gable_pinnacles` |
     | Rose window (R01) | `diameter`, `ring_lights` (inner→outer), `oculus_foils` |
     | Transept front (R02/R03) | `portals`, `portal_orders`, `rose_diameter`, `ring_lights`, `oculus_foils`, `turret_sides` |
     | Crossing (X01) | `vault`, `rib_count`, `belfry_openings_per_face`, `tower_pinnacles`, `fleche_tip_z` |
     | Transept bay (E) | `lights_west`, `lights_east`, `triforium_openings_per_side`, `vault`, `rib_count` |
     | Choir bay (Q) | `lights_north`, `lights_south`, `niches_per_side`, `vault`, `rib_count` |
     | Apse (A01) | `sides`, `lights_per_window`, `rib_count` |
     | Chapel (K) | `sides`, `radius`, `lights_per_window`, `roof_tip_z` |

   - The manifest is a declaration only. The actual geometry in `scene.blend` is authoritative.

## Environment and budget
- The environment is an offline container with Blender 4.3 (`blender -b --python` works), Python 3.11, no GPU and no network.
- Any renderer is acceptable, for example Cycles at low samples with denoising, Eevee or Workbench.
- The total time limit is 3600 seconds.
