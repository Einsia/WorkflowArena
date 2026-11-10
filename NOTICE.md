# Source notices

WorkflowArena combines benchmark task material with upstream software, scientific data, public records and media. Source-specific terms apply to those components; inclusion in this collection does not replace an upstream license or grant rights that the upstream publisher has not granted.

Each task's `metadata.json` identifies its source. Additional attribution appears in `SOURCE.json`, `CREDITS`, `tests/provenance.json` and the task's supplied license files where applicable. The ledger under `provenance/licenses/` covers the OPS source records identified there, not the entire collection.

- MAUD contract data retains its CC BY 4.0 attribution.
- CHAMPS competition data is identified as CC-BY by its competition rules; those rules do not specify a version. Organizer code retains its own license.
- GMTKN55 distinguishes CC BY 4.0 data from MIT evaluation code.
- Scientific software and data retain their respective upstream licenses, including the separately identified GPL-3.0 code and CC BY-NC 4.0 data in WFA-SCI-016. A license for an associated paper does not automatically cover its code or data.
- Media inputs retain their individual credits and source notices. Government-authored reports and independently authored appendices are distinguished.
- Finance source records identify the underlying SEC filings and the scope of provenance verification. They do not assert a new license over issuer-authored reports.
- Official judicial documents are distinguished from upstream database packaging and annotations.

Certain publisher inputs are intentionally excluded from Git. The associated `environment/fetch/` scripts retrieve pinned upstream files, verify their hashes, apply the recorded preparation steps and reconstruct the frozen task inputs. The fully prepared local delivery retains these files for use and verification. Respect the source terms when redistributing a prepared copy.

Evaluator references are kept outside solver inputs. Their public availability in the benchmark repository does not make them permitted solver inputs during evaluation.
