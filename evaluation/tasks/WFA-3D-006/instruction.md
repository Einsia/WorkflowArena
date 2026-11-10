# WFA-3D-006 — Mechanical Astronomical Clock Tower (cut-away demonstration movement)

## Task
Build, in Blender, a stone Gothic mechanical astronomical clock tower and animate its whole movement.

The south facade carries a group of astronomical dials:
- a main dial with hour and minute hands and an astrolabe at its centre;
- a 24-hour disc on one side and a calendar ring on the other;
- a moon-phase aperture above the main dial.

Above the dial storey is the automata storey: two windows, each with a parade wheel of figures behind it. At the top is the bell storey, where a skeleton striker figure rings the great bell to the beat of a cam.

The east wall is cut away in the movement storey (TW2) and the automata/bell storey (TW3). From the east you look straight into the stacked gear trains behind the wall:
- **Going side:** driven by a weight and great wheel, and regulated by a pendulum through the escapement.
- **Striking side:** a second weight, the striking train and an air-brake fly, which also drive the automata.

The overall look is a stone tower at dusk, with brass gears and painted dials. Materials and lighting are your choice.

The tower consists of 28 construction units. Each unit is governed by its sheet in `input/sheets/`; the change order in `input/changes/` takes precedence over the original sheets.

## Inputs
- `input/sheets/<unit id>.png`: one sheet per unit, 28 in total.
- `input/site/site-plan.png`: general arrangement, with zones, port-arbor coordinates and the coordinate grid.
- `input/site/ports.csv`: port-arbor coordinates.
- `input/site/layers.csv`: gear layer numbers and their y positions.
- `input/site/topology.png`: which units mount parts on which arbor.
- `input/legend.png`: symbols and drawing conventions.
- `input/changes/CO-01.png`: the change order.

## Global rules
### Coordinates and units
- Units are metres, with Z up. The tower axis is at x = 0, y = 0; the ground is at z = 0.
- The front (south) face points to −Y.
- "Front view" means looking from −Y toward +Y, with X to the right and Z up.

### Arbors and gears
- Every arbor is horizontal and parallel to Y.
- Port arbors (`ports.csv`) are fixed points. Every other arbor follows from the gear-train sheets:
  - start from an arbor that is already located;
  - move along the marked mesh azimuth by the standard centre distance m(z₁+z₂)/2 to place the next arbor;
  - the azimuth convention is shown in the legend.
- All gears are external involute spur gears:
  - the tooth count is exact;
  - the tip diameter is m(z+2);
  - the face width is as drawn, with the face mid-plane at the y of the marked layer;
  - the spoke pattern is as drawn.
- Meshing gears share layer and module and sit at the standard centre distance.
- Gears, discs, drums, cams and hands on one arbor are rigidly fixed together.
- Non-meshing gears in the same layer must not interfere.
- Every dial, astrolabe, disc, calendar ring, moon disc and parade wheel is coaxial with the arbor that drives it.

### Animation
- The timeline is frames 1–1440 at 24 fps.
- The movement runs at demonstration speed. There are two reference arbors:
  - **Arbor M** (minute arbor): turns clockwise in front view at a constant rate, one revolution per 120 frames. At frame 1 the main dial reads 10:00, with the minute hand at 12 and the hour hand at 10.
  - **Arbor SB** (strike barrel arbor): turns counter-clockwise in front view at a constant rate, one revolution per 480 frames.
- Every other arbor turns at a constant rate, with speed and direction set by its tooth-count chain. The escape wheel turns continuously, not in steps.
- The pendulum and anchor swing together about the anchor pivot:
  - the period is the small-amplitude period of a simple pendulum of that length, with g = 9.81 m/s²;
  - the amplitude is as drawn, with sinusoidal motion.
- Weights:
  - each rope pays out from its drum, and the weight descends vertically by the arc length the drum turns through;
  - the rope hangs from the side of the drum shown on the sheet.
- Striker figure: each cam lobe passing lifts and drops the arm once; on each drop the hammer touches the outer lip of BL1.
- Keyframes or drivers are both acceptable.

