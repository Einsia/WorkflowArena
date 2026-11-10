# WFA-CDN-003 — Assemble a 7-slot "confrontation → escape" sequence from 45 anonymous candidates

## Situation and inputs
You receive 45 anonymous, silent candidate clips `input/01.mp4` … `input/45.mp4` (H.264, 1280×720, SAR 1:1, 24 fps, 6–12 s each). They are excerpts of licensed open-movie animation; source attribution is provided in `CREDITS.md`. Clip numbers are random and carry no story-order information. Several candidates overlap in time or show the same scene in similar pictures. Everything you need is in the task directory; there is no network and none is needed. Put scratch work in `work/` and deliverables in `output/`. Python 3.11 and FFmpeg/ffprobe are available; no GPU, no video generation.

Two characters run through the sequence: a thin boy and a bald old man in a dark coat.

## Assembly contract
- For each of the 7 ordered slots below pick 1 candidate — 7 **distinct** candidates in total — each matching every field of its slot.
- Use each clip once, complete, at 1× speed and in its original orientation: no cropping, mirroring, filters, text, added or dropped frames, transitions or generated content; cuts already inside a clip stay as they are. Join with hard cuts.
- **Axis continuity:** the whole sequence obeys the 180° rule. Slot 1 establishes the line of action between the two characters; in every later slot the characters' left/right screen relationship, the eyeline direction of single shots and the characters' screen direction of movement must stay consistent with the axis established in slot 1 — no line crossing.
- Output 1280×720, constant 24 fps, no audio.

## Ordered shot list

### Slot 1 — Establishing: two people in danger
- Narrative function: establish the space and the two characters' initial situation.
- Content: a cold cyan mechanical space; a suspended grated platform runs across the frame, a tall wall of buttons and mist behind it. The thin boy is sprawled and struggling on the platform on **frame left**; the bald old man stands on **frame right**, bending and looking toward the boy.
- Shot size: extreme wide; both characters are small full figures.
- Angle and lens language: side-on, eye level; the platform roughly parallel to the bottom of frame.
- Camera movement: a single continuous locked-off shot.

### Slot 2 — First exchange: shot/reverse shot
- Narrative function: the two speak face to face for the first time.
- Content: most of the clip is a profile close-up of the boy against a pale riveted metal wall; he looks up and speaks several lines. Then a cut to a single close-up of the old man, leaning forward and replying.
- Shot size: close-up against close-up.
- Angle and lens language: two near-eye-level profile / three-quarter singles forming a shot/reverse shot; soft background.
- Camera movement: locked off.

### Slot 3 — Standoff in a closed room
- Narrative function: build silent tension through alternating singles.
- Content: a dark-red room. The clip opens on a medium close single of the old man, then a medium single of the boy, then a close-up of an old candlestick telephone, then a brief high-angle view down on the old man, ending back on a close single of the old man.
- Shot size: alternating medium close, medium and close-up.
- Angle and lens language: singles are near-eye-level frontal three-quarters, with one high-angle shot between them.
- Camera movement: essentially static.

### Slot 4 — Escalation: the receiver
- Narrative function: the standoff turns physical.
- Content: the clip opens directly on the boy walking toward the old telephone in the foreground and reaching out; cut to an over-the-shoulder shot past the back of the boy's head as the old man reaches across, snatches the receiver and holds it up toward the lens.
- Shot size: medium-full of the boy, then over-the-shoulder close.
- Angle and lens language: low camera with the telephone filling a large foreground block; then an over-the-shoulder reverse.
- Camera movement: mostly static; change comes from action and the cut.

### Slot 5 — Restaging
- Narrative function: a change of positions within the confrontation that sets up a new two-shot.
- Content: a warm brown hall with a huge arched grille door behind. The old man starts with his back to camera, then turns to face it; the boy walks into frame and stops beside and behind him, forming a foreground/background two-shot as they keep talking.
- Shot size: medium two-shot, old man in the foreground.
- Angle and lens language: eye level, one continuous shot.
- Camera movement: locked off.

### Slot 6 — The escape begins: through the doorway
- Narrative function: the two leave the light for unknown darkness.
- Content: inside a door, a heavy black curtain on one side and a bright doorway on the other. The old man squeezes in from the light and looks around warily; the boy follows close behind him.
- Shot size: medium to medium close as the characters come toward the lens.
- Angle and lens language: eye level from the dark interior facing the doorway, strong backlight; one continuous shot.
- Camera movement: locked off.

### Slot 7 — Escape: leaving the other behind
- Narrative function: the old man goes ahead and the boy is left behind.
- Content: a dim space with green shafts of light. One continuous shot: it opens with the boy standing at the edge of a platform and the old man already on a nearby thin tall post; the old man then hops from post to post away from him, and the boy gradually leaves frame.
- Shot size: full shot.
- Angle and lens language: eye level, slightly low.
- Camera movement: the camera trucks with the old man in the direction of his hops.

## Deliverables (public format spec)
1. `output/solution.mp4` — the 7 complete clips in slot order. H.264/yuv420p, 1280×720, SAR 1:1, 24/1 fps, no audio. Lossless concat or re-encode at CRF ≤ 18.
2. `output/solution.json` — `{"segments":[...]}` with exactly 7 objects in slot order: `slot` (1–7), `source:"NN"`, `output_frames:[start, end (exclusive)]`, `source_frames:[0, frame count]`, `output:[start,end]` (seconds). Frame intervals are integer half-open, contiguous from frame 0, no gaps or overlaps; seconds differ from frames/24 by at most 0.001 s; the final end frame equals the actual decoded frame count of solution.mp4.
3. `output/selection-evidence.json` — an array of 7 objects `{slot, source, frames:[a,b] (two frame numbers inside the chosen clip), reason}`; reason must name one concrete visible difference between the chosen clip and the most similar other candidate.

`output/` must contain exactly these three files.

## Judging
Each slot's choice is compared with a hidden reference; the encoded video is checked frame by frame against the clips you declare. Detailed scoring criteria are not included in this package.
