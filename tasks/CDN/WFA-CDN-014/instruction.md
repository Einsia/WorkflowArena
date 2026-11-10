# WFA-CDN-014: Why the North Node Failed

Prepare a 12-minute English briefing for a **state transportation department's bridge program steering committee**: program managers and local-agency oversight leads who approve and supervise unusual bridge projects. They are engineers, but not specialists in concrete truss design. The briefing answers one question:

**A partially built pedestrian truss span collapsed onto an open roadway days after it was set on its supports, while a crew was working on it. What failure mechanism brought it down, when did evidence of that mechanism become visible to the project team, and where could the sequence have been stopped — and what does the evidence *not* allow us to conclude?**

Use only the material in `input/`. Do not add facts, numbers or events from outside it. Apart from simple arithmetic on published values, do not perform new structural analysis.

## 1. Material
- `input/report.pdf`: the investigating agency's final report on the collapse.
- `CREDITS.md`: source category and licence.

No values are pre-extracted for you. Every number, time, date, count and conclusion you present must come from the report and be traceable to a page.

## 2. Briefing
- 9–11 slides, 16:9, including a title slide and a closing slide; no empty section dividers.
- Spoken length about 12 minutes (11–13 acceptable), timed at a delivery rate of 130–150 words per minute.
- The briefing must explain the mechanism from design to physical failure, show when and how the distress was observed and interpreted on site, assess where the sequence could have been interrupted, and close with a direct answer to the question, including its limits.
- Every slide title is a claim the slide supports.

## 3. Deliverables (in `output/`)
| File | Requirement |
|---|---|
| `presentation.pptx` | The deck. Must open in Windows desktop Microsoft PowerPoint (16.0) **without any repair prompt**, and remain fully functional when copied alone to another folder on an offline machine. |
| `slides.pdf` | Static export of the same slides. |
| `script.md` | Verbatim per-slide script with per-slide timing, marking every click, trigger and media event. The same per-slide text goes in the PPTX speaker notes. |
| `calculations.xlsx` | Every quantity you derive (anything not printed verbatim in the report), with source values, units, page references and live formulas. |
| `event-clip.mp4` | The media clip embedded in the deck (see §4), also delivered as a file. |
| `evidence-index.csv` | One row per fact-bearing slide element: slide, element, claim, printed page and PDF page, figure/table/section number, transformation (quote, crop, conversion, recomputation). |
| `playback-check.md` | What you actually verified, how, with which software and version, and what you could not verify. Claims without evidence earn nothing. |

## 4. Native objects, dynamics and media
- **Native charts**: at least **2** native, editable PowerPoint charts with data you transcribed from the report. "Edit Data" must open for each; the embedded workbook lists source values, units and pages. No invented intermediate points. At least one of these charts is **built progressively in the slide show** (native chart animation by series or by category, not stacked images).
- **Report figures**: at least **2** real figures from the report, cropped legibly with legends kept, explained with native (editable) callouts. A full-page screenshot is not an explanation.
- **Mechanism chain**: one slide that builds the failure mechanism from native, separately editable shapes and connectors, revealed link by link with **at least 6** on-click entrance animations in mechanism order.
- **Evidence timeline**: one slide with a dated timeline of what was observed and decided on site before the collapse. At least **5** dated entries are each a **PowerPoint trigger** (an animation fired by clicking that shape, not a hyperlink or slide jump) that reveals a separate, editable panel: what was recorded, by whom, and how it was interpreted at the time.
- **Event clip**: a 4–12 s H.264 MP4 (1280×720 or 1920×1080) assembled **only** from the report's still images of the collapse as it happened, embedded in the deck (not linked) and started by a click. Each still carries an on-frame label with its time from the report. The clip must make clear that it is a sequence of stills, not original footage, and its pacing must represent the real elapsed time between the stills, either 1:1 or with a slow-down factor stated on screen.

## 5. Quality
- Body text ≥ 20 pt; captions and source lines ≥ 12 pt; ≤ 6 bullets per slide; nothing overlaps or is clipped in any animation state.
- Explain technical terms for this audience. Use one consistent visual coding to separate facts established by the investigating agency, the agency's analysis and judgement, and your own inference.
- State that the briefing was produced with AI assistance; credit the source; do not imply review or endorsement by any agency or company named in the material.
- Key numbers and conclusions must agree across slides, notes, chart workbooks, `calculations.xlsx`, script, PDF and evidence index.

## 6. Tools and evaluation
You may use any local PDF/text tools, Python, FFmpeg, LibreOffice and python-pptx. The target playback environment is Windows desktop Microsoft PowerPoint 16.0; verify the delivered files as far as you can.

Reviewers score against a **non-public checklist**: coverage of and fidelity to the material, correctness of your reasoning and arithmetic, narrative, visual design, and the behaviour of native objects, animations and media in real PowerPoint. Each check is pass/fail; partial satisfaction fails. If PowerPoint needs to repair the file to open it, every media and animation check fails.
