# WFA-CDN-011: When and Why Did the Curve Turn?

Build an English briefing, 12–15 minutes long, for the emergency-preparedness and epidemiology leads of a U.S. state health department (comfortable with basic epidemiology). The setting is late February 2020: the knowledge cutoff is the latest date in the materials, and nothing known only after that may be used. The briefing answers one question:

**As of late February 2020, how large was the COVID-19 epidemic in China, when did the case curve turn, how high were the risks of severe disease and death — how far does the evidence support each answer, and which conclusions can a state preparing for imported cases use directly in its planning?**

Use only the materials in `input/`; do not add facts, numbers or events from outside them. This is an evidence-presentation task: do not build your own transmission model and do not generate new data.

## 1. Materials
- `input/report.pdf`: the complete 40-page report of an international expert mission (28 February 2020).
- `input/sitrep-*.pdf`: three WHO daily situation reports from the same period.
- `CREDITS.md`: source categories and licences.

No values are pre-extracted for you. Every number, date, proportion and range you present must come from the original materials and be traceable to a file and page (values read off a figure must be marked as read from the figure). For every quantity you derive, give the source values and the formula. Do not silently correct or harmonise numbers in the source materials.

## 2. Deliverables (in `output/`)
| File | Requirement |
|---|---|
| `presentation.pptx` | 14–18 slides, 16:9. Must open in desktop Microsoft PowerPoint (16.0) for Windows with no repair prompt, and remain fully functional when copied alone to another folder. |
| `slides.pdf` | Static export of the same deck, same slide count. |
| `script.md` | Verbatim per-slide script, marking click events and the estimated duration of each slide; the same per-slide text goes into the PPTX speaker notes. |
| `evidence-index.csv` | One row per fact-bearing slide element: slide, element, claim, source file, page, figure/table number, transformation (quote, read from figure, conversion, recalculation, aggregation). |
| `playback-check.md` | What you actually verified, how, with which software and version, and what you could not verify. |

## 3. Native objects
- **Native charts**: at least 4 native, editable PowerPoint charts, including at least one line chart and one column chart, with data you transcribe from the materials. "Edit Data" must open for every chart; the embedded workbook must list the source values, units and source (file and page), and every derived value must be computed by a live formula, not pasted. Do not invent data points that are not in the materials.
- **Report figure**: at least one real figure from the materials used as evidence, cleanly cropped with its legend and axes kept, with native editable annotations; a full-page screenshot does not count.
- **Click build**: on the slide that explains the turn of the case curve, use at least 3 separately editable native on-click entrance animations to build the argument step by step. Whole-slide fades, GIFs and videos do not count.

## 4. Quality bar
- Every slide title is a claim the slide supports; core numbers and their qualifying conditions are visible on the slide, derivations may go in the notes.
- English body text ≥ 20 pt; captions and source lines ≥ 12 pt; ≤ 6 bullets per slide; no overlap or occlusion in any animation state.
- Explain necessary terms for this audience.
- The last slide answers the opening question directly.
- State that the deck was produced by AI; do not imply review or endorsement by WHO or any government body.
- The same quantity must be consistent across slides, charts and their workbooks, notes, script and PDF.

## 5. Tools and evaluation
You may use any local PDF/text tools, Python, LibreOffice, python-pptx and (if available) PowerPoint. The target environment is desktop Microsoft PowerPoint 16.0 for Windows; verify the delivered files as far as you can.

Evaluation follows non-public scoring criteria covering understanding of and fidelity to the materials, your own reasoning and calculations, narrative, visual design, and the file's behaviour in real PowerPoint (opening, chart data and animations). Each check is pass/fail; partial fulfilment fails.
