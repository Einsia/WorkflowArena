> The working directory is `/workspace`. The task inputs are in `/workspace/inputs/` (the `inputs/` referred to below is this directory, e.g. `inputs/facts.md` is `/workspace/inputs/facts.md` and `inputs/law/INDEX.md` is `/workspace/inputs/law/INDEX.md`). "The materials in this task package" means the files under `/workspace/inputs/`. Write your deliverable to `/workspace/submission/`: `output/judgment.json` below means `/workspace/submission/judgment.json` (`/workspace/output` is a symlink to `/workspace/submission`, so either path works; grading reads only `/workspace/submission/judgment.json`).
>
> No network access at runtime. Installed software: Python 3.12 with numpy 2.1.3, scipy 1.14.1, pandas 2.2.3, openpyxl 3.1.5, xlrd 2.0.1, statsmodels 0.14.4, matplotlib 3.9.2, h5py 3.12.1, lxml 5.3.0, beautifulsoup4 4.12.3.
>
> This is an English translation of a task originally written in Chinese. The input materials and the answer vocabulary are Chinese: read the section "Language of the materials and of the answer" at the end of this document before you start.

# Multi-defendant criminal case adjudication (md-15)

## Task

You are a criminal trial judge. `inputs/facts.md` contains the facts **found by the court after trial** (经审理查明) in a criminal case with multiple defendants, including each defendant's basic information (date of birth, prior convictions, how they came into custody and their detention history) as well as the criminal facts found and a summary of the evidence. Personal names and place names have been anonymized, and the defendants are referred to by codes such as `[被告A]`; the court's reasoning, its conclusions on how each defendant's conduct is characterized, and the operative part of the judgment (判决主文) have all been removed.

Anonymization conventions (from the original data; please keep them in mind while reading):
- Defendants are always written as codes such as `[被告A]`, `[被告B]`; only a code without any suffix refers to a defendant.
- Other persons keep the original spelling (e.g. “张某1”, “李某”), or have been uniformly replaced by this task with placeholder names such as “陈某甲”, “老某乙”, “案外人丙”. The same placeholder name always refers to the same person throughout the text; unless the facts state it explicitly, placeholder names do not correspond to any defendant.
- `<LOC>` denotes a place name that has been removed; `□` denotes a character that was mistakenly masked by the original anonymization procedure and cannot be reliably restored (e.g. “红□”, “大□镇”); `×××` denotes a number withheld in the original text.
- A few anonymization residues that could not be resolved are kept as they are, for example a code immediately followed by a digit (`[被告C]3`), or a leftover letter X. Such a spelling may refer to that defendant or to another person with the same surname; judge from the context. Amounts, dates and quantities are the original figures and have not been changed.

Based solely on the materials in this task package, render a judgment on each of the following 9 defendants: [被告A], [被告B], [被告C], [被告D], [被告E], [被告F], [被告G], [被告H], [被告I] (the list is in `inputs/defendants.json`).

This is a first-instance case filed in 2019; apply the laws, judicial interpretations and sentencing norms that were in force at the time of the judgment. `inputs/law/` provides a closed legal corpus (the full text of the Criminal Law and all its amendments, the relevant judicial interpretations, and the versions of the Supreme People's Court's sentencing guidelines from different periods); the catalogue and the effective dates are in `inputs/law/INDEX.md`. While working on the task you must not go online and must not use any materials outside the task package.

## Deliverable

Write `output/judgment.json` (you may start filling it in from `inputs/judgment.template.json`), with the following structure:

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

(The example above only illustrates the format; its charge and circumstances have nothing to do with this case.)

Field descriptions:

