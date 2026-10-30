# About the data

The raw PDM dataset is **not included** in this repository.

**Why:** the export contains enumerator names and phone numbers, respondent GPS coordinates, and free-text answers. It also belongs to the programme, not to the analyst.

**What is published instead:** aggregate tables only, in [`outputs/tables`](../outputs/tables).

**Variables used by the analysis** (matched by question-number prefix, so column wording changes will not break it):

| Section | Question | Used for |
|---|---|---|
| B | B4 District, B5 Village | Grouping |
| C | C1 Sex, C2 Respondent, C3 Age | Profile, age bands |
| D | D3 Fairness of selection | Perception by age |
| E | E4 Amount as announced, E5 Package, E6 Quality | Quality, package grouping |
| F | F1 Travel time, F2 Waiting time, F3 Transport cost, F4 Cash access | Access and timeliness |
| J | J1 Used input, J2 Planted, J4 Fertiliser | Utilisation |
| K | K1 Appropriate, K2 Training, K3 Sufficient | Effectiveness and suitability |

Place a local copy at `data/PDM_dataset.xlsx` if you want to rerun the analysis. It is excluded by `.gitignore`.

**Anonymisation:** place names are replaced at analysis time using a local `data/anonymise_map.json` (see `anonymise_map.example.json`). The real map is git-ignored so real names never enter the repository.
