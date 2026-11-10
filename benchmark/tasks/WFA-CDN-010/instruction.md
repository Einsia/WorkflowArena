# WFA-CDN-010: Why a corn mill came down in one night

Prepare an **English** briefing for the board and plant managers of a mid-sized food-ingredient manufacturer. The audience understands operations but is not expert in explosion engineering or process safety. The briefing answers one question:

> **In the incident documented in `input/`, which technical conditions and which management conditions acted together to turn an ignition inside equipment into multiple explosions, collapsed buildings and casualties? Which of those conditions could have been recognised and controlled beforehand? How far does the evidence in the materials go, and what remains uncertain?**

## 1. Materials
- Use only the materials in `input/`: a long public incident-investigation report (PDF), technical attachments released with it (PDF), and one public web page from the publisher (HTML). Do not add facts, numbers or events from outside the pack.
- Knowledge cut-off is the report's publication; describe later developments only as the report states them.
- No values are pre-extracted for you. Every number, date, unit and condition you present must be traceable to a file and page. Where the materials word or quantify something differently, present it faithfully; do not silently harmonise.

## 2. Talk
- 12–15 minutes, **14–18 slides**, 16:9.
- Structure is yours, but the audience must first understand what happened, then why, and finish with actionable conclusions and an explicit evidence boundary.
- Every slide title is a claim that the slide's evidence supports.

## 3. Deliverables (in `output/`)
| File | Requirement |
|---|---|
| `presentation.pptx` | Opens in desktop Microsoft PowerPoint for Windows (16.0) with no repair prompt; still fully functional when only this file is copied to another offline machine. |
| `slides.pdf` | Static export with the same slides. |
| `script.md` | Verbatim per-slide script marking media and click events, with an estimated duration per slide. The same per-slide text goes into the PPTX speaker notes. |
| `evidence-index.csv` | One row per fact-bearing slide element: slide, element, claim, source file, PDF page (and printed page), figure/table/appendix id, transformation (quote, crop, conversion, recalculation). |
| `events.csv` | One row per media bookmark on the narration track: slide, bookmark name, bookmark time (s, two decimals), the exact sentence being spoken at that time, name of the triggered slide object. |

## 4. Native-object requirements
- **Narration and bookmarks**: on the slide that explains how the incident unfolded, embed an English narration track you produce (30–60 s, TTS or recorded, labelled on the slide as presenter-made) that starts automatically on slide entry. Add at least **3** PowerPoint media bookmarks to the track; each bookmark must, via a bookmark trigger, bring in one separate, editable native annotation over an original report figure, and the annotation must match what the narration is saying at that moment.
- **Native charts**: at least **2** native, editable PowerPoint charts with data you transcribe from the materials; "Edit Data" must open, and the embedded workbook must list source values, units, source pages and formulas for any conversion. Do not invent data points that are not in the materials.
- **Original figures**: use at least **3** real figures from the materials (main report or attachments), cropped cleanly with legends/labels kept, explained with native editable annotations; full-page screenshots do not count as explanation.
- **Causal diagram**: one causal diagram drawn with native, editable shapes, containing both technical and management/regulatory factors and their links.

## 5. Quality bar
- English body text ≥ 20 pt; captions and source lines ≥ 12 pt; ≤ 6 bullets per slide; no overlap or occlusion in any animation state.
- Explain necessary terms for this audience; use one consistent visual code to distinguish facts confirmed by the materials, the investigators' analytical findings, and your own inferences.
- State that the deck was produced with AI; credit source materials separately; do not imply review or endorsement by the investigating agency or the company.
- Core numbers and conclusions stay consistent across slides, notes, charts and their workbooks, script, narration and PDF.

## 6. Evaluation
Evaluation runs offline; you may use any local PDF/text/image/audio tools and Python. The target playback environment is desktop PowerPoint 16.0 for Windows; having a capability installed is not the same as a working file, so verify the delivered files as far as you can. Reviewers apply a **non-public checklist**, judging each item pass/fail; partial fulfilment fails. A PPTX that needs repair to open fails every native-object and delivery check. Time limit: 3600 s.
