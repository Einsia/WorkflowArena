# WFA-3D-010 Age-of-Sail Harbour and Fleet

## Task
Build, in Blender 4.3, a European merchant-and-naval harbour of the age of sail (around 1800), and berth a fleet of 10 sailing ships in it.

**Harbour components:**
- three vertical masonry quays, each with a timber pile pier;
- a rubble-mound breakwater with a red-and-white lighthouse on its head;
- treadwheel cranes and sheer legs on the quays;
- a row of multi-storey brick warehouses behind the quays;
- a masonry graving dock at the west end.

**Fleet:** the ships carry different rigs — full-rigged ship, barque, brig, schooner, ketch, sloop and others. All sails are set (drying), so each rig can be read at a glance.

**Look and feel:** warm afternoon sun and a lightly glittering sea. The scene should feel grand, with clearly separated zones and believable scale.

## Inputs
- `input/site/site-plan.png`: site plan.
- `input/site/units.csv`: anchor points and headings of harbour units.
- `input/site/berths.csv`: berths — fender lines, berth marks, water-side normals and bow headings.
- `input/site/berth_assignment.csv`: which berth each ship uses.
- `input/sheets/<ID>.png`: one drawing sheet per unit. **Each unit follows its sheet in `input/sheets/`; the change order in `input/changes/` (`CHANGE ORDER CO-01`) overrides the original sheets and `berth_assignment.csv`.**
- `input/legend.png`: symbol legend and rig classification rules (`RIG CLASSIFICATION` table).

## Units (26)

| IDs | Type |
|---|---|
| S01–S10 | ships |
| Q01–Q03 | quays |
| P01–P03 | piers |
| B01 | breakwater |
| L01 | lighthouse |
| C01–C02 | treadwheel cranes |
| C03 | sheer legs |
| W01–W04 | warehouses |
| D01 | graving dock |

## Coordinates, units and datums
- Metres, Z up, +X east, +Y north.
- Mean sea level is Z = 0, and the water surface lies on this plane.
- Harbour bed is at −8.00; the land platform is at +3.50.
- The shoreline (quay face lines) is at y = 0, with water on the −Y side.
- Sheet elevations use the datum stated on each sheet: ship sheets use the design waterline (DWL); harbour works use mean sea level; cranes, lighthouse and warehouses use their own base level.

## Global rules
1. **Berthing.** Each ship lies at its assigned berth and meets all four conditions:
   - its centreline is parallel to the berth fender line;
   - its bow points along `bow_heading_deg` (counter-clockwise from +X);
   - its midship section (mid-length of hull length L) passes through the berth mark;
   - the clear gap between the hull's maximum breadth and the fender line is 1.5 m.
2. **Draft.** With the ship upright, the DWL coincides with the water surface and the keel bottom is at Z = −T.
3. **Harbour joints.**
   - A pier's root end bears on its host quay's face line, and its deck top is flush with that quay's coping.
   - Cranes and sheer legs stand with their base on the coping of their host quay.
   - Warehouses stand on the land platform.
4. **Lighthouse.** The tower axis passes through the centre of the B01 head, and the tower base is the head's top surface.

**Ship dimension definitions:**
- L: hull length, excluding the bowsprit.
- B: maximum breadth.
- f: freeboard to the gunwale at midship.
- Mast height h: measured from the DWL to the masthead.
- Mast position a: measured from the stern end along the centreline.
- Gun ports: symmetric on both sides; sheets show the starboard side only.

## Naming contract
- **Collections.** One collection per unit, named exactly with the unit ID (e.g. `S07`, `W03`).
  - Global items (water, terrain, land, cameras, lights) go in `SITE`.
  - Child collections are allowed. No unit's objects may also appear in another unit's collection.
- **Ships `<ID>`:**
  - `<ID>_ROOT`: an empty at the intersection of the DWL, the centreline and the midship section. Local +X points to the bow, +Z up. Every ship object is parented (directly or indirectly) to it.
  - `<ID>_HULL`: the hull, a single mesh object without masts, spars, sails or bowsprit.
  - `<ID>_MAST_<n>`: masts, with n = 1 at the foremost mast.
  - `<ID>_YARD_<n>_<k>`: yards on mast n, with k counted from the bottom.
  - `<ID>_GAFF_<n>`: the gaff of the gaff sail on mast n.
  - `<ID>_JIB_<k>`: headsails.
  - `<ID>_BOWSPRIT`: bowsprit.
  - `<ID>_PORT_S_<k>` / `<ID>_PORT_P_<k>`: one object per gun port, starboard / port side.
  - Sail mesh names are free.