- `charges`: all the charges (罪名) of which the defendant is convicted, using the standard charge names determined by the Supreme People's Court and the Supreme People's Procuratorate (e.g. “交通肇事罪”); for alternative charges (选择性罪名), state the charge according to the acts actually committed (e.g. “非法买卖枪支罪”, “非法运输、储存爆炸物罪”). Do not list charges that are not established.
- `articles`: the numbers of the articles of the **Specific Provisions** (分则) of the Criminal Law on which the conviction is based (integers; do not give paragraphs or items). Do not list articles of the General Provisions (总则) (such as Articles 25, 26, 27, 65, 67 and 69).
- `roles`: for each charge in `charges`, give the defendant's position in the joint crime for that charge; the value is one of `主犯` / `从犯` / `胁从犯` / `不区分` (`不区分`: the defendant acted alone, or the court does not distinguish principal and accessory offenders for that charge). Only charges for which the court explicitly determined the principal/accessory position are graded.
- `leader`: whether the defendant is a ringleader (首要分子) (one who organizes or leads a criminal group, or who plays an organizing, planning or commanding role in a crime committed by a gathered crowd); boolean.
- `circumstances`: the **statutory** sentencing circumstances that the court would find; the only allowed values are `未成年` (under eighteen years of age at the time of the crime), `未遂`, `自首`, `坦白` (Criminal Law Article 67, paragraph 3), `立功`, `累犯`. If voluntary surrender (自首) is found for an offence, do not additionally list confession (坦白) for the same offence; where they are established separately for different offences, both may be listed. Discretionary circumstances (returning the proceeds, the victim's forgiveness, prior record of misconduct, admitting guilt in court, etc.) are not to be filled in.
- `charge_terms`: when the defendant is convicted of two or more charges, the sentence pronounced for each charge must be given, in the same format as `final_term`; when only one charge is involved it may be left empty.
- `final_term`: the principal punishment decided to be executed. `type` is one of `死刑` / `死刑缓期二年执行` / `无期徒刑` / `有期徒刑` / `拘役` / `管制` / `免予刑事处罚`; `months` is an integer number of months (`null` for `死刑`, `死刑缓期二年执行` and `无期徒刑`). If a defendant committed a new crime during a probation period and the probation has to be revoked and the punishment combined with that for the earlier crime, give the term decided to be executed after the combination.
- `probation`: whether probation (缓刑) is pronounced; boolean.

You decide the charges, articles, circumstances and terms yourself; do not take them from any external judgment. Supplementary punishments (fines, deprivation of political rights, etc.) do not need to be filled in.

## Acceptance

Grading is automatic, by a program (no human or model review):

- Per defendant: the set of charges, the set of articles and the set of statutory circumstances are each scored by set F1; the term decided to be executed is scored in bands according to its logarithmic distance from the reference term (full marks within about 20%, lower scores for larger deviations; death penalty and life imprisonment must match in type); probation is scored on agreement wherever the reference answer can determine it.
- Whole case: the principal / accessory determinations under each charge and the ringleader determinations are scored separately; in addition, the submission is checked for internal consistency with Criminal Law Article 69 (the relation between the term decided to be executed and the terms pronounced for the individual charges), Articles 72 and 74 (conditions for probation), and the relative severity of the principal and accessory offenders' terms.
- Full success requires: the charges and articles of all defendants are exactly right; all principal/accessory and ringleader determinations are right; the overall F1 of statutory circumstances is at least 0.8; for at least 80% of the defendants the term is within a logarithmic distance of 0.4 (roughly within a factor of 1.5) of the reference term; probation accuracy is at least 0.8; the Article 69 and Articles 72/74 consistency checks pass for every defendant to which they apply; and the ordering check (a principal offenders decided term is not below an accessorys under the same charge) holds for at least 90% of the relevant pairs.

## Language of the materials and of the answer (added in this English edition)

This task was originally written in Chinese; the statement above is a full English translation. The materials themselves are deliberately **not** translated:

- `inputs/facts.md` is in Chinese: the fact-finding part of a judgment of a court of the People's Republic of China in a criminal case.
- `inputs/law/` contains the Chinese texts of the Criminal Law of the People's Republic of China (point-in-time versions and all amendments), judicial interpretations and other normative documents, and the Supreme People's Court's sentencing guidelines; its catalogue `inputs/law/INDEX.md` is also in Chinese.
- `inputs/defendants.json` and `inputs/judgment.template.json` use the Chinese defendant codes (`[被告A]` = "Defendant A", etc.).

The JSON keys of `judgment.json` are the English keys shown above (`defendants`, `charges`, `articles`, `roles`, `leader`, `circumstances`, `charge_terms`, `final_term`, `type`, `months`, `probation`). Every value that is a name or a category must be written with the original **Chinese** string; English renderings are not recognized by the grader and are scored as wrong:

- the keys under `defendants`: the defendant codes exactly as listed in `inputs/defendants.json` (e.g. `[被告A]`);
- `charges`, and the keys of `roles` and `charge_terms`: Chinese charge names (罪名), e.g. `交通肇事罪`. Use the standard charge names determined by the Supreme People's Court and the Supreme People's Procuratorate as they appear in the charge-name provisions included in the corpus (`inputs/law/zuiming-*.md`, listed in `inputs/law/INDEX.md`), written exactly as there, including the final `罪`. The keys of `roles` and `charge_terms` must be the same strings as in `charges`;
- `roles` values: one of `主犯`, `从犯`, `胁从犯`, `不区分`;
- `circumstances`: only the six values `未成年`, `未遂`, `自首`, `坦白`, `立功`, `累犯`;
- `type` in `final_term` and in `charge_terms`: one of `死刑`, `死刑缓期二年执行`, `无期徒刑`, `有期徒刑`, `拘役`, `管制`, `免予刑事处罚`.

Numbers are plain JSON numbers: `articles` are integers in Arabic numerals (Article 第一百三十三条 is `133`); `months` is an integer number of months. The Chinese sources write terms in years (年) and months (个月 / 月) with Chinese numerals; convert them to months (1 year = 12 months, e.g. 三年六个月 = 42 months). `leader` and `probation` are JSON `true` / `false`.

Glossary of the Chinese answer values and key terms (for understanding only; always submit the Chinese value):

| Chinese | English meaning | Used in |
|---|---|---|
| 主犯 | principal offender | `roles` |
| 从犯 | accessory (secondary offender) | `roles` |
| 胁从犯 | coerced accomplice | `roles` |
| 不区分 | not distinguished (acted alone, or the court does not distinguish principal and accessory offenders for this charge) | `roles` |
| 首要分子 | ringleader | `leader` (boolean) |
| 未成年 | minor (under 18 at the time of the crime) | `circumstances` |
| 未遂 | attempted crime | `circumstances` |
| 自首 | voluntary surrender | `circumstances` |
| 坦白 | confession (Criminal Law Art. 67, para. 3) | `circumstances` |
| 立功 | meritorious service | `circumstances` |
| 累犯 | recidivist | `circumstances` |
| 死刑 | death penalty | `type` |
| 死刑缓期二年执行 | death penalty with a two-year reprieve | `type` |
| 无期徒刑 | life imprisonment | `type` |
| 有期徒刑 | fixed-term imprisonment | `type` |
| 拘役 | criminal detention | `type` |
| 管制 | public surveillance (non-custodial restriction) | `type` |
| 免予刑事处罚 | exemption from criminal punishment | `type` |
| `<法定情节>` | placeholder in the format example: a statutory sentencing circumstance | `circumstances` |
| 罪名 | charge (name of the offence) | `charges` |
| 宣告刑 | sentence pronounced for an individual charge | `charge_terms` |
| 决定执行的刑罚 | sentence decided to be executed (after combining punishments for several crimes) | `final_term` |
| 缓刑 | probation (suspended execution of the sentence) | `probation` |
| 分则 / 总则 | Specific Provisions / General Provisions of the Criminal Law | `articles` |
| 被告人 / `[被告A]` | defendant / anonymized code of Defendant A | keys of `defendants` |
| 案外人 | person who is not a party to this case (placeholder name) | — |
