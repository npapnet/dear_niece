---
name: run-profile-analysis
description: >
  Run the percentile analysis for a named profile and produce profiles/{name}/analysis.xlsx.
  Requires output/distributions_wide.xlsx (from pivot-distributions) and
  data/baseis-master.csv (from load-baseis) to exist first.
inputs:
  - name: profile
    description: Profile name — must match a directory under profiles/ containing schools.yml
    required: true
outputs:
  - name: analysis
    description: profiles/{name}/analysis.xlsx — six sheets covering percentile scores, shifts, metric, and baseis trend
---

## What this skill does

Calls `analyse.py --profile <name>`. Loads baseis data from `data/baseis-master.csv`,
filters to the school codes listed in `profiles/{name}/schools.yml` and to the
general-admission track (`position_type` containing `ΓΕΝIK`), then runs the full
percentile analysis. All six output sheets are written to `profiles/{name}/analysis.xlsx`.

| Sheet | Contents |
|---|---|
| `percentile_scores` | Score bin at 85th/90th/95th percentile per subject per year |
| `percentile_shifts` | Year-over-year change in those percentile bins |
| `high_end_metric` | Weighted sum of high-end bins |
| `bin_diffs` | Raw year-over-year percentage change per bin |
| `baseis` | Admission thresholds (columns = institution, rows = year) |
| `baseis_shifts` | Year-over-year change in admission thresholds |

## Command

```bash
uv run python analyse.py --profile <name>
```

## Notes

- `profiles/{name}/schools.yml` must exist and contain a `schools` list of 4-digit ministry codes.
- The output file `profiles/{name}/analysis.xlsx` is gitignored.
- The shared sheets (`percentile_scores`, `percentile_shifts`, `high_end_metric`, `bin_diffs`)
  are identical across profiles — only the `baseis` and `baseis_shifts` sheets differ.
