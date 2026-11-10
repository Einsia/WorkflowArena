# WFA-CDN-007 — Cutting picture to a narration script for a science short

## Situation and inputs
The narration for a 43-second science short about how coral reefs reproduce has been locked. Your job is to cut the picture to it.

- `input/narration.en.txt` (Chinese version: `narration.zh.txt`): the narration script. It has 6 time windows, and each line is marked with the programme time at which it starts.
- `input/clips/01.mp4` … `37.mp4`: 37 anonymous candidate clips of underwater documentary footage.
  - Format: H.264, 1280×720, 30 fps, silent, 6–11 s each.
  - Numbering is random and carries no order information.

Everything you need is inside the task directory; there is no network. Put drafts in `work/` and deliverables in `output/`. Generating or synthesising picture is not allowed.

## Editing requirements
- **One clip per window:** fill each time window with exactly one candidate, using 6 distinct candidates in total.
- **Taking the shot:** from the chosen candidate, take one contiguous source range whose length is exactly the window length.
  - 1× speed, original direction.
  - No crop, scale, mirror, grade, text, or transition.
- **Joining:** join the windows with hard cuts.
- **Picture follows narration:** within each window, the picture must match what that window's narration says for the whole window.
- **In-window sync:** where a second narration line starts after the window start, the picture event that line describes must land on that line's start time.
- **Output:** 1280×720, constant 30 fps, no audio, 43.0 s total (1290 frames).

## Deliverables
`output/` must contain exactly these three files:

1. `output/solution.mp4`
   - H.264/yuv420p, 1280×720, SAR 1:1, 30/1 fps, no audio track, 1290 frames.
2. `output/edl.json`
   - Format: `{"segments":[...]}`, exactly 6 objects in time order.
   - Each object has these fields (frame numbers are integers, half-open intervals):
     - `window`: 1–6;
     - `source`: candidate ID, e.g. `"NN"`;
     - `source_frames`: `[a,b]`, counted from the candidate's own frame 0;
     - `output_frames`: `[c,d]`, contiguous from 0 with no gaps or overlaps, and `b−a = d−c`.
3. `output/events.csv`
   - Header: `line_time_s,output_frame`.
   - Write one row for every narration line that starts after its window start:
     - `line_time_s`: the line's start time;
     - `output_frame`: the frame of `solution.mp4` at which the picture event described by that line begins.

## Assessment
- The cut is traced frame by frame back to the candidate clips and checked against `edl.json`.
- The clip and range chosen for each window are compared with hidden reference decisions.
- The frames declared in `events.csv` are verified in the cut.
- Detailed scoring criteria are not included in this package.