- **Quays:** `<ID>_WALL` (quay body), `<ID>_BOLLARD_<k>`, `<ID>_STAIR_<k>`.
- **Piers:** `<ID>_DECK` (deck, including any pier head), `<ID>_PILE_<k>` (one object per pile).
- **Breakwater:** `B01_MOUND` (mound, including the head), `B01_PARAPET_<k>` (one object per parapet segment).
- **Lighthouse:**
  - `L01_TOWER`: the tower, without gallery or lantern.
  - `L01_BAND_<k>`: one object per red band.
  - `L01_WINDOW_<k>`: tower windows.
  - `L01_ROTOR`: the rotating part; its local +X points along `BEAM 1` (as on sheet L01).
  - `L01_BEAM_<k>`: visible beam volumes, parented to `L01_ROTOR`.
- **Treadwheel cranes:** `<ID>_HOUSE`, `<ID>_WHEEL_<k>`, `<ID>_JIB`.
- **Sheer legs:** `C03_LEG_<k>`, `C03_BACKSTAY_<k>` (including its ground anchor).
- **Warehouses:**
  - `<ID>_BODY`: walls.
  - `<ID>_ROOF`: roof.
  - `<ID>_WIN_<k>`: front-facade windows.
  - `<ID>_DOOR_<k>`: front loading doors.
  - `<ID>_HOIST_<k>`: hoist beams.
- **Graving dock:** `D01_BASIN` (dock body with altars), `D01_KEELBLOCK_<k>`, `D01_GATE_<k>` (one object per gate leaf).
- **Water:** `SITE_WATER`, covering the basin and the sea outside the breakwater.

## Animation
- Timeline: frames 1–240 at 24 fps.
- **Ship roll.** Each `<ID>_ROOT` rolls sinusoidally about its own local X axis.
  - Amplitude 2.0°; period equal to the `ROLL PERIOD Tr` on the ship's sheet.
  - Upright at frame 1.
  - Ships make no other rigid-body motion.
- **Lighthouse rotation.** `L01_ROTOR` rotates uniformly about the tower axis. Direction, period (`LIGHT ROTATION PERIOD`) and the beam bearing at frame 1 (`BEAM PLAN`) follow the sheet.

## Deliverables
- **`output/scene.blend`:**
  - opens directly in Blender 4.3;
  - metric units, unit scale 1.0;
  - follows the naming contract and animation rules above.
- **Three 1920×1080 PNGs in `output/renders/`:**
  - `overview.png`: an oblique aerial view from above the south-east of the basin, with all 26 units in frame;
  - `central_quay.png`: from just above the water (eye height ≤ 6 m) due south of the central quay, looking north, with the ships at both sides of P01 and along the Q02 face in frame;
  - `lighthouse.png`: from inside the harbour towards the B01 head and L01, with at least one beam visible.
- **`output/manifest.json`:** of the form `{"units":[{"id":"S01","collection":"S01","built":true,"params":{...}}, ...]}`, with 26 entries. The `params` fields for each type are:
  - Ship:
    - `rig_type`: from the left column (`rig_type`) of the legend's `RIG CLASSIFICATION` table;
    - `masts`;
    - `yards_per_mast`: a list ordered from the bow;
    - `gaff_masts`: a list of mast numbers;
    - `jibs`;
    - `ports_per_side`;
    - `gun_decks`;
    - `loa_m`, `beam_m`, `draft_m`;
    - `berth`;
    - `roll_period_s`.
  - Quay: `length_m`, `coping_m`, `bollards`, `stairs`.
  - Pier: `length_m`, `width_m`, `bents`, `piles`, `deck_top_m`.
  - Breakwater:
    - `length_m`, `crest_m`, `segments`;
    - `parapet_side`: `seaward` or `harbour`.
  - Lighthouse:
    - `section`: `round`, `hexagon` or `octagon`;
    - `tower_h_m`, `red_bands`, `windows`, `beams`, `period_s`, `beam1_azimuth_deg`.
  - Treadwheel crane:
    - `wheels`, `wheel_diam_m`;
    - `roof`: `gable` or `pyramid`;
    - `jib_len_m`, `jib_heading_deg`.
  - Sheer legs: `leg_len_m`, `foot_spread_m`, `rake_deg`, `backstays`.
  - Warehouse:
    - `bays`, `floors`;
    - `roof`: `gable`, `hipped` or `gambrel`;
    - `hoists`, `eave_h_m`, `ridge_h_m`.
  - Graving dock:
    - `length_m`, `altars`, `keel_blocks`;
    - `gate`: `mitre` or `caisson`.

  The manifest is a declaration only. The scene is judged by the actual geometry and animation in `scene.blend`.
- **Optional:** `output/preview.mp4`, 640×360, ≤ 10 s.

## Environment and rules
- Offline container: Blender 4.3 (`blender -b --python` is available), Python 3.11, no GPU.
- Any render engine is allowed — for example Cycles at low samples with denoising, Eevee or Workbench.
- Time budget: 3600 s.
- No network access and no downloaded models or textures; all geometry and materials must be generated locally.
