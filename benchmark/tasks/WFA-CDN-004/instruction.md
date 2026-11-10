# WFA-CDN-004 — Machine Runaway: 6-slot state-change assembly cut to beats

## Inputs
- `input/clips/01.mp4` … `input/clips/44.mp4`: 44 anonymous, silent candidate clips (H.264, 1280×720, SAR 1:1, 30 fps, 6–12 s each) excerpted from licensed open animated films. Numbering is random and carries no story order. A clip may contain cuts from the original film.
- `input/beats.json`: the beat map of the final cut (frame numbers at 30 fps). For every slot it gives `start_frame`, `end_frame` (exclusive) and one accent frame `accent_frame`.

The environment is offline; everything needed is in the task directory. Drafts go in `work/`, deliverables in `output/`.

## Requirements
For the 6 ordered slots below, choose one candidate per slot (6 distinct candidates), take one contiguous sub-range from it, and join them with hard cuts in slot order so that every cut lands exactly on the slot boundaries in beats.json.

- Sub-ranges are used at 1× speed, forward, with the original picture: no retiming, no dropped/duplicated frames, no crop, mirror, grade, text, transitions or generated content.
- Each slot's **change point** (the first frame at which the later state of the slot's "change" holds) lands on that slot's `accent_frame`.
- Each slot describes the main content of its sub-range: the state before the change, the change itself, and the state after it all appear within the slot. Because slot lengths are fixed, the head or tail of a sub-range may unavoidably carry brief adjacent shots from that candidate's original cuts; this is allowed.

## Ordered storyboard

**Slot 1 | Overload.** In a pitch-black void, a lanky young man and a bald old man stand side by side on a small floating platform; full-figure long shot, camera essentially locked. Change: a blinding flash, and the surroundings turn from total black into a bright, heavily motion-blurred grey-white space, the two still standing on the platform.

**Slot 2 | Power cut.** An open square hatch in a green tiled wall with a lamp lit inside it; close shot, locked camera. A tiled panel slides down over the hatch and a pair of gloved hands presses it flat. Change: the picture drops to full black; afterwards a wide engine room slowly emerges from the dark with two figures standing in it.

**Slot 3 | Intrusion.** An empty square room with bare walls; frontal symmetrical long shot, locked camera; the young man swings his arms in the middle of the room. Change: dark cables pour out of the left corner and crawl over the left wall.

**Slot 4 | Breach.** A tilted low-angle close shot hugging a tiled wall with a metal pipe running along it; the camera slides along the wall. Change: cables burst through the wall, debris flies, and the warm orange, cable-filled space behind it is fully revealed.

**Slot 5 | Encirclement.** The bald old man stands alone before a golden curtain of vertically flowing light, hands clutching his head; medium shot, camera essentially locked. Change: the curtain behind him turns into rows of dark machinery studded with red indicator lights.

**Slot 6 | Failure.** The old man stands alone in diagonally falling streaks of light; full-figure long shot, the camera settling to rest. Change: the warm orange light of the whole scene drains away into a dim, cold green.

## Deliverables (exactly these 3 files in `output/`)
1. `output/solution.mp4`: H.264 / yuv420p, 1280×720, SAR 1:1, constant 30/1 fps, no audio; decoded frame count equals `total_frames` in `beats.json`. Lossless concat or re-encode at CRF ≤ 18.
2. `output/solution.json`: `{"segments":[...]}` with exactly 6 objects in slot order, each with `slot` (1–6), `source` (e.g. `"07"`), `source_frames:[a,b]` (decoded frame indices inside the candidate, half-open), `output_frames:[c,d]` (frame indices in the final cut, half-open).
3. `output/events.csv`: header `slot,source,source_frame,output_frame`, one row per slot, declaring the frame you identify as the change point in the candidate and its frame in the final cut.

All frame numbers start at 0 and count fully decoded frames.

## Judging
Each slot's choice is compared with a hidden key; the final video is checked frame by frame against the declared candidate sub-ranges; change points are checked at the frames declared in `events.csv`.
