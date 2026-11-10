# WFA-CDN-009: The door plug briefing

Prepare a 12-minute English briefing for the **joint safety review board of an airline and an aircraft manufacturer**: senior operations, quality and safety managers who are not structures engineers. The briefing answers one question:

**On a narrow-body airliner delivered only weeks earlier, a cabin door plug separated in flight. What chain of events made that possible, which breaks in that chain would have prevented it, and what does the evidence *not* allow us to conclude?**

Use only the material in `input/`. Do not add facts, numbers or events from outside it. Do not run new analyses of flight data or structures beyond simple arithmetic on published values.

## 1. Material
- `input/final-report.pdf`: the investigating agency's final report on the event.
- `input/preliminary-report.pdf`: the same agency's preliminary report on the event.
- `CREDITS.md`: source category and licence.

No values are pre-extracted. Every number, time, date, count and finding you present must come from these files and be traceable to a file and page.

## 2. Briefing
- 8–10 slides, 16:9, including title and closing slides. No empty divider slides.
- About 12 minutes spoken (11–13 min acceptable) at a speaking rate of 130–150 words per minute, including any pauses declared in the script.
- The deck must establish what happened in flight, reconstruct the causal chain back to its origin, evaluate where the chain could have been broken, and end with a direct answer to the question, including its limits.
- Every slide title is a claim the slide supports.

## 3. Deliverables (in `output/`)
| File | Requirement |
|---|---|
| `presentation.pptx` | The deck. Must open in desktop Microsoft PowerPoint for Windows (16.0) with **no repair prompt**, and remain fully functional when copied alone to another folder on an offline machine. |
| `slides.pdf` | Static export of the same slides. |
| `script.md` | Verbatim script per slide with per-slide timing and marked click/trigger events. The same per-slide text goes into the PPTX speaker notes. |
| `evidence-index.csv` | One row per fact-bearing slide element: slide, element, claim, source file, printed page and PDF page, figure/table/section number, transformation (quote, crop, conversion, recalculation). |
| `playback-check.md` | What you actually verified, how, with which software and version, and what you could not verify. Unsupported claims earn nothing. |

## 4. Native objects and animation
- **Native charts:** at least **2** native, editable PowerPoint charts with data you transcribe from the material. "Edit Data" must open for each chart; the embedded workbook must list the source values, units and source pages. Do not invent intermediate data points.
- **Report figures:** at least **2** real figures from the reports, cropped legibly with legends kept, explained with native (editable) callouts. A full-page screenshot is not an explanation.
- **Causal chain:** one slide builds the causal chain from native, separately editable shapes and connectors, revealed step by step with **at least 5** on-click entrance animations.
- **Interactive counterfactuals:** one slide shows the barriers you judge relevant as native shapes; each barrier shape is a **PowerPoint trigger** (animation triggered on click of that shape, not a hyperlink or slide jump) that reveals a separate, editable explanation of whether and why that barrier would have stopped the event, according to the material. At least **3** triggered barriers.

## 5. Quality
- Body text ≥ 20 pt; captions and source lines ≥ 12 pt; ≤ 6 bullets per slide; nothing overlaps or is clipped in any animation state.
- Explain technical terms for this audience; visually distinguish established findings, the agency's analysis/judgement, and your own inference.
- State that the deck was produced with AI assistance; credit the source documents; do not imply endorsement by any agency or company named in the material.
- Key numbers and findings must agree across slides, notes, chart workbooks, script, PDF and evidence index.

## 6. Tools and evaluation
You may use any local PDF/text tools, Python, LibreOffice and python-pptx. The target playback environment is desktop Microsoft PowerPoint 16.0 for Windows; verify the delivered file as far as you can.

Reviewers grade against a **non-public scoring guide**: coverage and fidelity to the material, correctness of your reasoning, narrative, visual design, and native object/animation behaviour in real PowerPoint. Each check is pass/fail; partial satisfaction fails. A file that PowerPoint must repair fails all media and animation checks.
