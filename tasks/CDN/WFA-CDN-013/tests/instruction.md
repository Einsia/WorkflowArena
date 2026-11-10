# WFA-CDN-013: The morning the fire outran the warnings: what the record supports, and what it cannot

(The English version is authoritative. `instruction.zh.md` is a reviewing translation.)

Prepare an English briefing for a **county emergency-management and land-use planning board**. Board members know local government, but they are not fire scientists. The briefing answers one question:

**On the morning of the 2018 Camp Fire, how did evacuation warnings and orders relate in time to the arrival of fire and to the burnovers that trapped evacuees? For three alternatives, what does the investigative record support, what does it not support, and what evidence would be needed to decide? The three alternatives are (a) earlier evacuation orders, (b) more egress capacity, and (c) fuel treatment around the community.**

Use only the two reports in `input/`. Do not add facts, numbers or events from outside them. This is an evidence briefing. Do not run fire-spread, traffic or evacuation simulations, and do not generate new data.

## 1. Materials
- `input/main-report.pdf`: the case-study report on notification, evacuation, traffic, temporary refuge areas, rescues and fatalities (278 pages).
- `input/companion-report.pdf`: the companion case-study report on fire progression (421 pages, with large-format maps).

The two reports belong to the same case study and cite each other. Their supplementary appendices are not provided. The briefing must draw on **both** reports.

Printed page numbers differ from PDF page numbers. No values have been pre-extracted. Every number, time, count and category you present must come from the reports and be traceable to a page. Where the two reports differ, or where a report disagrees with itself, you must find this yourself and present it transparently. Do not silently correct or merge the sources.

## 2. Structure (exactly 12 slides, 16:9)
Use the sections below in this order. Choose how many slides each section gets. Every slide must carry evidence; no empty divider slides.
1. **Question and setting.** The communities, the scale of the event, and the question.
2. **How fast the fire moved.** Fire progression into the communities on the morning of November 8.
3. **Warnings and orders versus fire arrival.** By zone, including how requests turned into notifications that reached residents.
4. **Burnovers and refuge.** Where and when evacuees were overtaken by fire, and where people sheltered in place. Give burnover counts by the reports' severity category.
5. **Counterfactual boundaries.** Alternatives (a), (b) and (c). For each one, state what the record supports, what it does not support, and what evidence would be needed.
6. **Answer and recommendations for the board.** Tie every recommendation to the evidence shown.

## 3. Deliverables (in `output/`)
| File | Requirements |
|---|---|
| `presentation.pptx` | The deck. Must open in Windows desktop Microsoft PowerPoint (16.0) **without any repair prompt**. It must remain fully functional when copied alone to another folder on an offline machine. |
| `slides.pdf` | Static export of the same 12 slides. |
| `script.md` | A verbatim script for each slide, with click events marked and an estimated duration per slide. Total length is 12–15 minutes. The same per-slide text goes into the PPTX speaker notes. |
| `calculations.xlsx` | Every quantity you derived, meaning any number not printed verbatim in a report. For each one give the source values, units, report and page, and a live formula. Do not paste results only. |
| `evidence-index.csv` | One row per fact-bearing slide element. Columns: slide, element, claim, report, printed page, PDF page, table/figure number, and transformation (quote, crop, transcription, recalculation). |
| `playback-check.md` | What you actually verified, how, and with which software and version, plus what you could not verify. Claims without evidence earn nothing. |

## 4. Native objects and maps
- **Native charts.** At least **3** native, editable PowerPoint charts, with data you transcribed from the reports. Edit Data must open for each chart. The embedded workbook must list source values, units, report and page, and use formulas for every derived value. One chart must show, zone by zone, the interval between evacuation notification and fire arrival. Do not invent intermediate data points.
- **Report maps.** Use at least **3** map images cropped from the reports, including at least one from each report. Crop them legibly and keep their legend or scale where the original has one. Explain each map with native, editable annotations (shapes, callouts, labels) placed on the features they refer to. A full-page screenshot does not count as an explanation.
- **Click sequence.** On one map slide, reveal the burnovers of the morning of November 8 in chronological order. Use at least **4** separately editable native click animations. A whole-slide fade, a GIF or an embedded video does not count.
- **Boundary diagram.** Draw one editable diagram from native shapes that separates, for the counterfactual alternatives, observed record, inference, and unsupported claims.

## 5. Quality bar
- Every slide title is a claim that the slide supports. Key values, times, conditions and boundaries must be visible on the slide. Derivations may go in the notes.
- Body text ≥ 20 pt; captions and source lines ≥ 12 pt; ≤ 6 bullets per slide. When projected, axes, legends, map labels and values are legible. Nothing overlaps or is obscured in any animation state.
- State the time basis used for every interval and its sign convention. Explain each technical term for the audience.
- Use one consistent visual treatment that tells observation, inference and unsupported/counterfactual claims apart.
- State that the briefing was produced with AI and credit the sources separately. Do not imply review or endorsement by the authoring agencies.
- Core values, times and counts must agree across slides, notes, charts and their workbooks, `calculations.xlsx`, the script and the PDF.

## 6. Tools and assessment
You may use any local PDF or text tool, Python, chart tools and, if available, PowerPoint. The target environment is Windows desktop Microsoft PowerPoint 16.0. Having a capability installed does not mean the file works, so verify the delivered files as far as you can.

Reviewers assess the work against **non-public scoring criteria**. They audit every slide for coverage and fidelity to the reports, check the correctness of your own reasoning and calculations, judge the narrative and visual design, and check native-object behaviour in real PowerPoint. Each check is pass/fail, and partial fulfilment fails. If PowerPoint has to repair the file before opening it, every native-object and deliverable check fails.
