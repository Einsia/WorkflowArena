# WFA-3D-007 — Star Lake Theme Park

## Task
Build a complete theme-park scene in Blender 4.3. The park's 12 rides must all run at the same time on one shared timeline.

The park covers roughly 300 m × 275 m. The style is bright and saturated, in clear late-afternoon weather.

The central axis runs south to north:
- the entrance gate and entrance plaza;
- a ring plaza around a fountain;
- a lake with a bandstand on its island.

A perimeter promenade encloses the core. The east, west and north wings hold the rides: Ferris wheels, carousels, a swinging ship, a drop tower, chain swings, teacups, a giant frisbee and a gyro observation tower. Kiosks stand along the promenade.

The park has 26 construction units:
- rides R01–R12;
- park units G01, V01, F01, M01, K01–K05, L01, B01, B02, P01 and H01.

Build each unit to its sheet in `input/sheets/`. The change order in `input/changes/` takes precedence over the original sheets and the original site plan.

## Inputs
| Path | Content |
|---|---|
| `input/site/site-plan.png` | Site plan (original state) |
| `input/site/placement.csv` | Ride pads (`ride_pad`) and park-unit anchor points (`park_unit`), with azimuths |
| `input/site/paths.csv` | Path centerlines and widths |
| `input/sheets/<ID>.png` | One construction sheet per unit |
| `input/legend.png` | Symbol legend shared by all sheets |
| `input/changes/CO-01.png` | Change order |

## Global rules

### Coordinates and units
- Meters, with Z up, X east and Y north.
- Ground is at 0.00.
- Paths, the plaza ring, the island and the bridge heads all have their surface at +0.05.
- Azimuths are measured from +X, counter-clockwise positive, in degrees.

### Ride placement
- The plan origin on a ride's sheet is the ride center. Place it on the ground at the center of its pad.
- Align the sheet's local +X axis (the entrance direction) with the pad's facing azimuth.
- Pads are assigned to rides by the `initial_unit` column, unless the change order says otherwise.

### Park-unit placement
Place the plan center of each park unit at its point in `placement.csv`. The meaning of `facing_or_rot_deg` depends on the unit:

| Units | Meaning |
|---|---|
| G01, V01, H01, K01–K05 | Azimuth of the main facade's outward normal (the south elevation for the gate; the service/entrance facade for the others) |
| B01, B02 | Azimuth of the bridge axis |
| F01, M01, L01, P01 | Not rotated |

### Paths
- `segment`: a straight strip of the given width along the centerline, with square ends.
- `ring`: an annulus with centerline radius r around (cx, cy).
- Path surfaces are at +0.05.

### Entrances and entrance spurs
Each ride has an entrance point on its local +X axis, at distance R + 2.0 from the ride center. R is the safety-envelope radius on that ride's sheet. The entrance point's height is +0.05.
- Mark the entrance point with an empty named `<ID>_ENTRY`.
- Each entrance spur is a straight path 3.0 m wide. It runs from the entrance point along the ride's facing direction until it meets the centerline of the perimeter promenade (E03–E07).

### Safety envelopes
Every part of a ride must stay inside the safety envelope on its sheet at every frame. The envelope is a cylinder with plan radius R and height H, measured from the ground.

Horizontal clearance between the envelopes of any two rides is at least 3.0 m.

Horizontal clearance from an envelope to the edge of any path, entrance spur or bridge deck is at least 1.5 m. A ride's own entrance spur is exempt.

### Lake and bridges
- The whole island is paved and walkable.
- Each of B01 and B02 meets the end of E08/E09 at one end and the island at the other. Each bridge head is flush with the surface it meets.
- Starting from the gate passage, a pedestrian can reach all 12 ride entrances and the island.

### Cancelled units
A unit cancelled by the change order keeps an empty collection with its ID, and gets `built:false` in the manifest.

## Animation
- Timeline: 24 fps, frames 1–720 (30 s).
- All 12 rides run at the same time from frame 1, as specified on their sheets, with t = (frame − 1) / 24 s.
  - Frame 1 is the start pose shown on the sheet.
  - Rotations are uniform.
  - Swings follow the sinusoid given on the sheet.
  - Lifts cycle through the piecewise-linear profile drawn on the sheet.
