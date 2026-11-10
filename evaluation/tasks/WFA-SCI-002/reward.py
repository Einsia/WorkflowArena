#!/usr/bin/env python3
"""Harbor reward for comp-casp15-ema: fraction of the 26 CASP15 EMA participant groups beaten on mean signed Pearson(global score, TM)."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify as V  # noqa: E402
from _common import emit, LOG  # noqa: E402

sub = sys.argv[1]
if not os.path.isdir(sub):
    emit(0.0, {"valid": 0})
    sys.exit(0)
truth = V.load_truth()
agg, per = V.score_dir(sub, truth, False)
P = V.participants(truth, False)
vals = [v[0]['mean_pearson_TM'] for v in P.values()]
mine = agg['mean_pearson_TM']
json.dump({'aggregate': agg, 'per_target': per, 'field': {g: v[0]['mean_pearson_TM'] for g, v in P.items()}},
          open(os.path.join(LOG, "details.json"), "w"), indent=1)
if agg['n_targets_covered'] == 0:
    emit(0.0, {"valid": 0})
    sys.exit(0)
beaten = sum(1 for v in vals if v < mine - 1e-12)
better = sum(1 for v in vals if v > mine + 1e-12)
emit(beaten / len(vals), {"valid": 1, "mean_pearson_TM": mine, "mean_loss_TM": agg['mean_loss_TM'], "mean_pearson_QS": agg['mean_pearson_QS'],
                          "n_targets_covered": agg['n_targets_covered'], "rank": better + 1, "field_size": len(vals) + 1})
