# WFA-3D-015 — The 2 a.m. Caller

## Task
Make a 30-second, five-shot, 16:9 photoreal short film. Two hosts are on air in a late-night radio studio. A taxi driver stopped at a red light is listening to the show on the car radio, then phones in and speaks on air. The film cuts back and forth between the studio and the taxi. The link between the two spaces is built entirely through sound: the same words must sound different in the studio, from the car radio and over the phone line. No subtitles, title cards or voice-over narration.

You build the scene yourself in 3D; this is not footage assembly. Scene identities and layout are in input/scene.json and input/layout.svg (the SVG is a layout reference only). The four English lines are in input/transcript.en.txt. input/ also holds two raw noise files. You make every other sound and all of the speech yourself.

## Shots and edit
30 fps. The five shots start nominally at 0, 6, 12, 18 and 24 s, and the film ends at 30 s.

| Shot | Content | Size / angle | Movement / optics |
|---|---|---|---|
| S1 0–6 s | Studio, ON AIR lamp lit. HOST_A speaks L1 into the mic; HOST_B then starts L2 | Medium-wide two-shot, eye level | Locked-off, normal lens |
| S2 6–12 s | Inside the taxi, radio in frame. L2 comes out of the radio; the driver turns the radio down, then raises the phone to his ear | Over-the-shoulder medium from the back seat | Handheld, normal lens |
| S3 12–18 s | The driver speaks L3 into the phone | Profile close-up | Locked-off, shallow depth of field |
| S4 18–24 s | Studio. HOST_B, on headphones, listens to the caller. When the driver has finished, HOST_B pulls down the CALLER fader to drop the call; then HOST_A, off screen, starts L4 | Medium close single | Slow dolly-in, shallow depth of field |
| S5 24–30 s | Inside the taxi; L4 comes out of the radio. The driver hangs up and turns the radio back up; the light turns green and the taxi pulls away | Medium from the back seat | Handheld, normal lens |

Four transitions:

- **T12 (6.0 s)**: sound match cut. L2 runs continuously across the cut, with no dropped or repeated words. Before the cut it is the live studio sound; after the cut it is the same line played by the car radio.
- **T23 (12.0 s)**: hard cut with a J-cut. L3 enters 0.6 s early.
- **T34 (18.0 s)**: hard cut with an L-cut. L3 carries on across the cut; once we are in the studio, the caller is heard only through the phone line.
- **T45 (24.0 s)**: sound match cut. L4 runs continuously across the cut. Before the cut it is the live studio sound; after the cut it is the same line played by the car radio.

There must be no other cuts, freezes, overlaid graphics or inserted footage. The ON AIR lamp, the fader and the radio display are in-scene props. Apart from the edit points, you choose when each action and line happens. Every one must really occur in the rendered picture and sound, and must be recorded truthfully in events.csv.

## Production
- Build the film in Blender 4.3 and render it offline. The look must be photoreal, with believable materials, night lighting and shadows. Flat-shaded, toon, sprite or primitive-blockout renders do not qualify.
- All three people must be rigged characters whose fingers can move individually. Any on-screen speaker needs lip movement synchronised with the speech.
- The four lines use three distinguishable voices. They must be natural, clearly intelligible English speech, made offline. Network TTS, paid services and imitation of a real person's voice are not allowed.
- Every sound must match its listening point in the story: live in the studio, live in the taxi cabin, from the car radio, and over the phone line must be distinguishable from one another. On-screen and off-screen sources must sit in the stereo image consistently with where they are in the scene.
- No music.

## Deliverables
1. **base/**:
   - `output.mp4`: H.264, yuv420p, 1280×720, constant 30 fps, exactly 900 frames; AAC stereo at 48 kHz; integrated loudness −20 ±2 LUFS, true peak ≤ −1 dBTP, no clipping.
   - `timeline.json` and `events.csv`.
   - Four stereo stems, `stems/{studio,taxi,radio,phone}.wav`: 48 kHz PCM, the same length as the film. They are the four listening points: live studio sound, live taxi-cabin sound, sound played by the car radio, and sound carried by the phone line. With the master gain declared in timeline.json applied, the four stems must sum to the mix.
2. **rev1/** and **rev2/**: the two revisions described below. Each contains the same files as base/ except events.csv, which is not required.
3. **project/**: `scene.blend` (Blender 4.3), the build scripts, and a `README.md` giving the exact export commands. Pack media into the project or reference it by project-relative paths.
   - Characters `HOST_A`, `HOST_B` and `DRIVER`, with armatures `HOST_A_RIG`, `HOST_B_RIG` and `DRIVER_RIG`.
   - Props `MIC_A`, `MIC_B`, `CONSOLE`, `CALLER_FADER`, `ON_AIR_LAMP`, `TAXI`, `RADIO`, `RADIO_KNOB`, `PHONE` and `TRAFFIC_LIGHT`.
   - Cameras `CAM_S1` to `CAM_S5`.
   - Generate all three versions from the same .blend using the scene custom properties `rev1_hold_frames` and `rev2_trim_frames`: 0/0 for base, 12/0 for rev1 and 12/9 for rev2.
4. **timeline.json** (in every version): shot frame ranges, the four transitions, the in/out points of each line and of the main sounds on each stem, and the master gain.
5. **events.csv**: header `event_id,frame,description`. Include at least these events:
   - `line1_start`, `line1_end`, `line2_start`, `line2_end`, `line3_start`, `line3_end`, `line4_start`, `line4_end`
   - `knob_down_start`, `knob_down_end`, `phone_at_ear`, `caller_fader_down`, `phone_hang_up`, `knob_up_start`, `knob_up_end`, `light_green`
6. **credits.md**: the source of every asset and tool, including how the speech was made.
7. **qa.md**: the problems you actually found and fixed, with the frame numbers or sample positions before and after each fix. If you found none, say so. Do not invent problems.

## Two revisions
- **rev1** (from base): hold the end of S2 for 12 more frames, so T23 moves 12 frames later. Everything from T23 on (picture, action and sound, including the start of the L3 J-cut) moves 12 frames later, and the transitions keep their form. Total length 912 frames. Everything before the start of the T23 J-cut stays unchanged.
- **rev2** (from rev1): trim 9 frames from the end of S4, so T45 moves 9 frames earlier. L4 and all sound after it, and all of S5's picture and action, move 9 frames earlier than in rev1; the transitions keep their form. Total length 903 frames. The picture before T45 and the sound before L4 are the same as in rev1.

## Rules
Use only the local offline environment: Blender 4.3, FFmpeg, Python 3.11 with its installed libraries, espeak-ng and sox. No network access, no downloaded assets, and no generative video or speech services. Do not read other tasks' answers, and do not include credentials in the product. Suggested wall-clock budget is 10800 s; the experimenter's figure applies. Save a valid set of deliverables early, then keep improving it.

Reviewers will examine the decoded film and stems and the project file, and the film will also be watched and listened to in a blinded review. Film and audio terms carry their usual industry meaning.
