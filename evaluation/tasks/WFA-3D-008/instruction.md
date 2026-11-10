# Qinglan Junction — large-scale railway landscape build

## Scene
Build, in Blender at 1:1 real-world scale, a finely detailed railway landscape junction in the spirit of a high-end model railway layout: clean ballast and rails, rows of catenary masts, colour-light signals, platforms with canopies, an old-style masonry station building, and a line that runs through a hill tunnel and crosses a creek and the East River. Three distinct trains run over the network to a timetable, entering platforms, dwelling and departing. Sunny afternoon; from above, every district reads clearly.

The network consists of a counter-clockwise main loop, two station tracks in the hub yard, and a branch that leaves the east throat of the yard, passes through a tunnel, crosses the river and ends at a terminus station.

## Inputs
- `input/sheets/<ID>.png`: one drawing sheet per construction unit, 32 sheets. Each unit is built as shown on its sheet.
- `input/changes/CO-01.png`: change order; it takes precedence over the original sheets and timetable.
- `input/site/network.png`: network topology schematic and site control point (not to scale).
- `input/site/topology.csv`: end-to-end connections between track sections and turnouts.
- `input/site/placement.csv`: placement of platforms, station buildings, signals, tunnel portals and bridges (reference section, measure, chainage, side).
- `input/site/timetable.csv`: train timetable (frame numbers).
- `input/legend.png`: drawing symbols and left/right conventions.

Unit IDs: track sections T01–T12, simple turnouts D01–D03, platforms P01–P03, station buildings S01–S02, tunnel portals G01–G02, bridges B01–B02, colour-light signals X01–X05, trains R1–R3.

## Global rules
1. **Coordinates and units**: metric, unit scale 1.0; X east, Y north, Z up. Control point and East River position: see `network.png`.
2. **Track geometry**: each track section is the sequence of tangents (`TANGENT`) and circular arcs (`CIRC. CURVE`) in the sheet's `ALIGNMENT TABLE`; the sheet plan uses a local frame with the section start at the origin and the start tangent along +x. Sections and turnouts join end-to-end as listed in `topology.csv`, with continuous plan position, tangent direction and rail-top elevation at every joint. Rail-top elevation varies linearly with chainage inside a section. Gauge 1.435.
3. **Turnouts**: the through route is straight; the diverging route is a single circular arc starting at the switch toe, with radius and angle as on the sheet.
4. **Placement rules** (`placement.csv`); `side` is left/right looking in the direction of increasing chainage of the reference section.
   - Platform: the platform midpoint lies on the track normal at the given chainage; the platform edge nearest the track is 1.75 from the track centreline; platform-top height above the local rail top is on the sheet.
   - Station building: front façade parallel to the adjacent track at `facade_offset_m` from the track centreline; plan midpoint on the normal at the given chainage.
   - Signal: mast centre 2.50 from the track centreline.
   - Catenary mast: centre 3.00 from the track centreline, on the side shown on the sheet.
   - Tunnel portal: opening centreline on the track centreline; end-wall face perpendicular to the local track tangent. The hill covers the line between G01 and G02.
   - Bridge: bridge centreline on the track centreline, bridge mid-length at the given position; deck top 0.35 below rail top.
5. **Trains and animation**: 24 fps, frame range 1–1440. All three trains run on the track; every vehicle stays on the track centreline, aligned with the track tangent, in the consist order shown on the sheet.
   - Dwell: from the arrival frame to the departure frame (inclusive) the train is stationary with its mid-length aligned, along the track, with the platform midpoint. An empty arrival frame means the train is already at that platform on frame 1; an empty departure frame means it stays until frame 1440.
   - Routes: R1 runs the main loop through yard track T01 (counter-clockwise); R2 runs the main loop through yard track T02 (counter-clockwise); R3 runs from the terminus over the branch and the diverging route of D03 into track T01 to call at P01, then returns the same way to the terminus.
6. **Site elements**: terrain, East River and creek water, the hill, buffer stop, lights, cameras etc. go into collection `SITE`.

