---
name: run-profile-analysis
description: >
  Run the high-end metric + per-school regression analysis for a named profile and
  produce profiles/{name}/analysis-{year}-{hash}.xlsx + report-{year}-{hash}.md.
  Requires data/_pipeline_cache/distributions_wide.xlsx (from pivot-distributions) and
  data/_pipeline_cache/baseis-master.csv (from load-baseis) to exist first.
inputs:
  - name: profile
    description: Profile name — must match a directory under profiles/ containing schools.yml
    required: true
outputs:
  - name: analysis
    description: profiles/{name}/analysis-{year}-{hash}.xlsx — seven sheets (metric, weights, bin diffs, baseis, shifts, detail, predictions)
  - name: report
    description: profiles/{name}/report-{year}-{hash}.md — markdown summary of weights, diffs, baseis shifts, predictions
---

## What this skill does

Calls `analyse.py --profile <name>`. Loads `data/_pipeline_cache/baseis-master.csv`,
filters it to the school codes listed in `profiles/{name}/schools.yml` and to years
≤ `prediction_year − 1`, loads the grade distributions up to `prediction_year`, then:

1. Computes the weighted **high-end metric** per year and its year-over-year shift.
   Weights come from `metric_weights.yml` (optionally overridden per-profile via a
   `metric_weights:` block in `schools.yml`); `metrics.py` owns the weight logic.
2. Fits a per-school least-squares regression of βάσεις shift on metric shift and
   predicts the upcoming threshold from the most recent metric shift.
3. Persists the weight set to the content-addressable `weights/{hash}.{npy,yml}` store.

Both outputs are suffixed with the weight-set `{hash}` (printed at the end of the run),
so different weight sets coexist without clobbering. The workbook has seven sheets:

| Sheet | Contents |
|---|---|
| `high_end_metric` | Weighted metric value and year-over-year shift per year |
| `metric_weights` | The weight set used (dense table); hash stamped in cell A1 |
| `bin_diffs` | Raw year-over-year percentage-point shift per bin |
| `baseis` | Admission thresholds in wide format (rows=year, cols=school_code) |
| `baseis_shifts` | Year-over-year change in admission thresholds |
| `baseis_detail` | Long-format baseis: year, school_code, institution, department, entry |
| `predictions` | Per-school regression coefficients, predicted shift, predicted entry |

## Command

```bash
uv run python analyse.py --profile <name>
```

## Notes

- `profiles/{name}/schools.yml` must exist and contain a `prediction_year` and a
  `schools` list of 4-digit ministry codes.
- The output files `profiles/{name}/analysis-{year}-{hash}.xlsx` and
  `report-{year}-{hash}.md` are gitignored; to find the latest, glob
  `report-{year}-*.md`.
- The `high_end_metric`, `metric_weights`, and `bin_diffs` sheets are profile-independent
  for a given weight set — only the `baseis*` and `predictions` sheets differ per profile.
