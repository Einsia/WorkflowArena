# WFA-CDN-012: What the Outlook's Cases Tell a Resource Planner

Prepare a 12-minute English briefing for the **commissioners and senior staff of a state public utility commission** who are opening an integrated resource planning proceeding. They are economists, lawyers and engineers, not energy modellers. The briefing answers one question:

**Across the outlook's modelled cases, how far apart are the 2050 outcomes that matter to an electricity planner — how much electricity is used, what generates it, and what customers pay — which single assumption opens each gap, and what can a planner responsibly take from that spread?**

Use only the material in `input/`. Do not add facts, figures or events from outside it. Apart from arithmetic on published values (differences, ratios, growth rates, unit and price-basis conversions), do not produce new projections.

## 1. Material
- `input/outlook-report.pdf`: the long-term energy outlook report of a U.S. federal statistical agency.
- `input/case-descriptions.pdf`: the same agency's description of the modelled cases.
- `input/figure-data.xlsx`: the data behind the report's figures, as published.
- `input/tables/<case>_table<N>.xlsx`: the agency's published projection tables for each case, as released (tables 1, 2, 3, 8 and 20).
- `CREDITS.md`: source category and licence.

No values are pre-extracted for you. Every number, date and conclusion you present must come from these files and be traceable to a file and page, or a file, sheet and cell.

## 2. Briefing
- 9–11 slides, 16:9, including a title slide and a closing slide; no empty divider slides.
- About 12 minutes spoken (11–13 minutes acceptable).
- Cover electricity demand, the generation mix, and electricity and natural-gas prices across the cases; place electricity use in the context of total U.S. energy consumption; and end by answering the question directly, including what the spread does **not** tell a planner.
- Every slide title is a claim the slide supports.

## 3. Deliverables (in `output/`)
| File | Requirement |
|---|---|
| `presentation.pptx` | The deck. Must open in desktop Microsoft PowerPoint (16.0) for Windows **without any repair prompt** and remain fully functional when copied alone to another folder on an offline machine. |
| `slides.pdf` | Static export of the same slides. |
| `script.md` | Verbatim per-slide script with per-slide timings. The same per-slide text goes in the PPTX speaker notes. |
| `scenario-data.xlsx` | Every number on the slides that is not printed verbatim in the material: its source values, units, price basis, source file/sheet/cell or page, and a live formula. Pasted results do not count. |
| `evidence-index.csv` | One row per fact-bearing slide element: slide, element, claim, source file, page or sheet/cell, transformation (quote, crop, conversion, recalculation). |
| `playback-check.md` | What you actually verified, how, with which software and version, and what you could not verify. Claims without evidence earn nothing. |

## 4. Native objects
- **Native table**: one slide carries a native, editable PowerPoint table (not a picture, not an embedded worksheet) comparing **all eleven cases** on at least five 2050 indicators that together cover demand, supply mix and prices, with the 2025 value shown for reference.
- **Native charts**: at least **3** native, editable PowerPoint charts whose data you transcribe from the material; "Edit Data" must open for each. One of them shows the average electricity price over 2025–2050 for at least four cases. The embedded workbook of each chart lists source values, units, price basis and source location. Do not invent intermediate data points.
- **Table–chart agreement**: any value that appears both in the native table and in a chart must be identical as displayed (same number, unit, basis and rounding), and must agree with the source tables.
- **Report figure**: use at least **1** figure reproduced from the report, cropped cleanly with its legend kept, and explained with native (editable) callouts; a full-page screenshot is not an explanation.

## 5. Quality
- Body text ≥ 20 pt; captions, source lines and table-cell text ≥ 12 pt; ≤ 6 bullets per slide; nothing overlaps or is clipped.
- Every quantity carries its unit; every monetary value carries its price basis. Quantities compared on one slide are on a common, stated basis.
- Explain technical terms for this audience. Distinguish visually and consistently between what the agency's model projects, what the agency states, and your own inference.
- State that the briefing was prepared with AI assistance; credit the source documents; do not imply review or endorsement by the agency or any organisation named in the material.
- Key numbers and conclusions must agree across slides, notes, the native table, chart workbooks, `scenario-data.xlsx`, the script, the PDF and the evidence index.

## 6. Tools and evaluation
You may use any local PDF/text tools, Python, LibreOffice and python-pptx. The target playback environment is desktop Microsoft PowerPoint 16.0 for Windows; verify the files you actually deliver wherever you can.

Reviewers score against a **non-public checklist**: coverage of and fidelity to the material, the correctness of your own reasoning and arithmetic, narrative, visual design, and the behaviour of native objects in real PowerPoint. Each check is pass/fail; partial satisfaction is a fail. A file that PowerPoint must repair fails all native-object and delivery checks.
