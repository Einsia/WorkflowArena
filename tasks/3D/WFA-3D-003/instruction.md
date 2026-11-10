# WFA-3D-003 — Final assembly of the modular orbital station "Tianshu"

## Task
Assemble the complete low-Earth-orbit station "Tianshu" in Blender and produce a 10-second on-orbit animation: the solar arrays track the Sun, the radiators stay edge-on to the Sun, and a cargo vehicle approaches along its docking axis and docks.

The station consists of 28 construction units:
- nodes N1–N3;
- laboratory modules L1–L5;
- airlock K1;
- truss segments T1–T5;
- solar array wing assemblies S1–S4;
- radiators R1–R4;
- robotic arms A1–A2;
- visiting vehicles V1–V3;
- exposed facility E1.

The style is realistic near-future crewed spacecraft:
- white MLI-covered pressurized modules;
- aluminium trusses;
- deep-blue solar blankets;
- white radiator panels.

The background is black space; an Earth limb at the bottom of the frame is welcome. The station should read as an engineered structure on a vast scale.

Each unit follows its sheet in `input/sheets/`; the change order in `input/changes/` takes precedence over the original sheets.

## Inputs
- `input/sheets/<unit id>.png`: one spec sheet per unit. Each sheet gives the unit's dimensions, port table and external parts in its **local frame**.
- `input/site/topology.csv`, `input/site/topology.png`: connections between units, written as parent.port ↔ child.port. The diagram shows neither orientation nor scale.
- `input/legend.png`: symbol legend for all sheets, including the codes for counted parts (written as `code WIN`, etc.).
- `input/changes/CO-01.png`: engineering change order, with the attachment `CO-01-N2B.png`.

## Global rules
1. **Frames and units**
   - Units are metres, and Z is up.
   - The station frame is the local frame of N1, with its origin at the local origin on the N1 sheet.
   - Read each sheet's local origin and axes from the axes drawn on that sheet.
2. **Port mating**
   - Each pair of connected ports must mate coaxially: the face centres coincide, the outward normals are opposite, and the key directions are equal.
   - Berthing ports (B) mate only with B ports, and docking ports (D) mate only with D ports.
   - Every unit's position and attitude follows from N1 through the chain of connections.
3. **Sun direction**
   - In the station frame, the unit vector toward the Sun at frame f is S(f) = (cos β·cos φ, sin β, cos β·sin φ).
   - Here β = 15° and φ = 20° + 0.6°·(f − 1).
4. **Animation**
   - The animation runs at 24 fps over frames 1–240.
   - **Solar arrays:** the cell-side normal of every blanket tracks the Sun.
     - With a single-axis gimbal, the normal may rotate only about α; it takes the direction with the smallest angle to S(f).
     - With a two-axis gimbal, the normal equals S(f).
   - **Radiators:** the panel stack rotates about its own rotary axis so that the panel normal stays perpendicular to S(f), keeping the panels edge-on.
   - **Visiting vehicle V2:**
     - At frame 1, it is 40 m out along the outward normal of its berth port, already in its docked attitude.
     - It then approaches in a straight line along the port axis at constant speed and docks at frame 180.
     - It remains stationary from frame 180 to 240.
   - All other units are static. The robotic arms hold the poses given on their sheets.
5. **Global items**
   - The Sun is a sun light `SUN` in collection `SITE`. Its local +Z points to S(f) at every frame, so light travels along −S(f).
   - Cameras `CAM_OVERVIEW`, `CAM_STBD` and `CAM_FWD` are also in `SITE`.

## Naming contract (scene.blend)
- **Unit collections:** each unit has one collection named exactly with its id, for example `N1` or `T4`. Global items go in `SITE`.
- **Root empty:** each unit has a root empty `<id>_ROOT`.
  - Its world transform equals the pose of the unit's sheet frame in the station frame, with no scale.
  - All other objects of the unit are parented under it, directly or indirectly.
- **Main structure mesh:** name it `<id>_BODY`. It is:
  - the shell of a node, lab, airlock or vehicle;
  - the truss frame of a truss segment;
  - the solar array base;
  - the radiator mast;
  - the facility deck;
  - the arm pedestal.
  - In every case `<id>_BODY` is the bare main structure only. Port collars and flanges, docking mechanisms, nozzles and every other attached part are separate objects, so the extent of BODY equals the sheet dimensions (L, D, W, H).
- **Ports:** every port, connected or not, is an empty `<id>_P<n>`. It sits at the port face centre, with local +Z as the outward normal and local +Y as the key.
- **Counted parts:** each part that has a code in the legend is a separate object named `<id>_<code>_<nn>`, for example `L2_WIN_03`, `T1_BAY_04` or `S3_SEG_12`. Each solar segment `SEG` is parented to its blanket `BLANKET`.
- **Solar blankets:** `<id>_BLANKET_<nn>`, with local +Z as the cell-side normal.
- **Radiator panels:** `<id>_PANEL_<nn>`, with local +Z as the panel normal.
- **Robotic arms:** the end-effector mesh is `<id>_EFFECTOR`, and an empty `<id>_EE` sits at the centre of the end-effector face.

## Deliverables
1. **`output/scene.blend`**
   - It opens directly in Blender 4.3.
   - It uses metric units with unit scale 1.
   - The animation is on the timeline.
2. **`output/renders/`** (1920×1080 PNG)
   - `overview.png`: frame 240, from `CAM_OVERVIEW`. It shows the whole station with every unit in frame.
   - `stbd_truss.png`: frame 240, from `CAM_STBD`. It is a close view of the starboard truss and both of its solar wing assemblies.
   - `forward.png`: frame 180, from `CAM_FWD`. It shows the forward modules with V2 just docked.
   - Optional: `preview.mp4`, 640×360, covering frames 1–240.
3. **`output/manifest.json`**
   - The format is `{"units":[{"id","collection","built","params":{...}}]}`, with 28 entries.
   - `params` holds the values you read from the drawings and actually built, with the change order applied.
   - The fields for each unit type are:

| Type | params fields |
|---|---|
| Node N | `length_m, diameter_m, port_count, ring_count` |
| Lab L | `length_m, diameter_m, window_count, payload_sites` |
| Airlock K | `length_m, diameter_m, tank_count` |
| Truss T | `length_m, bay_count, bracing` (`"X"` or `"warren"`) |
| Solar S | `blanket_length_m, blanket_count, segments_per_blanket, gimbal` (`"1-axis"` or `"2-axis"`) |
| Radiator R | `panel_count, panel_length_m` |
| Arm A | `dof, end_effector` (`"snare"` or `"gripper"`) |
| Vehicle V | `length_m, diameter_m, solar_wings, rcs_quads` |
| Facility E | `slots_total, slots_occupied` |

The manifest is only your declaration. The review measures scene.blend itself and checks the manifest against it.

## Environment and rules
- **Environment:** an offline container with Blender 4.3 (`blender -b --python` available), Python 3.11 and no GPU.
- **Rendering:** any renderer is allowed: Cycles with low samples plus denoising, Eevee, or Workbench.
- **Budget:** 3600 s wall clock. Save a valid deliverable early, then refine it.
- **Restrictions:** no network access and no downloaded assets. Do not read files outside this task.
- **Terminology:** spacecraft terms (node, truss bay, gimbal, end effector, RCS quad, etc.) carry their usual industry meaning.
