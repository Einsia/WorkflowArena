#!/usr/bin/env python3
"""Fraction of the frozen 382-team organizer reference population beaten.
Both the submission and reference scores use the organizer's stratified half split.
"""
import csv, gzip, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify as V  # noqa: E402
from _common import emit, LOG  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sub = os.path.join(sys.argv[1], "submission.csv")
if not os.path.isfile(sub):
    emit(0.0, {"valid": 0})
    sys.exit(0)
truth = os.path.join(HERE, "reference", "data_test.csv.gz")
try:
    tot, per = V.score(sub, truth)
except SystemExit as e:  # verify raises SystemExit(msg) on malformed / incomplete submissions
    json.dump({"valid": False, "error": str(e)}, open(os.path.join(LOG, "details.json"), "w"))
    emit(0.0, {"valid": 0})
    sys.exit(0)
except Exception as e:  # unparsable CSV etc. -> invalid submission
    json.dump({"valid": False, "error": repr(e)[:500]}, open(os.path.join(LOG, "details.json"), "w"))
    emit(0.0, {"valid": 0})
    sys.exit(0)
half = set(int(x) for x in gzip.open(os.path.join(HERE, "reference", "organizer_half_split_ids.txt.gz"), "rt").read().split())
tot_h, per_h = V.score(sub, truth, half)
top = V.load_top400()
rank400 = 1 + sum(1 for r in top if r[2] < tot_h)
beaten = sum(1 for row in top if row[2] > tot_h)
if not top:
    raise RuntimeError("Empty reference population")
json.dump({"valid": True, "score_mean_log_mae": tot, "per_type_log_mae": per,
           "score_organizer_half_split": tot_h, "per_type_half_split": per_h,
           "rank_among_top400_half_split": rank400, "n_top400": len(top),
           "reference_population": "organizer_top400_stratified_half_split"},
          open(os.path.join(LOG, "details.json"), "w"), indent=1)
emit(beaten / len(top), {"valid": 1, "score_mean_log_mae": tot,
                        "score_organizer_half_split": tot_h,
                        "rank_among_top400_half_split": rank400, "n_top400": len(top)})