### Naming contract
- One collection per unit, named exactly by the unit id (e.g. `GT4`, `TW3`). Global items such as ground, lights and cameras go in a `SITE` collection.
- Every labelled part on a sheet is its own object, named `<unit id>_<label>`. These are:
  - gears: `GT4_c`, `MP1_ring`, `ES1_escape`, `ES1_anchor`;
  - hands: `DL1_minute`, `DL1_hour`;
  - other moving parts: `AS1_rete`, `DL2_disc`, `CR1_ring`, `MP1_disc`, `PD1_pendulum`, `GT8_fly`;
  - weight parts: `WT1_drum`, `WT1_weight`, `WT2_drum`, `WT2_weight`;
  - automata parts: `AU1_wheel`, `AU2_wheel`, `AU3_cam`, `AU3_arm`;
  - bells: `BL1_bell`, `BL2_bell`.
- The origin of every moving object lies on its rotation axis.
- Countable components can be built either way:
  - one object per item, named `<unit id>_<component>_<nn>`; or
  - one object named `<unit id>_<component>`, with each item as a separate connected piece.

  The component names are:

| Unit | Components |
|---|---|
| TW1 | `door`, `buttress`, `course` |
| TW2 | `window`, `pilaster` |
| TW3 | `opening`, `post` |
| TW4 | `dormer`, `pinnacle` |
| DL1 | `marker`, `tick` |
| AS1 | `star`, `division`, `circle` |
| DL2 | `division` |
| CR1 | `segment`, `medallion` |
| MP1 | `moon`, `star` |
| AU1, AU2 | `fig` |
| BL1, BL2 | `canon`, `hammer` |
| WT2 | `disc` |
| GT8 | `vane` |

## Deliverables
1. `output/scene.blend` (Blender 4.3):
   - metric units, unit scale 1.0;
   - all 28 unit collections plus `SITE`;
   - animation on the timeline, frames 1–1440 at 24 fps.
2. `output/renders/`, three 1920×1080 PNGs:
   - `overview.png`: frame 1, from the south-east and about 25° above, showing the whole tower including the spire, with the cut-away movement visible.
   - `cutaway.png`: frame 1, a level view from the east into the cut-away TW2/TW3, framed on the gear trains.
   - `front_dials.png`: frame 721, square-on to the south facade, framing all dials, the moon aperture and both automata windows.
3. `output/manifest.json`:
   - an array with one entry per unit: `{"id","collection","built":true|false,"params":{...}}`.
   - `params` fields:
     - gear trains `GT*`: `teeth` (gear label → teeth), `module_mm` (label → module), `arbor_xz` (arbor → [x,z]), `omega_deg_per_frame` (arbor → degrees per frame, clockwise in front view positive).
     - `DL1`: `hour_markers`, `minute_ticks`, `minute_hand_len`, `hour_hand_len`.
     - `AS1`: `star_pointers`, `zodiac_divisions`, `tympan_circles`.
     - `DL2`: `diameter`, `divisions`, `numerals`.
     - `CR1`: `segments`, `medallions`.
     - `MP1`: `ring_teeth`, `moons`, `stars`.
     - `ES1`: `escape_teeth`, `anchor_pivot_xz`.
     - `PD1`: `length`, `period_frames`.
     - `WT1`, `WT2`: `drum_d`, `rope_side`, `drop_m`.
     - `BL1`, `BL2`: `lip_d`, `canons`, `hammers`.
     - `AU1`, `AU2`: `figures`.
     - `AU3`: `cam_lobes`, `strikes`.
     - `TW1`–`TW4`: counts of the countable components on the sheet, keyed by the component names in the table above.
4. Optional: `output/preview.mp4`, 640×360, an animation preview of at most 10 s.

## Environment and rules
- Offline container with Blender 4.3 (`blender -b --python` available), Python 3.11 and no GPU. Any renderer may be used.
- The wall-clock budget is 3600 s. Save a valid `scene.blend` early, then keep improving it.
- No network access and no downloaded assets. Do not read files outside this task's inputs.
- Grading is based on measurements of `scene.blend`. `manifest.json` is only your declaration; mismatches with the measured scene lose credit.
