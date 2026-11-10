# WFA-3D-013 — Attic Storm

## Task
Make a 28-second, five-shot, 2.39:1 scope live-action-style short. On a stormy night MARA reads letters alone under the pendant lamp in an attic; the wind and rain build, she looks up and says one line. The window latch gives way, the casement blows open and the curtain billows into the room. After a lightning flash, a gust sets the pendant lamp swinging and its moving light and shadows sweep the attic. She gets up, goes to the window, gathers the curtain, pulls the window shut and latches it. The film ends in calm: the lamp gradually comes to rest while the rain continues. The story must be carried by on-screen action and sound only; no subtitles or title cards.

This is a photoreal 3D scene you build yourself, not a footage assembly. Scene identity and layout are in input/scene.json and input/layout.svg (the SVG is a layout reference only); the line is in input/transcript.en.txt. input/ contains only two raw noise files; every other sound, and the spoken line, must be made by you.

## Shots and edits
24 fps. The five shots nominally start at 0, 6, 11, 17 and 23 s; the film ends at 28 s.

| Shot | Content | Size / angle | Movement / optics |
|---|---|---|---|
| S1 0–6 s | MARA at the desk under the pendant lamp reading a letter; the casement rattles in the wind; she looks up at the window and says the line | Medium shot, eye level | Slow dolly-in, normal lens |
| S2 6–11 s | The latch gives way, the casement blows inward, the curtain balloons into the room, rain spatters the sill; lightning flares outside at the end of the shot | Close shot, facing the window | Handheld |
| S3 11–17 s | The attic in the afterglow of the flash: a gust sets the lamp swinging, light and shadow sweep the walls and rafters; MARA rises and heads for the window; thunder rolls | Wide shot, low angle | Locked-off, wide lens |
| S4 17–23 s | MARA's hands catch the flapping curtain, pull the casement back and fasten the latch | Close shot, over the shoulder | Locked-off, shallow depth of field |
| S5 23–28 s | The attic settling: the curtain hangs down, the lamp's swing dies away, MARA stands at the window, the rain softens, distant thunder | Extreme wide shot, high angle | Slow pull-back |

Four transitions:

- **T12 (6.0 s)**: straight cut with a dialogue L-cut: the S1 line carries across the cut and ends 0.5 s into S2.
- **T23 (11.0 s)**: hidden cut inside the overexposed white-out of a lightning flash; the same flash is continuous across the cut.
- **T34 (17.0 s)**: straight cut.
- **T45 (23.0 s)**: 1.0 s dissolve centred on 23.0 s.

Apart from these four there must be no other cuts, freeze frames, overlaid graphics or inserts. Action timing outside the edit points is yours to plan, but every action must really happen in the rendered picture and sound and be recorded truthfully in events.csv.

## Production requirements
- Build and render offline in Blender 4.3. The picture must look like photoreal cinema, with credible materials, lighting and shadows. Flat shading, cartoon, cards or untextured geometry do not qualify.
- Motivated lighting: the only interior source is the tungsten pendant lamp; outside the window there is only the night sky and the lightning. Light direction, colour temperature and contrast must be consistent across all five shots.
- MARA must be rigged with individually animated fingers and must have lip sync matching the spoken line.
- The curtain must be a cloth simulation, with its cache delivered with the project.
- The line must be natural, clearly intelligible English speech produced offline. No online TTS, paid services or imitation of real people's voices.
- Wind, rain, thunder, the casement, the latch and the lamp must all be heard and must match the picture; music may not be used to cover missing action sounds.

## Deliverables
1. **base/**: `output.mp4` (H.264, yuv420p, 1280×536, square pixels, constant 24 fps, exactly 672 frames; AAC stereo 48 kHz; integrated loudness −23 ±1 LUFS, true peak ≤ −1 dBTP, no clipping), `timeline.json`, `events.csv`, and three stems `stems/{dialogue,storm,foley}.wav` (48 kHz PCM, 28 s each). The stems, summed with the master gains declared in timeline.json, must equal the mix.
2. **revision/**: the dependent revision, with `output.mp4` and `timeline.json`, same format and frame count as the base.
3. **project/**: `scene.blend` (Blender 4.3), build scripts and a `README.md` with the exact export commands; media packed or referenced by project-relative paths. Object names: character `MARA`, armature `MARA_RIG`; props `PENDANT_LAMP`, `LAMP_CORD`, `CURTAIN`, `CURTAIN_ROD`, `WINDOW_SASH`, `WINDOW_LATCH`, `DESK`; lights `LAMP_LIGHT` (the bulb) and `LIGHTNING`; cameras `CAM_S1` to `CAM_S5`. Both versions must come from the same .blend via the scene custom property `dissolve_frames` (24 for base, 48 for revision).
4. **timeline.json** (both versions): shot frame ranges, transition types and frame ranges, dialogue in/out, master gain per stem.
5. **events.csv**: header `event_id,frame,description`, containing at least: `line_start`, `line_end`, `window_burst`, `flash_peak`, `thunder_1`, `lamp_swing_start`, `mara_rise`, `curtain_grab`, `window_shut`, `latch_click`, `thunder_far`.
6. **credits.md**: source of every asset and tool, including how the line was produced. **qa.md**: problems you actually found and fixed, with before/after frame numbers or sample positions; if you found none, say so truthfully. Do not invent.

## Dependent revision
Lengthen the T45 dissolve to 2.0 s, still centred on 23.0 s, total length unchanged. Picture outside the dissolve span and all audio stay unchanged.

## Rules
Local offline environment only (Blender 4.3, FFmpeg, Python 3.11 with installed libraries, espeak-ng, sox). No network, no downloaded assets, no generative video or speech services. Do not read other tasks' answers; no credentials in outputs. The wall-clock budget is set by the organisers (10800 s suggested); save a valid delivery early, then keep improving.

Review inspects the decoded film and stems and the project file, and includes blind viewing. Film and audio terms carry their usual industry meaning.
