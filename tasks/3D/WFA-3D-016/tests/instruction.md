# WFA-3D-016 — Chain Swap / Test Ride

## Task
Make a 30-second, six-shot, 16:9 photoreal short with no dialogue. A courier's bike has snapped its chain and is in a corner bike shop. The mechanic takes off the old chain, threads a new chain over the cog and chainring, closes it with a quick link, then turns the crank by hand so the chain drives the rear wheel. Outside on the pavement the courier waits holding a helmet, checks the watch, then looks back towards the shop. The two lines are cross-cut, and the last shot follows the courier riding away. The story must be carried by on-screen action and sound only: no subtitles, title cards or narration.

You build the scene yourself; this is not footage assembly. The shop and the street outside are one continuous space, and the waiting courier can be seen through the shop window from inside. Scene identity and layout are in input/scene.json and input/layout.svg (the SVG is a layout reference only). input/ contains only three raw noise files; every sound must be made by you.

## Shots and edits
30 fps. Nominal shot starts are 0, 5, 9, 15, 18 and 22 s; the film ends at 30 s.

| Shot | Content | Size / angle | Movement / optics |
|---|---|---|---|
| S1 0–5 s | Inside the shop, bike clamped in the repair stand; the mechanic removes the broken old chain and drops it into the parts tray; the courier is visible through the window behind | Wide, eye level | Locked-off, deep focus |
| S2 5–9 s | On the pavement the courier, helmet in hand, raises the left wrist to check the watch | Medium, slight low angle | Handheld |
| S3 9–15 s | The mechanic's hands hang the new chain on the rear cog, wrap it onto the chainring, bring the two ends together and close the quick link | Extreme close-up, macro | Locked-off, shallow depth of field |
| S4 15–18 s | The courier turns to look at the shop door | Medium close-up | Slow dolly-in, shallow depth of field |
| S5 18–22 s | The mechanic grips and turns the crank; the chain drives the rear cog and wheel; then he lets go | Close-up, chainring mid-frame | Locked-off |
| S6 22–30 s | In the street the courier rides the same bike away and exits frame right | Opens on a close-up of the moving chainring, then widens to a wide shot | Tracking, pulling back |

Five edits:

- **T12 (5.0 s), T23 (9.0 s), T34 (15.0 s), T45 (18.0 s)**: hard cuts of the cross-cut. Picture and both location ambiences switch on the edit point together.
- **T56 (22.0 s)**: graphic-and-motion match cut from the S5 chainring to the moving chainring in S6, a hard cut that also performs the time ellipsis.

No other cuts, freezes, dissolves, overlay graphics or inserts. Action timing between edit points is yours to plan, but it must really happen in the rendered picture and sound and be declared truthfully in events.csv.

## Production requirements
- Build and render offline in Blender 4.3 with a photoreal look: credible materials, lighting and shadows. Flat shading, cartoon, cards or grey-box geometry fail.
- Both characters are skeleton-rigged with individually animated fingers. The mechanic's hand contact with the chain, quick link and crank must be believable.
- The chain is built from individual links, really meshes with and drives the chainring and cog; the bike's rotating parts must behave according to this bike's mechanics.
- Every visible contact and mechanical action has synchronised Foley. The two ambiences must be clearly distinct; music must not cover missing action sound.

## Deliverables
1. **base/**:
   - `output.mp4`: H.264, yuv420p, 1280×720, constant 30 fps, exactly 900 frames; AAC stereo 48 kHz; integrated loudness −18 ±2 LUFS, sample peak ≤ −1 dBFS, no clipping.
   - `timeline.json`, `events.csv`.
   - three stems `stems/{foley,shop,street}.wav`: 48 kHz PCM, 30 s each. Summed with the master gains declared in timeline.json they must equal the mix.
2. **revision/**: roll-edit revision with the same contents as base (no events.csv), still 900 frames.
3. **project/**: `scene.blend` (Blender 4.3), build scripts and a `README.md` with exact export commands. Media packed or referenced by project-relative paths.
   - Characters `MECHANIC`, `COURIER`; armatures `MECHANIC_RIG`, `COURIER_RIG`.
   - Props `BIKE`, `CHAIN`, `QUICK_LINK`, `OLD_CHAIN`, `CHAINRING`, `CRANK`, `REAR_COG`, `REAR_WHEEL`, `FRONT_WHEEL`, `REPAIR_STAND`, `PARTS_TRAY`, `WINDOW`, `WATCH`, `HELMET`.
   - Cameras `CAM_S1` to `CAM_S6`.
   - The revision must be produced from the same .blend via the scene custom property `roll_T34_frames` (0 for base, 9 for revision).
4. **timeline.json** (both versions): shot frame ranges, edit points, stem in/out points, master gains.
5. **events.csv**: header `event_id,frame,description`, containing at least `old_chain_off`, `watch_check`, `chain_hand_contact`, `link_join_start`, `link_click`, `courier_turn`, `crank_grab`, `crank_turn_start`, `chain_engage`, `crank_release`, `pedal_start`.
6. **credits.md**: source of every asset and tool. **qa.md**: problems you actually found and fixed, with before/after frame numbers or sample positions; if none, say so truthfully. Do not invent.

## Revision
Roll T34 by 9 frames: S3 runs 9 frames longer at its tail and S4 loses 9 frames at its head; total length unchanged. In the revision both the picture and the sound switch at the new T34; all other edit points and content stay as they were.

## Rules
Local offline environment only: Blender 4.3, FFmpeg, Python 3.11 with installed libraries, espeak-ng, sox. No network or downloads, no generative video/audio services, no reading other tasks' solutions, no credentials in outputs. The wall-clock budget is set by the operator (10800 s suggested for this task); save a valid deliverable early, then refine.

Review inspects the decoded film and stems, the project file, and includes blinded viewing. Film and audio terms carry their usual industry meaning.