- Reading rotation directions:
  - vertical-axis rides are read from above;
  - Ferris wheels are read from the entrance;
  - the frisbee disc is read as noted on its sheet.
- Ferris-wheel gondolas stay upright at all times.
- You may use keyframes, drivers or constraints. The motion must live on the scene timeline, so that world transforms can be evaluated at any frame.

## Naming contract
- One collection per unit, named exactly the unit ID, e.g. `R07` or `K03`.
- Global items go in the `SITE` collection:
  - the ground;
  - paths `PATH_<path_id>`;
  - entrance spurs `SPUR_<rideID>`.
- Name moving parts as noted on each sheet:
  - `<ID>_MAIN`;
  - `<ID>_CAR01…`, `<ID>_HORSE01…`, `<ID>_SEAT01…` and `<ID>_SUB01…`.
- Put the entrance empty `<ID>_ENTRY` in the ride's own collection.

## Deliverables (in `output/`)
1. **`scene.blend`**: opens in Blender 4.3. Metric units with Unit Scale 1.0, frame range 1–720, 24 fps.
2. **Renders**: three images, each 1920×1080 at frame 361.
   - `renders/overview.png`: a high bird's-eye view of the whole park from the south-west, looking down at about 35°–50°. The gate and all 12 rides must be in frame.
   - `renders/wing_east.png`: from above the island, looking east over the east wing. The rides on the three east pads and on pad PE4 must be in frame.
   - `renders/lake.png`: from about 15 m above the south axis path, looking north. The lake, both bridges and the bandstand must be in frame.
3. **`manifest.json`**: an array with one entry per unit:
   ```json
   {"id":"R01","collection":"R01","type":"FW","built":true,
    "params":{"x":…, "y":…, "rot_deg":…, …}}
   ```
   - `x`, `y` and `rot_deg` are the placement you actually used.
   - Fill the remaining fields from the sheets, with the change order applied, using the table below.

| type | Units | params fields |
|---|---|---|
| FW Ferris wheel | R01 R07 | `diameter_m, hub_height_m, gondolas, gondola_type(open/closed), period_s, direction(cw/ccw)` |
| CR Carousel | R02 R09 | `diameter_m, horses_per_row(array, outer→inner), roof, period_s, direction, bob_per_rev` |
| PS Swinging ship | R03 | `pivot_height_m, arm_m, hull_length_m, seat_rows, amplitude_deg, period_s` |
| DT Drop tower | R04 | `tower_height_m, faces, seats_per_face, cycle_s` |
| CS Chain swing | R05 R10 | `tower_height_m, seat_type(double/single), seats, fly_angle_deg, period_s, direction` |
| TC Teacups | R06 R11 | `platter_diameter_m, sub_platters, cups_per_sub, canopy(true/false), main_period_s, sub_period_s` |
| FB Giant frisbee | R08 | `pivot_height_m, arm_m, amplitude_deg, period_s, seats, disc_period_s, disc_direction` |
| RT Gyro tower | R12 | `mast_height_m, seats, cycle_s, spin_period_s, spin_direction` |
| G Gate | G01 | `width_m, arches, towers, spire` |
| V Visitor center | V01 | `storeys, roof, bays` |
| F Fountain | F01 | `basin_diameter_m, tiers, jets` |
| M Clock tower | M01 | `height_m, tiers, clock_faces` |
| K Kiosk | K01–K05 | `roof, windows, awning_stripes (awning only)` |
| L Lake | L01 | `water_level_m, island_radius_m` |
| B Footbridge | B01 B02 | `deck_width_m, form(beam-3span/arch), rail_posts_per_side` |
| P Bandstand | P01 | `sides, roof` |
| H Restaurant | H01 | `roof, bays` |

For form values, use the English words from the legend: `onion`, `cone`, `scallop`, `hip`, `gable`, `awning`, `ogee`, `arch` and `beam-3span`.

`manifest.json` is only your declaration. Review is based on measurements of `scene.blend`.

## Environment and rules
- Offline container with Blender 4.3 (`blender -b --python` is available) and Python 3.11. There is no GPU.
- Choose any render engine and sample count.
- The wall-clock budget is 3600 s. Save a valid set of deliverables early, then keep improving it.
- No network access and no downloaded assets. Generate all geometry and materials locally.
- Do not read any files other than this task's inputs.
