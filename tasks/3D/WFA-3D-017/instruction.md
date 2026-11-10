# WFA-3D-017 — Rainy Corner / Last Bus

## Task
Make a 30-second, five-shot, 16:9 photoreal short. On a rainy night at a street corner, a woman holding a closed umbrella waits at the bus stop for the last bus. The lamp flickers a few times and goes out, leaving the corner lit only by the cyan neon sign. She opens her umbrella and, stepping off the kerb, puts one foot into the puddle. The bus pulls in, its headlights light her up, and she speaks the film's single line into her phone. Finally we return to the opening set-up: nobody is at the stop, the rain has eased, and the streetlamp comes back on. The story is told through picture and sound only — no subtitles or title cards.

This is a 3D scene you build yourself, not a stock-footage assembly. Scene identity and layout are in input/scene.json and input/layout.svg (the SVG is a layout reference only); the line is in input/transcript.en.txt. input/ contains only two raw noise files; every other sound, and the line itself, must be made by you.

## Shots and editing
24 fps, 30 seconds, 720 frames.

| Shot | Content | Size / angle | Movement / optics |
|---|---|---|---|
| S1 0–6 s | The whole corner: streetlamp, wet road, the puddle by the kerb, the bus stop; the woman waits by the stop holding a closed umbrella; the lamp starts to flicker | Extreme wide shot, high angle | Locked-off, deep focus |
| S2 6–12 s | The puddle surface: raindrops keep falling in; the water reflects the lit streetlamp; the lamp goes out, the lamp in the reflection goes out with it, and only the cyan glow of the neon remains on the water | Close-up, very low angle just above the water | Locked-off, shallow depth of field |
| S3 12–19 s | She opens the umbrella, steps off the kerb and puts a foot into the same puddle; water splashes and the reflection breaks up; by now the corner is lit only by the neon | Medium shot, eye level | Lateral tracking shot |
| S4 19–25 s | Under the umbrella she takes out her phone and speaks the line; the bus headlights sweep from frame left onto her face and the wet umbrella | Medium close-up, slight low angle | Slow dolly-in, shallow depth of field |
| S5 25–30 s | The same corner, nobody at the stop, lighter rain; the streetlamp comes back on and the road and puddle reflect it again | Same set-up and shot size as S1 | Locked-off, deep focus |

Four transitions:

- **T12 (6.0 s)**: hard cut.
- **T23 (12.0 s)**: 1.0-second dissolve centred on 12.0 s.
- **T34 (19.0 s)**: hard cut with a sound bridge: the bus pulling in enters as off-screen sound 1.0 s before the cut.
- **T45 (25.0 s)**: hard cut, L-cut: the bus sound carries over the first 1.5 s of S5 and then ends.

No other cuts, freeze frames, graphic overlays or inserts. Action timing other than the edit points is up to you, but every action must really happen in the rendered picture and sound and be recorded truthfully in events.csv.

## Production requirements
- Build and render offline in Blender 4.3. The picture must read as a photoreal night exterior: the wet road, the puddle reflections, the lighting and the shadows must all be believable. Flat shading, toon looks, cards or untextured geometry fail.
- The rain must be simulated as 3D raindrops in the scene, not a 2D overlay or a rain texture; the puddle surface must show ripples raised by the drops; the splash and ripples from the footstep must really happen in the picture. Ship simulation caches with the project.
- The streetlamp, the neon sign and the bus headlights are real light sources in the scene; lighting and reflections in the picture must follow their state.
- The character must be rigged with individually animated fingers, and her mouth must be lip-synced to the line.
- The line must be natural, clearly intelligible English speech produced offline. No online TTS, paid services or imitation of real people's voices.
- Rain is heard throughout; once the umbrella is open, rain on the canopy must be audible; the streetlamp's electrical sound follows the lamp going off and on; footsteps, the puddle step and the bus all need matching sound. Do not use music to cover missing action sound.

## Deliverables
1. **base/**: `output.mp4` (H.264, yuv420p, 1280×720, constant 24 fps, exactly 720 frames; AAC stereo 48 kHz; integrated loudness −20 ±2 LUFS, sample peak ≤ −1 dBFS, no clipping), `timeline.json`, `events.csv`, and three stems `stems/{speech,rain,fx}.wav` (48 kHz PCM, same length as the film). The stems summed with the master gains declared in timeline.json must equal the mix.
2. **revision1/** and **revision2/**: two dependent revisions (below); each contains the same set of files as base (film, timeline.json, events.csv, three stems).
3. **project/**: `scene.blend` (Blender 4.3), build scripts, and a `README.md` with the exact export commands; media packed or referenced by project-relative paths. Object names: character `COMMUTER`, armature `COMMUTER_RIG`; props and set `UMBRELLA`, `PHONE`, `STREETLAMP`, `LAMP_HEAD`, `PUDDLE`, `ROAD`, `KERB`, `BUS_STOP`, `NEON_SIGN`, `RAIN`, `BUS_LIGHTS`; cameras `CAM_S1` to `CAM_S5`. All three films must be generated from the same .blend via the scene custom properties `rev_s2_hold_frames` and `rev_s4_trim_frames` (base 0/0, revision1 12/0, revision2 12/6).
4. **timeline.json** (every version): shot frame ranges, transitions and audio in/out points (including the sound bridge and the L-cut), master gains.
5. **events.csv** (every version): header `event_id,frame,description`, with at least these events: `lamp_flicker_start`, `lamp_off`, `umbrella_open`, `foot_contact`, `headlights_on_face`, `line_start`, `line_end`, `lamp_on`.
6. **credits.md**: the source of every asset and tool, including how the line was produced. **qa.md**: issues you actually found and fixed, with before/after frame numbers or sample positions; if you found none, say so honestly — do not invent any.

## Dependent revisions
- **Revision 1 (revision1/)**: extend the end of S2 by 12 frames; the extension is continuing action, not a freeze. The T23 dissolve keeps its duration and moves with the new boundary; S3 and everything after it — picture, action and sound — shift 12 frames later, for a total of 732 frames. Everything before the S2 extension stays unchanged.
- **Revision 2 (revision2/)**: starting from Revision 1, trim the first 6 frames of S4 while keeping the T34 cut point where it is; the rest of S4 and S5 move earlier accordingly, the sound-bridge lead and the L-cut tail length stay the same, for a total of 726 frames. Everything before T34 is identical to Revision 1.

## Rules
Use only the local offline environment (Blender 4.3, FFmpeg, Python 3.11 with installed libraries, espeak-ng, sox). No network access, no downloaded assets, no generative video or speech services. Do not read other tasks' answers; artefacts must not contain credentials. Suggested wall-clock budget 10800 s (the operator sets the actual budget); save a valid delivery early, then keep improving.

Reviewers inspect the decoded films and stems and the project files, and run blind viewings. Film and audio terms carry their usual industry meaning.
