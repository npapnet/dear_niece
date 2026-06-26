---
name: run-analysis
description: >
  Run the percentile analysis and produce analysis.xlsx.
  Requires output/distributions_wide.xlsx (from pivot-distributions) to exist first.
inputs:
  - name: profile
    description: Profile name (directory under profiles/). When given, baseis data comes from baseis-master.csv filtered to the profile's school codes and output goes to profiles/{name}/analysis.xlsx. Omit to use legacy data/baseis.xlsx and write to output/analysis.xlsx.
    required: false
    default: null
  - name: distributions_wide
    description: Path to the wide-format distribution pivot
    required: false
    default: output/distributions_wide.xlsx
outputs:
  - name: analysis
    description: profiles/{name}/analysis.xlsx (with --profile) or output/analysis.xlsx (legacy) — six sheets covering percentile scores, shifts, metric, and baseis trend
---

## What this skill does

Calls `analyse.py`, which produces six sheets in the analysis output:

| Sheet | Contents |
|---|---|
| `percentile_scores` | Score bin at 85th/90th/95th percentile per subject per year |
| `percentile_shifts` | Year-over-year change in those percentile bins |
| `high_end_metric` | Weighted sum of high-end bins (reproduces the manual metric from `wide_df-work.xlsx`) |
| `bin_diffs` | Raw year-over-year percentage change per bin |
| `baseis` | Admission thresholds from `data/baseis.xlsx` in wide format |
| `baseis_shifts` | Year-over-year change in admission thresholds |

## Command

```bash
# profile-based (recommended)
uv run python analyse.py --profile <name>

# legacy (no profile)
uv run python analyse.py
```

## Notes

- The weighted metric uses bins ≥14 for `lang`, ≥16 for `phys`, ≥18 for `bio`/`chem`,
  with increasing weights toward higher bins.
- A positive percentile shift means that year's exams were harder (top students scored higher).
- 2025 metric shift is −14.85, similar to 2024's −16.90, suggesting another drop in βάσεις.
