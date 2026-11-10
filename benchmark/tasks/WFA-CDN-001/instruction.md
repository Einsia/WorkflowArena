# WFA-CDN-001 — Pursuit and Search: assemble a 7-slot sequence from 40 anonymous candidates

## Situation and input
`input/01.mp4` … `input/40.mp4` are 40 anonymous, silent candidate clips (H.264, 1280×720 square-pixel 16:9 letterboxed canvas, 30 fps, 6–12 s each), excerpted from licensed open animated films; source attribution is provided in `CREDITS.md`. Numbering is random and carries no story order. Everything you need is in the task directory; there is no network. Put drafts in `work/` and deliverables in `output/`. Python 3.11, FFmpeg/ffprobe and OpenCV are available; no GPU, no generated content.

## Ordered shot list
Pick one candidate for each of the 7 ordered slots below (7 distinct candidates). The chosen clip must match every part of its slot description.

**Slot 1 · Establishing: the endless snowfield**
Aerial. Snow-covered crags and blue ice in the foreground; past them an open snowfield, one tiny walker and a winding line of footprints behind them. Single shot. Camera: a steady aerial fly-forward with a continuous lateral drift, at an even speed.

**Slot 2 · Collapse: the searcher gives out**
Close-up of a red-haired woman's face as she lies on her side in the snow; tilted, ground-level framing, snow drifting past. Single shot. Camera: a slow push-in on her face with a slight drift, continuing to the end of the shot.

**Slot 3 · Transition: the remembered city**
A city panorama fading up from black (dense rooftops, a tower in the distance), cut to a high-angle shot looking down a narrow alley. Two shots. Camera: both shots locked off; the framing does not change within either shot.

**Slot 4 · Searching along the wall**
The frame opens almost entirely covered by a large dark foreground mass; it sweeps away to reveal a short-red-haired girl against a sunlit wall; she leans out to look and moves along the wall, and the framing ends behind her shoulder. Single shot. Camera: a lateral tracking move travelling with her, with a slight handheld feel.

**Slot 5 · The chase**
Close shot of the short-red-haired girl turning away; wide shot of her running down a narrow alley; she climbs over the edge of a roof; an injured small winged creature on the roof tiles. Camera: in both the running shot and the creature shot the camera pushes forward.

**Slot 6 · Discovery and approach**
Close-up of the girl's gaze; a hand reaching toward the small winged creature on the tiles; close-up of the girl breaking into a smile. Three shots. Camera: the two face close-ups are locked off; the middle shot pulls back while trucking sideways, gradually opening up the hand–creature relationship.

**Slot 7 · Losing control**
High overhead view of a dim interior, papers and clutter strewn on the floor; the image becomes turbulent later in the shot. Single shot. Camera: completely static at first, then it starts to push forward and keeps accelerating.

## Assembly contract
- For each slot use **one contiguous range** of the chosen clip: 1× speed, forward, no scaling, cropping, mirroring, filters, text, frame interpolation or generated content; the range must keep every shot and the whole camera move described for that slot. Cuts inside a clip stay as they are.
- Join the 7 segments in slot order with **hard cuts** — no transitions, no black.
- The finished sequence is **exactly 1650 frames (55.0 s)** long.

## Deliverables
1. `output/assembly.mp4` — H.264/yuv420p, 1280×720, SAR 1:1, constant 30/1 fps, no audio, 1650 frames.
2. `output/selection.json` — `{"slots":[...]}` with exactly 7 objects in slot order:
   - `slot`: 1–7; `source`: two-digit string such as `"07"`;
   - `source_frames`: `[a,b]`, the frames used from that clip, half-open, 0-based;
   - `output_frames`: `[c,d]`, the segment's frames in the assembly, half-open; the 7 segments start at 0 and abut; the last `d` = 1650 = the decoded frame count of the assembly; `b−a = d−c`;
   - `closest_alternative`: the other candidate you consider most similar to your pick but not right for this slot;
   - `reason`: one sentence naming a concrete visible difference between the two.

`output/` must contain only these two files.
