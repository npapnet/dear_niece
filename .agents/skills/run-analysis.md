---
name: run-analysis
description: >
  Run the percentile analysis for a named profile and produce profiles/{name}/analysis.xlsx.
  Requires output/distributions_wide.xlsx (from pivot-distributions) to exist first.
inputs:
  - name: profile
    description: Profile name — must match a directory under profiles/ containing schools.yml
    required: true
  - name: distributions_wide
    description: Path to the wide-format distribution pivot
    required: false
    default: output/distributions_wide.xlsx
outputs:
  - name: analysis
    description: profiles/{name}/analysis.xlsx — seven sheets covering percentile scores, shifts, metric, baseis trend, and baseis detail
---

## What this skill does

Calls `analyse.py --profile <name>`, which produces seven sheets in `profiles/{name}/analysis.xlsx`:

| Sheet | Contents |
|---|---|
| `percentile_scores` | Score bin at 85th/90th/95th percentile per subject per year |
| `percentile_shifts` | Year-over-year change in those percentile bins |
| `high_end_metric` | Weighted sum of high-end bins |
| `bin_diffs` | Raw year-over-year percentage change per bin |
| `baseis` | Admission thresholds in wide format (rows=year, cols=school_code) |
| `baseis_shifts` | Year-over-year change in admission thresholds |
| `baseis_detail` | Long-format baseis: year, school_code, institution, department, entry |

## Command

```bash
uv run python analyse.py --profile <name>
```

## Notes

- The weighted metric uses bins ≥14 for `lang`, ≥16 for `phys`, ≥18 for `bio`/`chem`,
  with increasing weights toward higher bins.
- A positive percentile shift means that year's exams were harder (top students scored higher).
- 2025 metric shift is −14.85, similar to 2024's −16.90, suggesting another drop in βάσεις.
