# WFA-CDN-006 — One candidate pool, two intents: a comedy trailer and a suspense trailer

## Situation and inputs
`input/01.mp4` … `input/39.mp4` are 39 anonymous, silent candidate clips excerpted from a licensed open animated short. They are H.264, 640×360 square pixels, 24 fps, and 6.7–12 s each. Clip numbers are random and carry no story-order information. Many candidates overlap in time or cover the same scene with different in and out points.

Everything you need is inside the task directory, and there is no network. Use `work/` for scratch files and `output/` for deliverables. Python 3.11 and FFmpeg/ffprobe are available. There is no GPU, and generated imagery is not allowed.

## Task
Cut two short trailers from the same pool. Each trailer has 5 ordered slots, and each slot takes 1 candidate.

- **Version A, comedy trailer:** makes the audience laugh through timing, contrast, and gags.
- **Version B, suspense trailer:** makes the audience tense through watching, threat, and delay.

Each slot is defined by its narrative function and its film language. The chosen clip must satisfy every part of the slot description, including how the clip opens and how it ends. Cuts already inside a clip count as part of that clip.

## Assembly contract
- Use each clip in full, at 1× speed and in its original direction. Do not crop, mirror, grade, or add text. Do not add or drop frames, and add no transitions or generated content. Join clips with hard cuts.
- Within one version, the 5 clips must all be different. The two versions may use the same candidate.
- Each version must be 640×360, constant 24 fps, with no audio.

## Version A: comedy trailer

### A1 Entrance with irony
- Function: a smug little gang makes its entrance. The audience sees a hazard hanging over their heads; they do not.
- Film language: the clip opens on a tight close group shot of three small characters, from an eye-level to slightly low camera, as they press toward the lens. It then cuts to a low angle with a heavy object suspended at the top of frame, and a huge arm sweeps past the frame edge. It ends on a medium close shot of the leader holding a small object. The whole clip stays on the gang.

### A2 Peek gag
- Function: a single-take gag built on timing: a peek, a retreat, and then the bystander pays for it.
- Film language: one locked-off camera for the whole clip. A near tree trunk at frame left acts as a foreground screen, and a bird stands on a branch a little further away at frame right. A character peeks out from behind the trunk and ducks back. The bystander is then hit by a small object flying in from off-screen and leaves the frame. The clip ends on the empty branch.

### A3 Chain of close calls
- Function: an oblivious small character dodges several "disasters from nowhere" one after another and carries on as if nothing happened. The gag escalates and pays off.
- Film language: a wide shot that stays on this small character throughout. The clip opens with a calm hold. Then a first large object rolls in from one side and grazes past, followed by other large objects toppling or dropping. The clip ends with the character alone in frame, unharmed and still absorbed in its own business.

### A4 Deadpan scale contrast
- Function: a huge figure silently appears behind the small character, who notices nothing. The laugh comes from the difference in size and a long pause.
- Film language: one essentially fixed framing. The small character is in the foreground, busy with what is in front of it. The huge character walks in from the frame edge and stops right behind it. The two then share the frame, and the pause holds until the clip ends.

### A5 Closing button
- Function: the character who thinks it is winning walks straight into the opponent's grip. The captor's sly grin is the button, then the picture starts to fade out.
- Film language: a medium shot opens on a small character edging along a branch toward a huge figure at frame right whose back is to camera. A big hand grabs it. The clip cuts to a close two-shot of the two, with the captor grinning. It ends while the picture is fading down toward black.

## Version B: suspense trailer

### B1 Being watched
- Function: establish the unease that someone in the dark is watching.
- Film language: the clip opens on a low-angle wide shot of several small characters walking along a path toward camera. One of them walks right up to the lens and fills the frame, giving a wipe-like transition. The clip cuts to a high-angle subjective view looking down on them through foreground leaves, and a huge dark shape intrudes from the right foreground. It ends back on an eye-level medium shot of them, unaware.

### B2 The threat behind
- Function: the audience sees the danger; the character does not.
- Film language: deep staging in one essentially fixed framing. An unsuspecting small character is in the foreground, head down and busy. A huge silhouette walks in from off-screen and stops behind it, looming over it. The clip stays in this tension without release.

### B3 Watching from cover, then a strike
- Function: a hidden figure watches from cover, then a strike from off-screen makes the bystander vanish.
- Film language: one locked-off camera for the whole clip. A near tree trunk screens the foreground, and a bystander sits on a branch further away. The hidden figure leans out and disappears again. The bystander is suddenly hit by something flying in from off-screen and vanishes from frame, leaving an empty shot.

### B4 Delay and shock
- Function: hold on an unsuspecting character long enough to make the audience wait. Danger finally breaks in, but the clip cuts away before the outcome; the suspense is left unresolved.
- Film language: a wide shot with a static camera. The clip opens with a long, still hold. A huge object then rolls in from off-screen and closes on the character. The clip ends at the most dangerous moment, as the object bears down on the character, without showing what happens.

### B5 Stinger
- Function: a harmless small object falls and exposes a danger hidden in the ground, leaving an unresolved threat.
- Film language: a low-angle wide shot of an empty patch of ground. A small object drops in from the top of frame and bounces. A hard cut to a close insert shows it impaled on something hidden in the ground. The clip ends on a static wide shot of a clearing covered with these hidden things, with no character in frame.

## Deliverables (public format specification)
1. `output/comedy.mp4` and `output/suspense.mp4`: each joins its 5 full clips in slot order. They must be H.264/yuv420p, 640×360, SAR 1:1, 24/1 fps, with no audio. Lossless concatenation is allowed, and so is re-encoding at CRF ≤ 18.
2. `output/edl.json`: `{"comedy":{"segments":[...]}, "suspense":{"segments":[...]}}`. Each version holds exactly 5 objects in slot order, with these fields:
   - `slot`: `"A1"`…`"A5"` or `"B1"`…`"B5"`;
   - `source`: `"NN"`;
   - `output_frames`: `[start frame, end frame (exclusive)]`;
   - `source_frames`: `[0, frame count]`;
   - `output`: `[start, end]` in seconds.

   Intervals are half-open and contiguous from frame 0, with no gaps or overlaps. Seconds must be within 0.001 s of frames/24. Each version's final end frame must equal the actual decoded frame count of its mp4.
3. `output/selection-evidence.json`: an array of 10 objects `{version:"comedy"|"suspense", slot, source, source_frames:[a,b], reason}`. Require b−a ≥ 12, with both values inside the clip. `reason` must name one specific visible difference from the most similar other candidate.

`output/` must contain exactly these 4 files.

## Judging
Every slot choice is compared with a hidden reference selection. The encoded videos are checked frame by frame against the clips you declare in `edl.json`. The evidence file is reviewed by humans or judges. The detailed scoring criteria are not included in this package.
