# WFA-3D-012 — Club Night / Flag Fall

## Brief
Make a 30-second, six-shot, 16:9 photoreal short film. Late at night in a chess club, only one game is still running. Under time pressure, White plays a knight move and presses the clock; at the wall, the arbiter sets the same move on the demonstration board; Black captures the knight with the rook, presses the clock and quietly speaks the first line; White's flag falls; the arbiter announces the result and White tips over his own king. The story must be told through on-screen action, the clock and sound, with no captions or explanatory title cards.

This is a photoreal 3D scene that you build yourself, not an assembly of stock clips. Scene identity, the position and the layout are given in input/scene.json and input/layout.svg (the SVG is a layout reference only). The two English lines are in input/transcript.en.txt. input/ contains only one raw noise texture; every other sound, and both spoken lines, are yours to make.

## Shots and edits
The film runs at 30 fps. Nominal shot starts are 0, 4, 9, 13, 19 and 24 s, and the film ends at 30 s.

| Shot | Content | Scale / angle | Movement / optics |
|---|---|---|---|
| S1 0–4 s | Dim hall; at the only lit table the two players face each other; the arbiter stands at the wall demo board | Extreme wide shot, high angle | Static |
| S2 4–9 s | White moves the knight, presses the clock, then looks up at the opponent | Over-the-shoulder medium close-up (over Black's shoulder) | Static, shallow depth of field |
| S3 9–13 s | Cross-cut: the arbiter sets the same move on the demo board | Medium shot | Slow lateral truck |
| S4 13–19 s | Reverse shot: Black captures the knight with the rook; the captured knight falls and rolls onto the table, coming to rest; Black presses the clock and begins the first line | Over-the-shoulder medium close-up (over White's shoulder) | Static, shallow depth of field |
| S5 19–24 s | Insert: close-up of the clock, White's flag falls; the clock's running is audible up close | Close-up | Static, shallow depth of field |
| S6 24–30 s | The arbiter has reached the table and speaks the second line; White tips over his own king | Two-shot in profile, medium | Slow dolly-in |

Five transitions:

- **T12 (4.0 s):** hard cut.
- **T23 (9.0 s):** cross-cut, hard cut to the arbiter.
- **T34 (13.0 s):** cross-cut, hard cut back to the table, forming a shot/reverse-shot pair with S2.
- **T45 (19.0 s):** hard cut to the insert; Black's line carries into S5 as an L-cut.
- **T56 (24.0 s):** hard cut; the arbiter's line enters 0.6 s early as a J-cut.

No other cuts, freeze frames, graphic overlays or inserted footage are allowed. Action timing between edit points is yours to plan, but every action must really happen in the rendered picture and sound and be recorded truthfully in events.csv.

## Production requirements
- Build and render offline in Blender 4.3. The picture must look photoreal, with believable materials, lighting and shadows. Flat shading, cartoon looks, cards or untextured clay geometry are not acceptable.
- All three characters must be rigged with individually animated fingers; whoever speaks on screen must have lip sync matching the speech.
- The game, the clock and the demo board must agree with scene.json and the story in every shot and follow the rules and conventions of over-the-board tournament play.
- The captured knight and the tipped king must be physically simulated, with the simulation cache delivered with the project.
- Both lines must be natural, clearly intelligible English speech produced offline. Online TTS, paid services and imitation of real people's voices are forbidden.
- The hall must feel quiet; piece, clock and footstep sounds must be in sync with the picture, and music must not be used to cover missing action sounds.

## Deliverables
1. **base/**: `output.mp4` (H.264, yuv420p, 1280×720, constant 30 fps, exactly 900 frames; AAC stereo 48 kHz; integrated loudness −23 ±2 LUFS, true peak ≤ −1 dBTP, no clipping), `timeline.json`, `events.csv`, and three stems `stems/{speech,table,room}.wav` (48 kHz PCM, 30 s each). The stems, summed with the master gains declared in timeline.json, must equal the mix.
2. **revision/**: the dependent revision, same contents as base (events.csv not required), 885 frames long.
3. **project/**: `scene.blend` (Blender 4.3), build scripts, and a `README.md` with the exact export commands; media packed into the project or referenced by project-relative paths. Object names in the project:
   - characters `PLAYER_W`, `PLAYER_B`, `ARBITER`, with armatures `PLAYER_W_RIG`, `PLAYER_B_RIG`, `ARBITER_RIG`;
   - table board `BOARD` (origin at the board centre, local +X toward the h-file, local +Y toward the 8th rank); pieces `W_KING`, `W_KNIGHT`, `W_PAWN`, `B_KING`, `B_ROOK`;
   - demo board `DEMO_BOARD` (same axis convention as `BOARD`), pieces `DEMO_W_KING`, `DEMO_W_KNIGHT`, `DEMO_W_PAWN`, `DEMO_B_KING`, `DEMO_B_ROOK`;
   - clock `CLOCK`, parts `CLOCK_BUTTON_W`, `CLOCK_BUTTON_B`, `CLOCK_HAND_W`, `CLOCK_HAND_B`, `FLAG_W`, `FLAG_B`;
   - cameras `CAM_S1` to `CAM_S6`.
   The revision must be produced from the same .blend through the scene custom property `revision_trim_frames` (0 for base, 15 for the revision).
4. **timeline.json** (both versions): shot frame ranges, transitions, audio in/out of each line and stem, and master gains.
5. **events.csv**: header `event_id,frame,description`, containing at least: `w_lift`, `w_place`, `w_press`, `w_glance`, `demo_move_start`, `demo_move_end`, `b_capture_contact`, `knight_rest`, `b_press`, `line_black_start`, `line_black_end`, `flag_fall`, `line_arbiter_start`, `line_arbiter_end`, `king_tip`.
6. **credits.md**: the source of every asset and tool, including how the spoken lines were produced. **qa.md**: problems you actually found and fixed, with before/after frame numbers or sample positions; if you found none, say so truthfully — do not invent any.

## Dependent revision
Ripple-delete 15 frames from the end of S3: S3 becomes 105 frames long, and all picture, action and sound from S4 onward move 15 frames earlier, with the transition types unchanged; everything before 12.5 s stays unchanged. The revision must still meet every content requirement above.

## Rules
Use only the local offline environment (Blender 4.3, FFmpeg, Python 3.11 with installed libraries, espeak-ng, sox). No network access, no downloaded assets, and no generative video or speech services. Do not read other tasks' answers, and include no credentials in your outputs. The experimenter will tell you the wall-clock budget; save a valid deliverable early, then keep improving it.

Reviewers will inspect the decoded film and stems and the project file, and will run blind viewings. Film, audio and chess terms carry their usual professional meaning.
