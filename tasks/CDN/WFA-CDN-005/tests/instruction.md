# WFA-CDN-005 — Assemble a 7-slot, fixed-length 52-second sequence from 45 anonymous candidates

## Situation and inputs
`input/01.mp4` … `input/45.mp4` are 45 anonymous, silent candidate clips (H.264, 640×360, SAR 1:1, 24 fps, 6–12 s each) excerpted from a licensed open animated film. Numbering is random and carries no story order. Several candidates overlap in time or show different portions of the same event. Everything needed is in the task directory; there is no network. Put scratch work in `work/` and deliverables in `output/`. Python 3.11 and FFmpeg/ffprobe are available; no GPU, no generated content.

## Assembly contract
- Choose one candidate for each of the 7 ordered slots below; the 7 candidates must all be different.
- From each chosen candidate you may take **one contiguous sub-range**, at 1× speed and in original direction — no scaling, cropping, mirroring, filtering, text, frame interpolation or frame dropping. Cuts already inside a candidate stay as they are.
- After trimming, every segment must still show everything its slot describes, in the described order.
- Hard cuts only between segments, no transitions. No flash frames at edit points: each segment's in-point and out-point must be at least 12 frames away from any original cut inside that segment.
- The finished sequence is exactly **1248 frames (52.000 s)** long.

## Ordered shot list

### Slot 1 · Waking
- Narrative function: opening; establish the protagonist and his home, bringing him "on stage" out of darkness.
- Content: the mouth of a burrow, at first completely dark inside; the protagonist's face gradually emerges from the darkness and his ears rise. Hard cut to a side wide shot: he crawls out of the hole, stands up and stretches.
- Camera language: medium shot of the burrow at eye level; side wide shot from a slightly low camera; both shots locked off.

### Slot 2 · Greeting the morning
- Narrative function: establish his good mood.
- Content: looking up at the sky, the protagonist rises into frame from the bottom edge and stretches; cut to a medium close-up of him against treetops and sky, smiling contentedly.
- Camera language: low-angle upshot, then an eye-level medium close-up; locked off.

### Slot 3 · Absorbed
- Narrative function: he is lost in nature, while hinting that someone is watching.
- Content: white flowers in the foreground; the protagonist walks up from the distance and leans in to smell them; cut to a wide shot of him from behind; then a shot through leaves, past a dark blurred foreground shape, toward the small distant protagonist; finally a close-up of him smelling the flowers, enraptured.
- Camera language: medium shot with foreground occlusion, wide shot, voyeuristic wide shot with foreground occlusion, close-up.

### Slot 4 · A tender contact
- Narrative function: his gentlest moment, foreshadowing a later loss.
- Content: the protagonist faces camera; a purple butterfly flies in from off-screen, settles on the tip of his nose, then lifts off and circles him while he breaks into an open-mouthed laugh; cut to his back as he walks toward a large tree in the distance.
- Camera language: medium close-up, locked off; then a full shot from behind.

### Slot 5 · The threat gathers
- Narrative function: the antagonists appear and gather.
- Content: behind a fallen tree trunk, at first only one grey, fluffy small animal is present; a red small animal then joins it, and a third climbs out over the top of the trunk; a fruit they were holding drops onto the grass.
- Camera language: low-camera medium shot, a single locked-off shot.

### Slot 6 · The strike
- Narrative function: the conflict erupts; cause and effect are complete within one segment.
- Content: it starts with the throw from behind the trunk, a fruit flying out of frame; cut to a wide shot of the protagonist alone in the meadow, struck by fruit after fruit, the last one — a red fruit — landing squarely on top of his head; cut back behind the trunk, where they keep throwing.
- Camera language: low medium shot behind the trunk, eye-level wide shot, medium shot again.

### Slot 7 · Humiliation
- Narrative function: ending — the protagonist routed, his tormentors triumphant.
- Content: a wide shot of an empty meadow and a large tree; the protagonist dashes in from frame left and runs for the trunk through a hail of falling green fruit; cut to beside the trunk, where he hides and peers out, shaken; cut to a wide shot of the three small animals jumping for joy under a tree.
- Camera language: wide shot, medium shot beside the trunk, wide shot.

## Deliverables (public format spec)
1. `output/solution.mp4`: the 7 segments in slot order. H.264, yuv420p, 640×360, SAR 1:1, constant 24/1 fps, no audio track; lossless or CRF ≤ 18. Exactly 1248 frames.
2. `output/solution.json`: `{"segments":[...]}` with exactly 7 objects in slot order, each `{"slot":k, "source":"NN", "source_frames":[a,b], "output_frames":[c,d]}`. Integer frame numbers, half-open intervals; `source_frames` are relative to frame 0 of the chosen candidate; `output_frames` start at 0 and are contiguous with no gaps or overlaps, `d−c = b−a`, and the last `d` equals 1248.

`output/` must contain only these two files.

## How it is judged
Chosen clips are compared with a hidden key, and the declared ranges are checked frame by frame against the rendered sequence. The detailed scoring sheet is not included in this package.
