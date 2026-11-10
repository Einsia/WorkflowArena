# WFA-3D-018 — Lane Two

## Task
Make a 30-second, six-shot, 16:9 short in an observational documentary style. An airport security checkpoint at night; two spaces on either side of a partition wall have things happening at the same time. In the screening lane a red duffel bag passes through the X-ray machine; the screener sees the monitor, stops the belt and calls on her radio. At the gates, a passenger who has just scanned through is stopped by an officer. The film cross-cuts between the two places, and the two lines converge at the search table at the end. The story must be carried by on-screen action and sound alone; no subtitles or explanatory title cards.

This is a photoreal 3D scene you build yourself, not a footage assembly. The plan layout of both spaces and the identity of characters and props are in input/scene.json and input/layout.svg (the SVG is a layout reference only); the two English lines are in input/transcript.en.txt. input/ contains only two raw noise files; every other sound and both spoken lines must be made by you.

## Shots and editing
30 fps; the six shots start nominally at 0, 5, 10, 15, 20 and 24 s, ending at 30 s.

| Shot | Place | Content | Size / angle | Movement / optics |
|---|---|---|---|---|
| S1 0–5 s | Screening lane | The passenger puts the red bag into a grey tray and pushes it onto the belt; the tray rides into the X-ray tunnel; the screener is at the operator station in the background; the passenger exits frame left | Wide, high angle | Locked-off, deep focus |
| S2 5–10 s | Gate hall | The passenger scans her boarding pass at gate 2, the glass flaps open and she walks through; the officer stands post beyond the gates | Medium wide, eye level | Follow pan, normal lens |
| S3 10–15 s | Screening lane | The monitor shows an X-ray image of this bag; the screener presses the belt-stop button, the belt stops with the red bag and its tray at the tunnel exit, and the tray behind bumps into it; she picks up the radio and says the first line | Over-the-shoulder close shot (behind the screener) | Locked-off, shallow depth of field, rack focus from the monitor to the stop button |
| S4 15–20 s | Gate hall | The officer hears the call, raises a hand and steps into the passenger's path, saying the second line; the passenger stops and turns her head to him | Medium, eye level | Handheld |
| S5 20–24 s | Screening lane | At the exit the screener lifts the red bag with both hands and puts it on the search table | Close shot, low angle | Slow dolly-in |
| S6 24–30 s | Gate hall → screening lane | The officer leads the passenger toward the north door in the partition; the camera follows, then whips toward the screening-lane side; as the frame settles the two enter the lane through the north door and reach the search table, where the screener stands with the bag on the table | Medium tracking → whip pan → medium wide | Plays as a single take |

Transitions:

- **T12 (5.0 s)**: cross-cut hard cut, J-cut, gate-hall sound leads by 0.6 s.
- **T23 (10.0 s), T34 (15.0 s), T45 (20.0 s)**: cross-cut hard cuts, sound cuts with picture.
- **T56 (24.0 s)**: cross-cut hard cut, J-cut, gate-hall sound leads by 0.5 s.
- **Hidden cut (27.0 s, frame 810)**: concealed in the S6 whip pan, joining a gate-hall camera to a screening-lane camera; the sound travels with the whip from the gate hall into the lane with no seam.

The cross-cutting depicts simultaneous parallel action: both places share one continuous timeline, and while the film is away from one place its people, belt and bags keep going, so the state on returning matches the time that has passed. No cuts other than those above, no freeze frames, overlay graphics or inserts. Action timing outside the edit points is yours to plan, but every action must really occur in the rendered picture and sound and be truthfully recorded in events.csv.

## Production requirements
- Build and render offline in Blender 4.3. The picture must read as photoreal documentary footage, with believable materials, lighting and shadows. Flat shading, toon looks, cards or untextured geometry do not qualify.
- All three characters are rigged with individually articulated fingers; any character speaking on screen has lip sync matching the voice.
- The motion of trays and bags on the belt while running, stopping and colliding must be a rigid-body simulation; ship the simulation cache with the project.
- Both lines must be natural, clearly intelligible English speech produced offline. No online TTS, paid services or imitation of real people's voices.
- The screening lane and the gate hall must sound like two different acoustic spaces; actions of machines and people on screen need corresponding sound. Music may not be used to mask missing action sounds.

## Deliverables
1. **base/**: `output.mp4` (H.264, yuv420p, 1280×720, constant 30 fps, exactly 900 frames; AAC stereo 48 kHz; integrated loudness −20 ±2 LUFS, sample peak ≤ −1 dBFS, no clipping), `timeline.json`, `events.csv`, and three stems `stems/{speech,lane,gate}.wav` (48 kHz PCM, 30 s each; lane = all non-dialogue sound of the screening lane, gate = all non-dialogue sound of the gate hall). The stems summed with the master gains declared in timeline.json must equal the mix.
2. **revision/**: the dependent revision, same contents as base (events.csv not required), 930 frames, stems 31 s each.
3. **project/**: `scene.blend` (Blender 4.3), build scripts and a `README.md` with exact export commands; media packed or project-relative. Scene frame numbers equal output frame numbers (base 0–899). Object names: characters `PASSENGER`, `SCREENER`, `OFFICER` with armatures `PASSENGER_RIG`, `SCREENER_RIG`, `OFFICER_RIG`; props `BAG`, `TRAY_A` (holds the red bag), `TRAY_B` (the tray behind), `CONVEYOR`, `XRAY_TUNNEL`, `MONITOR`, `BELT_STOP_BUTTON`, `RADIO_HANDSET`, `SEARCH_TABLE`, `TURNSTILE_GATE2`, `BOARDING_PASS`, `PARTITION`; cameras `CAM_S1` to `CAM_S5`, plus `CAM_S6A` and `CAM_S6B` on either side of the S6 hidden cut. The revision must be produced from the same .blend via the scene custom property `revision_insert_frames` (0 for base, 30 for the revision).
4. **timeline.json** (both versions): shot frame ranges and cameras, type and frame of every transition (including the hidden cut), in/out of each stem and J-cut leads, master gains.
5. **events.csv**: header `event_id,frame,description`, containing at least: `tray_push`, `bag_enter_tunnel`, `pass_scan`, `flaps_open`, `passenger_through`, `stop_press`, `belt_stop`, `tray_bump`, `line_screener_start`, `line_screener_end`, `officer_halt`, `line_officer_start`, `line_officer_end`, `passenger_stop`, `bag_grip`, `bag_place`, `passenger_arrive`.
6. **credits.md**: source of every asset and tool, including how the lines were made. **qa.md**: problems you actually found and fixed, with before/after frame numbers or sample positions; if you found none, say so truthfully; do not invent.

## Dependent revision
Insert a new 1-second (30-frame) beat of performance at the head of S5: having reached the exit, the screener first bends to glance at the luggage tag on the bag, then lifts it exactly as before. Everything before 20 s stays unchanged; all picture, action and sound from the original S5 onward shifts 30 frames later, transition types and sound leads stay the same, and both places remain on one continuous timeline.

## Rules
Local offline environment only (Blender 4.3, FFmpeg, Python 3.11 with installed libraries, espeak-ng, sox). No network, no downloaded assets, no generative video or voice services. Do not read other tasks' answers; no credentials in outputs. Suggested wall-clock budget 10800 s, subject to the experimenter; save a valid deliverable early, then keep improving.

Review examines the decoded film and stems and the project file, and includes blind viewing. Film and audio terms carry their usual industry meaning.
