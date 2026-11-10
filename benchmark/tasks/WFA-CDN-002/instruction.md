# WFA-CDN-002 — Assemble a 6-slot mourning sequence from 42 anonymous candidates (with one J-cut)

## Situation and input
`input/01.mp4` … `input/42.mp4` are 42 anonymous candidate clips. They are excerpts from a licensed open animated film and carry their original production sound. Specs: H.264, 1280×544, SAR 1:1, 24 fps; AAC stereo 48 kHz; 6–12 s each. The numbering is random and carries no story-order information.

Everything you need is inside the task directory; there is no network. Put drafts in `work/` and deliverables in `output/`. Environment: Python 3.11 and FFmpeg/ffprobe; no GPU; no generative content.

## Goal
Cut a six-beat mourning passage. It starts from the numbness after a loss, passes through memory, and arrives at release. The six slots below are in a fixed order. Choose one candidate per slot. The six candidates must all be different, and each must match every field of its slot. Cuts that already exist inside a clip stay as they are.

## Assembly contract
- **Picture:** Use each clip in full, at 1× speed, in its original direction. Do not crop, scale, mirror, grade, add titles, add transitions, or add or drop frames. The only exception is slot 6; see the J-cut below. Join all shots with straight cuts.
- **Sound:** Use only the production sound that comes with each chosen candidate, frame-synchronous with its picture. Do not add other sound. Do not use fades or crossfades.
- **J-cut (slot 5 → slot 6):** Slot 6's sound enters 24 frames (1.0 s) before its picture and replaces the last 24 frames of slot 5's sound.
  - Sound: slot 6 plays from candidate frame 0 to the end.
  - Picture: slot 6 plays from candidate frame 24 to the end.
  - Slot 5's picture stays complete. All other cuts are straight cuts in both picture and sound.

## Ordered shot list

### Slot 1
- Narrative function: the starting point of grief; the character is sunk in loss.
- Content: a single shot. A close shot of a young red-haired woman against a background of tangled tree roots. At the start, her head is bowed and her hair hides her face. She slowly lifts her face. Her gaze first falls downward, then turns to screen right and stays there until the clip ends.
- Shot size: close shot (head and shoulders).
- Angle: front three-quarter, slightly above eye level.
- Camera: locked off; all change in the frame comes from the character.

### Slot 2
- Narrative function: memory, the warmth of meeting.
- Content:
  - Low angle: a small winged creature stands on a wooden beam, opens its wings, then folds them.
  - Cut to a smiling close shot of the woman against a bright timber-roof background.
  - Cut back to the creature crouched quietly on the beam while a flock of birds crosses the sky. The clip stays on this image.
- Shot size: medium on the creature, close on the woman.
- Angle: low angle on the creature, eye level on the woman.
- Camera: locked off.

### Slot 3
- Narrative function: memory, the peak of joy.
- Content:
  - High ground at sunset. The woman starts walking from beside a stone pillar toward the camera.
  - Once she is close, she cups her hands around her mouth and calls out.
  - Cut to a run of hard-backlit images: her silhouette, with small flying dragons circling around her. The clip ends inside the backlit images.
- Shot size: full shot, with her walking into a medium close-up; the backlit images are full and medium shots.
- Angle: eye level or slightly below.
- Camera: the calling shot is locked off; in the backlit images the camera moves with her.

### Slot 4
- Narrative function: memory, the loss.
- Content:
  - A small winged creature glides alone in a pink-orange sky.
  - A huge dragon's head dives into frame from the top.
  - Cut to a wider image: the dragon sweeps over the rooftops.
  - Over the woman's back: she reaches out, the dragon's claws seize the small creature, then her horrified face.
  - Cut to the small creature being carried off in the dragon's grip, with the woman's open hand in the foreground reaching after it. The clip ends on this foreground-hand image.
- Shot size: medium in the sky, long shot over the roofs, over-the-shoulder medium, foreground hand close shot.
- Angle: mostly low angle, including an over-the-shoulder view.
- Camera: pans and tracks that follow the flyers; fast pacing.

### Slot 5
- Narrative function: back to the present, the stillness of grief.
- Content: a single shot. An extreme long shot of a barren high cliff. The woman sits alone at the edge, small in frame, with misty mountains behind her. The clip stays on this image throughout.
- Shot size: extreme long shot.
- Angle: eye level, side-on.
- Camera: locked off, with almost no movement in frame.

### Slot 6
- Narrative function: release and departure (J-cut entry).
- Content:
  - A single shot. Ground-level low camera, with white snowdrop flowers in the right foreground.
  - At the start, the frame holds only the foreground flowers and the small figure of the woman walking away in the distance.
  - Midway through the clip, a small winged creature flies in low from the left, lands, pauses for a moment, then turns its back to the camera and crawls away into the distance.
  - The clip ends while it is still crawling away.
- Shot size: long shot, with the foreground flowers in close shot.
- Angle: ground-level low angle.
- Camera: locked off.

## Deliverables
1. `output/sequence.mp4`: the assembled sequence in slot order.
   - Video: H.264/yuv420p, 1280×544, SAR 1:1, constant 24/1 fps.
   - Audio: one AAC-LC stereo 48 kHz track.
   - Audio and video durations are equal to within 1 frame.
   - Lossless concatenation or CRF ≤ 18 re-encode.
2. `output/edl.json`: `{"segments":[...]}` with exactly 6 objects in slot order.
   - Each object has the fields `slot`, `source:"NN"`, `picture:{output_frames:[a,b], source_frames:[c,d]}`, and `sound:{output_frames:[a,b], source_frames:[c,d]}`.
   - Units are 24 fps frames; intervals are half-open.
   - The `picture` segments run contiguously from frame 0 with no gaps or overlaps; the `sound` segments do the same.
   - The last `picture` end frame equals the actual decoded frame count of sequence.mp4.
3. `output/selection-evidence.json`: an array of 6 objects `{slot, source, source_frames:[a,b], reason}`.
   - `source_frames` must lie inside the chosen clip, with b−a ≥ 12.
   - `reason` must name one concrete visible difference between the chosen clip and the most similar other candidate.

`output/` must contain exactly these three files.

## Judging
- Each slot choice is compared with a reference selection.
- The picture and sound of the sequence are checked frame by frame against your EDL and the original candidates.
- The evidence file is reviewed by humans.
- The detailed scoring sheet is not part of this package.
