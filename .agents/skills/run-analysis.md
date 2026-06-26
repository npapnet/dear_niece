---
name: run-analysis
description: >
  Run the percentile analysis and produce the step2_analysis.xlsx report.
  Requires output/wide_df.xlsx (from process-distributions) to exist first.
inputs:
  - name: wide_df
    description: Path to the wide-format distribution pivot
    required: false
    default: output/wide_df.xlsx
  - name: baseis
    description: Path to the hand-curated baseis subset
    required: false
    default: data/baseis.xlsx
outputs:
  - name: analysis
    description: output/step2_analysis.xlsx — six sheets covering percentile scores, shifts, metric, and baseis trend
---

## What this skill does

Calls `process-step2.py`, which produces six sheets in `output/step2_analysis.xlsx`:

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
uv run python process-step2.py
```

## Notes

- The weighted metric uses bins ≥14 for `lang`, ≥16 for `phys`, ≥18 for `bio`/`chem`,
  with increasing weights toward higher bins.
- A positive percentile shift means that year's exams were harder (top students scored higher).
- 2025 metric shift is −14.85, similar to 2024's −16.90, suggesting another drop in βάσεις.
