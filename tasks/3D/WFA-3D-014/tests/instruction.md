# WFA-3D-014 — Night Shift / Rack C Collapse

## Task
Make a 30-second, five-shot, 16:9 photoreal short. In aisle C of a warehouse on the night shift, a forklift with empty forks reverses and the rear of its overhead guard clips a rack upright. The upright shudders; cartons on the top-level pallet slide out, topple and crash onto the aisle floor. Down the aisle, a picker lets go of her picking cart and backs off behind the yellow safety line; the radio on her belt carries the dispatcher's question, and she raises the radio to answer. Tell the story through picture and sound only — no subtitles or explanatory title cards.

This is a 3D scene you build yourself, not a stock-footage edit. Scene identity, dimensions and layout are in input/scene.json and input/layout.svg (the SVG is a layout reference only); the two English lines are in input/transcript.en.txt. input/ contains only two raw noise files; every other sound and both lines must be made by you.

## Shots and edit
30 fps. The five shots start nominally at 0, 6, 11, 18 and 24 s; the film ends at 30 s.

| Shot | Content | Size / angle | Movement / optics |
|---|---|---|---|
| S1 0–6 s | Aisle C, the forklift reversing with its reverse alarm sounding; at the far end the picker pushes her cart | Extreme wide shot, high angle | Locked-off, wide lens |
| S2 6–11 s | Rear of the forklift and the driver looking back; the overhead guard strikes the upright and the forklift stops dead | Medium close-up, low angle | Tracking truck |
| S3 11–18 s | Top-level pallet: cartons slide out, topple and fall one after another toward the aisle floor | Medium shot, looking up | Locked-off, long lens |
| S4 18–24 s | The picker lets go of the cart and backs off behind the safety line; the dispatcher's voice comes over the radio | Medium shot, eye level | Panning follow |
| S5 24–30 s | Back to the S1 set-up: scattered cartons, the stopped forklift; the picker raises the radio and answers | Extreme wide shot, high angle | Locked-off (re-uses CAM_S1) |

Four transitions:

- **T12 (6.0 s)**: match on action, cutting on the forklift's reversing move; the reverse alarm runs continuously across the cut.
- **T23 (11.0 s)**: hard cut.
- **T34 (18.0 s)**: hard cut.
- **T45 (24.0 s)**: sound bridge. The dispatcher's radio line starts inside S4, runs across the cut and finishes in S5.

No other cuts, freezes, speed changes, graphic overlays or inserts, and no jump cuts anywhere in the film. Action timing outside the edit points is yours to plan, but every action must actually happen in the rendered picture and sound and be recorded truthfully in events.csv.

## Production requirements
- Build and render offline in Blender 4.3, at the true metric scale given in scene.json. The picture must look photoreal, with believable materials, lighting and shadows. Flat shading, cartoon looks, cards or untextured geometry do not qualify.
- Both the driver and the picker are rigged, with independently animated fingers.
- The carton collapse is a rigid-body physics simulation; ship the simulation cache with the project.
- Both lines are natural, intelligible English speech produced offline. The dispatcher is heard only through the radio. No online TTS, paid services or imitation of real people's voices.
- Sound perspective must match the camera set-ups; music may not be used to cover missing action sounds.

## Deliverables
1. **base/**: `output.mp4` (H.264, yuv420p, 1280×720, constant 30 fps, exactly 900 frames; AAC stereo 48 kHz; integrated loudness −20 ±2 LUFS, true peak ≤ −1 dBTP), `timeline.json`, `events.csv`, and three stems `stems/{speech,fx,amb}.wav` (48 kHz PCM, 30 s each). The stems, summed with the master gains declared in timeline.json, must equal the mix.
2. **revision/**: the revised version, same contents as base (no events.csv), still 900 frames.
3. **project/**: `scene.blend` (Blender 4.3), build scripts and a `README.md` with the exact export commands; media packed or referenced by project-relative paths. Object names: characters `DRIVER`, `PICKER`, rigs `DRIVER_RIG`, `PICKER_RIG`; props and set `FORKLIFT`, `RACK_C`, `UPRIGHT_C1`…`UPRIGHT_C5`, `PALLET_TOP`, `BOX_01`…`BOX_12`, `CART`, `RADIO`, `SAFETY_LINE`; cameras `CAM_S1`…`CAM_S4` (S5 uses `CAM_S1`). The revision must be generated from the same .blend via the scene custom property `roll_T23_frames` (0 for base, −10 for revision).
4. **timeline.json** (both versions): shot frame ranges and the camera used for each, transitions and audio in/out points, master gains.
5. **events.csv**: header `event_id,frame,description`, containing at least: `upright_contact`, `forklift_stop`, `pallet_tip`, `first_box_release`, `first_floor_hit`, `last_box_rest`, `picker_behind_line`, `radio_raise`, `line_dispatch_start`, `line_dispatch_end`, `line_picker_start`, `line_picker_end`.
6. **credits.md**: the source of every asset and tool, including how the lines were produced. **qa.md**: problems you actually found and fixed, with before/after frame numbers or sample positions; if you found none, say so honestly — do not invent any.

## Revision
Roll T23 ten frames earlier: S2 loses 10 frames, S3 gains 10 frames, total length and transition types unchanged. All other picture and all sound stay unchanged.

## Rules
Local offline environment only (Blender 4.3, FFmpeg, Python 3.11 with installed libraries, espeak-ng, sox). No network, no downloaded assets, no generative video or speech services. Do not read other tasks' answers; no credentials in deliverables. The wall-clock budget is set by the organisers (10800 s suggested); save a valid deliverable early, then keep improving.

Reviewers will inspect the decoded film and stems and the project file, and will run blind viewings. Film and audio terms carry their usual industry meaning.