## Deliverables
Offline container: Blender 4.3 (`blender -b --python` available), Python 3.11, no GPU, 3600 s budget. Any render engine.

1. `output/scene.blend`
   - One collection per unit whose name is exactly the unit ID (e.g. `T07`, `G02`, `R3`); site elements in `SITE`.
   - Object naming (`<ID>` = unit ID; countable parts may be separate objects or separate mesh islands within one object):

     | Unit | Required objects |
     |---|---|
     | Track section | `<ID>_AXIS`: curve object along the track centreline at rail-top elevation (world space); `<ID>_MAST_*`: catenary masts; `<ID>_SLEEPERS*`: sleepers (material colour per legend: timber dark brown, concrete light grey) |
     | Turnout | `<ID>_AXIS_MAIN`, `<ID>_AXIS_DIV`: through / diverging centreline curves; `<ID>_MACHINE`: point machine |
     | Platform | `<ID>_DECK`; `<ID>_COL_*`: canopy columns; `<ID>_BENCH_*`: benches |
     | Station building | `<ID>_BODY`; `<ID>_ROOF`; `<ID>_OPENING_*`: front-façade door/window openings (one per bay per storey); `<ID>_TOWER` if there is a clock tower |
     | Signal | `<ID>_MAST`; `<ID>_LAMP_*`: lamps numbered top to bottom with materials of the matching colour; `<ID>_LADDER` if a ladder is shown |
     | Tunnel portal | `<ID>_PORTAL`: end wall with opening; `<ID>_VOUSSOIR_*`: arch stones; `<ID>_WING_*`: wing walls |
     | Bridge | `<ID>_DECK`; `<ID>_PIER_*`: piers; truss diagonals `<ID>_DIAG_*` for steel trusses; arch barrels `<ID>_ARCH_*` for stone arches |
     | Train | `<ID>_V01`, `<ID>_V02`, …: one object per vehicle (children allowed), origin at rail-top level directly below the body centre, local +X along the vehicle length; wheelsets of the locomotive or leading railcar `<ID>_V01_AXLE_*` |

2. `output/renders/`
   - `overview.png`: 1920×1080, high oblique view showing the whole network and all three trains;
   - `hub.png`: 1280×720, yard close-up showing P01, P02, S01 and at least one train at a platform;
   - `terminus.png`: 1280×720, view of B02 and the terminus from the downstream side of the East River.
3. `output/manifest.json`: an array with one entry per unit `{"id", "collection", "built", "params"}`. `params` holds what you read from the sheets and actually built:
   - Track section: `elements` (array of `{"type":"straight","length"}` or `{"type":"arc","radius","angle_deg","dir":"L"|"R"}`), `z_start`, `z_end`, `masts`, `mast_side` (`"L"`/`"R"`), `sleeper` (`"wood"`/`"concrete"`)
   - Turnout: `hand`, `frog`, `radius`, `angle_deg`, `machine_side`
   - Platform: `length`, `width`, `height`, `canopy` (`"none"`/`"single"`/`"double"`), `canopy_columns`, `benches`
   - Station building: `length`, `depth`, `floors`, `bays`, `roof` (`"hip"`/`"gable"`/`"flat"`), `clock_tower`
   - Signal: `aspects`, `colors` (top to bottom, e.g. `["G","Y","R"]`), `ladder`, `height`
   - Tunnel portal: `shape` (`"semicircular"`/`"horseshoe"`), `voussoirs`, `wing_walls` (`"splayed"`/`"straight"`)
   - Bridge: `type` (`"warren_through"`/`"stone_arch_deck"`), `spans`, `panels_per_span`, `piers`
   - Train: `n_vehicles`, `loco_axles`, `vehicle_lengths`, `colors` (hex)

   The manifest is a declaration only; the geometry and animation in the `.blend` are authoritative.
4. Optional: `output/preview.mp4`, 640×360, at most 10 s animation preview.

Local offline tools only; no network access or downloaded assets.
