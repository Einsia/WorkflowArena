# WFA-3D-011 — The First Bowl

## Task
Make a 30-second, five-shot, 16:9 photoreal slice-of-life short. A winter evening: grandmother Mei, at the kitchen stove, lifts the lid off a soup pot, steam pours out and she ladles a bowl of soup; her grandson Lin comes in from the cold entrance hall and is heard before he is seen; Mei turns and hands the hot bowl to Lin, who takes it in both hands. The story is carried by on-screen action and sound; no subtitles, explanatory cards or music.

This is a photoreal 3D scene that you build yourself, not a stock-footage assembly. Scene identity and layout are in input/scene.json and input/layout.svg (the SVG is a layout reference only); the three English lines are in input/transcript.en.txt. input/ contains only two raw noise textures; every other sound and all three lines must be produced by you.

## Shots and editing
30 fps. The five shots nominally start at 0, 6, 13, 18 and 24 s; the film ends at 30 s.

| Shot | Content | Size / angle | Movement / optics |
|---|---|---|---|
| S1 0–6 s | Kitchen: Mei at the stove grips the lid handle and lifts the lid | Wide shot, eye level | Locked-off, deep focus |
| S2 6–13 s | Pot mouth: the lid leaves frame, steam rises; Mei ladles soup from the pot into the bowl in her hand; at the end, the door, wind and Lin's first line are heard off-screen | Close-up, high angle | Locked-off, shallow depth of field |
| S3 13–18 s | Doorway: Lin shuts the door behind him, finishes his first line and walks toward the kitchen | Medium shot, eye level | Handheld |
| S4 18–24 s | Over Lin's shoulder onto Mei: she turns, holds the bowl out in both hands and says the second line | Over-the-shoulder medium shot | Slow dolly-in, shallow depth of field |
| S5 24–30 s | The bowl and both characters' hands: Lin takes the bowl in both hands, Mei lets go, steam rises from the bowl; Lin says the third line off-screen | Close-up, side angle | Slow tilt up, shallow depth of field |

Four transitions:

- **T12 (6.0 s)**: match cut on action, cut during the lid lift; the lid's motion is continuous across the cut.
- **T23 (13.0 s)**: hard cut, J-cut; the entrance-hall sound (wind, door and Lin's first line) leads the picture by 1.0 s.
- **T34 (18.0 s)**: hard cut.
- **T45 (24.0 s)**: match cut on action, cut during the handover; bowl and hand motion are continuous across the cut.

No other cuts, freezes, dissolves, graphic overlays or inserts. Action timing away from the edit points is yours to plan, but every action must really happen in the rendered picture and sound and be truthfully recorded in events.csv.

## Production requirements
- Build and render offline in Blender 4.3. The picture must read as photoreal, with believable materials, lighting and shadows. Flat shading, cartoon look, cards or untextured clay geometry do not qualify.
- Both characters are rigged with individually animated fingers; contact between hands and the lid, ladle and bowl must be physically believable. Whoever speaks on screen has lip-sync matching the speech.
- The soup (scooping and pouring) and the steam are physics simulations; ship the simulation caches with the project.
- The three lines are natural, clearly intelligible English speech made offline, 2.0–4.5 words per second per line, with the two characters' voices distinguishable. No online TTS, paid services or imitation of real people's voices.
- The kitchen and the entrance hall each have a believable acoustic environment; on-screen actions have corresponding action sounds.

## Deliverables
1. **base/**: `output.mp4` (H.264, yuv420p, 1280×720, constant 30 fps, exactly 900 frames; AAC stereo 48 kHz; integrated loudness −18 ±2 LUFS, sample peak ≤ −1 dBFS, no clipping), `timeline.json`, `events.csv`, and three stems `stems/{speech,kitchen,hall}.wav` (48 kHz PCM, 30 s each). The stems summed with the master gains declared in timeline.json must equal the mix.
2. **revision/**: the dependent revision, same contents as base (no events.csv), 891 frames long.
3. **project/**: `scene.blend` (Blender 4.3), build scripts and a `README.md` with exact export commands; media packed or referenced by project-relative paths. Object names: characters `MEI`, `LIN` with armatures `MEI_RIG`, `LIN_RIG`; props `POT`, `POT_LID`, `LADLE`, `BOWL`, `DOOR`, `STOVE`; simulation domains `SOUP_DOMAIN`, `STEAM_DOMAIN` (several allowed, use these as name prefixes); cameras `CAM_S1` to `CAM_S5`. The revision must be produced from the same .blend via the scene custom property `revision_trim_frames` (0 for base, 9 for the revision).
4. **timeline.json** (both versions): shot frame ranges, transitions, per-stem audio region in/out points and master gains.
5. **events.csv**: header `event_id,frame,description`, containing at least: `lid_grip`, `lid_lift`, `ladle_in`, `pour_start`, `pour_end`, `line_door_start`, `line_door_end`, `door_close`, `line_warn_start`, `line_warn_end`, `lin_touch`, `mei_release`, `line_thanks_start`, `line_thanks_end`.
6. **credits.md**: the source of every asset and tool, including how the lines were produced. **qa.md**: problems you actually found and fixed, with frame numbers or sample positions before and after; if you found none, say so truthfully. Do not invent.

## Dependent revision
Move T23 9 frames earlier by trimming the last 9 frames of S2. All picture, action and sound from T23 onward shift 9 frames earlier as a block; transition types and the J-cut lead stay unchanged. Picture before T23 stays unchanged.

## Rules
Local offline environment only (Blender 4.3, FFmpeg, Python 3.11 and installed libraries, espeak-ng, sox). No network, no downloaded assets, no generative video or speech services. Do not read other tasks' answers; no credentials in outputs. The wall-clock budget is set by the experimenter (10800 s recommended); save a valid delivery early, then keep improving.

Review inspects the decoded film and stems and the project file, and includes blinded viewing. Film and audio terms carry their usual industry meaning.
