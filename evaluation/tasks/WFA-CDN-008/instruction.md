# WFA-CDN-008 — Two intercut threads, seven beats, from 46 anonymous candidates

## Situation and inputs
You receive 46 anonymous, silent candidate clips `input/01.mp4` … `input/46.mp4` (H.264, 1280×720, square pixels, 30 fps, 6.0–12.0 s each). They are licensed underwater documentary footage; source attribution is provided in `CREDITS.md`. Clip numbers are random. Everything needed is in the task directory; no network access is available or needed. Use `work/` for scratch and `output/` for deliverables. Assume 4–8 CPU cores, Python 3.11, FFmpeg/ffprobe and OpenCV; no GPU and no video generation.

The piece is a short "reef exploration": thread A is the camera travelling through reef terrain; thread B is encounters with reef animals. Each beat is defined by the content and the camera movement over the whole clip.

## Assembly contract
- Choose exactly seven DIFFERENT candidates, one per beat below, each matching all five fields of its beat.
- Intercutting: the two threads strictly alternate, opening and closing on thread A; within each thread keep the order given below.
- Use each chosen clip once, complete, at 1× speed, in original direction, with no crop, mirror, filter, text, added or dropped frames, transitions or generated content. Join by hard cuts.
- Output 1280×720, constant 30 fps, no audio.

## Thread A: reef terrain (in order A1–A4)

### A1
- description: A shallow reef mound with the moving, glinting water surface visible at the top of frame; a mound of yellow-brown plate coral fills most of the right side, distant sand and scattered rocks on the left.
- shot_size: Wide, tightening to medium-wide.
- camera_angle: Level from just below the mound top, tilted slightly up toward the surface.
- lens_size: Wide, strong near/far size difference.
- camera_movement: Continuous forward swim toward the mound throughout; the mound grows steadily and stays in frame.

### A2
- description: Opens close along the rim of a large pinkish-brown table coral whose fine branches fill the lower frame; the camera then clears the table top, revealing pale sand ahead and another table coral in the distance.
- shot_size: Close, widening to wide.
- camera_angle: From roughly table-top height rising to a slightly high angle above the table.
- lens_size: Wide.
- camera_movement: Continuous forward travel with a rise, passing over the coral top and continuing on.

### A3
- description: Open, pale, cracked limestone seabed; a dark hollow and reef lip on the left of frame; a black long-spined sea urchin mid-frame that keeps growing larger during the clip.
- shot_size: Wide, tightening to a close shot of the urchin.
- camera_angle: Oblique high angle just above the seabed.
- lens_size: Wide.
- camera_movement: Dolly-in toward the urchin, with clear parallax between the near seabed and the distant reef lip.

### A4
- description: A layered table-coral reef under deep blue water with many small fish above it; near the end several white, orange-banded butterflyfish swim into the foreground.
- shot_size: Wide.
- camera_angle: Level, slightly downward.
- lens_size: Wide.
- camera_movement: Hovering locked-off frame; the framing stays essentially still, with no push, pull, pan or drift.

## Thread B: reef animals (in order B1–B3)

### B1
- description: A large school of yellow-green surgeonfish with black vertical bars feeds over the reef; several fish pass extremely close to the lens as large defocused foreground masses; midway a large dark fish moves through the school.
- shot_size: Medium to close on fish bodies, reef as background.
- camera_angle: Level, close to the reef surface.
- lens_size: Wide; near fish heavily out of focus.
- camera_movement: Handheld hover inside the school with only small shake.

### B2
- description: Low over a flat coral platform with a low reef overhang ahead; the shadow beneath it is at first almost unreadable, and as the camera nears, schools of small yellow fish and red fish shapes appear.
- shot_size: Wide, tightening to medium.
- camera_angle: Low, level, close to the bottom.
- lens_size: Medium-wide; near platform texture sharp.
- camera_movement: Slow low push toward the overhang, settling to a stop at the end.

### B3
- description: Several whitetip reef sharks cruise low over sand and coral rubble; first distant and small, they come closer and fill a large part of the frame, ending over a patch of white coral rubble and table corals.
- shot_size: Wide, tightening to medium.
- camera_angle: Oblique high angle slightly above the sharks.
- lens_size: Wide.
- camera_movement: Lateral tracking: the camera moves toward frame-left with the sharks, so sand and reef stream continuously from the left side of frame to the right.

## Deliverables (public format specification)
1. `output/solution.mp4` — the seven complete clips in intercut order. H.264/yuv420p, 1280×720, SAR 1:1, 30/1 fps, no audio. Lossless concatenation or CRF≤18 re-encode.
2. `output/solution.json` — `{"segments":[...]}` with exactly seven objects in output order: `thread:"A"|"B"`, `beat:"A1".."B3"`, `source:"NN"`, `output:[start,end]`, `source_range:[0,duration]`, `output_frames:[first,last_exclusive]`, `source_frames:[0,frame_count]`. Seconds, half-open, contiguous from frame 0, no gaps/overlaps; seconds equal frames/30 within 0.001 s; the final end equals the decoded frame count of solution.mp4.
3. `output/selection-evidence.json` — array of seven objects `{beat, source, source_frames:[a,b] (b−a ≥ 12, both inside the clip), reason}` where the reason names a concrete visible difference between the chosen clip and the most similar other candidate.

`output/` must contain exactly these three files.

## How the result is judged
Each beat's choice is compared with a hidden reference; the encoded video is checked frame-by-frame against the clip you name. The evidence file is reviewed by a person/judge. The detailed scoring sheet is not part of this package.
