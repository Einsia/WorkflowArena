# Multi-defendant criminal case adjudication (dense-md-08)

Work in `/workspace`. The evidence, law library and answer template are in `inputs/`. Write `output/judgment.json` and `work/reasoning.md`. The `output/` directory points to the collected `submission/` directory; both paths refer to the same judgment file.

## Task

Establish the facts and render a judgment using the witness testimony, victim statements, defendants' statements and defences, documentary evidence, expert opinions and other evidence in `inputs/facts.md`. These are evidence excerpts from anonymized judgments, not complete case files. The court's overall factual synthesis, reasoning and operative judgment for this case are not provided. Statements may contradict one another or contain assertions that were not accepted; assess them in the context of the whole case.

Submit conclusions only for these 8 defendants: 武某B、徐某A、武某C、常某某、任某A、刘某2、史某某、任某C. Other participants remain in the evidence as background. They do not require judgments in your answer, which does not mean they were innocent or their conduct can be ignored. See `inputs/defendants.json` for the exact answer scope.

Names retain the source's anonymized spelling, including 某, letters and numeric suffixes. The same exact spelling identifies the same person; do not merge similar names without evidence. Bracketed codes such as `[被告A]` are also person identifiers. Amounts, dates and quantities retain the source wording. Digits immediately next to names may be ambiguous; use context and do not change figures arbitrarily.

Apply the criminal-law framework in effect by the end of 2019. For conduct spanning amendments, use the dates in the evidence and the rule applying the earlier law unless the later law is more lenient. The closed library `inputs/law/` contains historical Criminal Law texts, amendments, relevant judicial interpretations and sentencing guidelines. Effective dates appear in `inputs/law/INDEX.md`. Do not directly use later rules to increase punishment. Do not access the network or use case materials or legal sources outside this package.

Determine the charges, Specific Provisions articles, position in each joint crime, statutory sentencing circumstances, individual and combined sentences, and probation. Explain material uncertainties, including incomplete procedural facts, in `work/reasoning.md`, while submitting your best judgment in the required format. Sentence length is a discretionary prediction; closeness to the source court's sentence is a separate metric, not a uniquely correct factual conclusion.

## Deliverables

Write `output/judgment.json`, optionally starting from `inputs/judgment.template.json`:

```json
{
  "defendants": {
    "[被告A]": {
      "charges": ["交通肇事罪"],
      "articles": [133],
      "roles": {"交通肇事罪": "不区分"},
      "leader": false,
      "circumstances": ["<法定情节>"],
      "charge_terms": {},
      "final_term": {"type": "有期徒刑", "months": 12},
      "probation": false
    }
  }
}
```

This example illustrates the format only; its charge, defendant and circumstance placeholder are unrelated to this case. The placeholder `<法定情节>` is not an allowed answer value.

- `charges`: every charge of which the defendant is convicted. Use the standard Chinese charge names determined by the Supreme People's Court and Supreme People's Procuratorate, as provided in `inputs/law/zuiming-*.md`. For alternative charge names, select the acts actually committed, such as `非法买卖枪支罪` or `非法运输、储存爆炸物罪`. Do not include unestablished charges.
- `articles`: integer article numbers of the Criminal Law's **Specific Provisions**, without paragraph or item numbers. Exclude General Provisions articles, such as 25, 26, 27, 65, 67 and 69.
- `roles`: one value for each charge: `主犯` (principal), `从犯` (accessory), `胁从犯` (coerced accomplice), or `不区分` (acting alone or no distinction of roles for that charge). If the same charge covers several incidents, use `主犯` if the defendant played a principal role in any one incident; use `从犯` if all their participation was secondary or auxiliary. Explain incident-level differences in `work/reasoning.md`. Only roles distinguished by the source reference and assessable from the public materials are scored.
- `leader`: a boolean indicating a statutory ringleader of a criminal group or gathered-crowd crime. An ordinary group's convener or an ordinary principal offender is not automatically a statutory ringleader.
- `circumstances`: statutory sentencing circumstances, using only `未成年` (under 18 at the time of the offence), `未遂` (attempt), `自首` (voluntary surrender), `坦白` (confession under Article 67(3)), `立功` (meritorious service), and `累犯` (recidivism). Do not separately list confession for an offence already qualifying as voluntary surrender; both may be listed if established for different offences. Do not include discretionary considerations such as restitution, forgiveness, prior misconduct or admitting guilt in court.
- `charge_terms`: for two or more charges, give the sentence pronounced for each charge, using the same term format as `final_term`. It may be empty for a single charge.
- `final_term`: the principal punishment decided to be executed. `type` must be `死刑` (death), `死刑缓期二年执行` (death with two-year reprieve), `无期徒刑` (life), `有期徒刑` (fixed-term imprisonment), `拘役` (criminal detention), `管制` (public surveillance), or `免予刑事处罚` (exemption from punishment). `months` is an integer, or `null` for death, reprieved death and life. Convert years to months: three years and six months is 42 months. If a new crime during probation requires revocation and combination with the earlier sentence, give the combined term decided to be executed.
- `probation`: a boolean indicating whether probation is pronounced.

Use the exact Chinese names and categorical values, including the final `罪` in charges; English translations are not accepted as substitutes. Keys in `roles` and `charge_terms` must match the strings in `charges`. Defendant keys must match `inputs/defendants.json`. JSON field names are the English keys shown above; numbers are JSON numbers and booleans are `true` or `false`.

Determine the answers yourself rather than copying an external judgment. Supplementary punishments, such as fines or deprivation of political rights, need not be supplied. The evidence and legal corpus remain in Chinese to preserve their meaning.

## Grading

The deterministic grader uses source labels reviewed by the authors. Fields that cannot be determined because of missing or conflicting source material are excluded in advance rather than treated as negative examples. There is no model judge.

- Per defendant: charge, article and statutory-circumstance sets use set F1. The final sentence uses logarithmic-distance bands relative to the reference, with full credit at roughly 20% distance and less credit for larger differences; death and life penalties require the relevant type match. Probation is scored where the reference is determinable.
- Whole case: roles under each charge and ringleader status are scored separately. Internal consistency checks concern Article 69's relation between individual and combined sentences, Articles 72 and 74's probation conditions, and principal-versus-accessory sentence ordering.
- The primary Harbor reward is binary full success: all defendants' charge and article sets and all graded roles must be exact; the graded ringleader set must be exact; statutory-circumstance micro-F1 must be at least 0.8; at least 80% of defendants with graded sentences must have sentence-band score at least 0.8; graded probation accuracy must be at least 0.8; all applicable Article 69 and probation consistency checks must pass; and principal-versus-accessory sentence ordering must hold in at least 90% of relevant pairs. A sentence-band score of at least 0.8 ordinarily corresponds to logarithmic distance at most 0.4, approximately a factor of 1.5. Missing-source masks affect the applicable denominators. Partial branch and whole-case scores are also reported.

Only `output/judgment.json` is machine-scored. `work/reasoning.md` records your evidence, reasoning and unresolved gaps for review. Delegation telemetry is collected by the execution harness, separately from the legal score.
