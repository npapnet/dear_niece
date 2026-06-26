---
name: yearly-update
description: >
  Full pipeline for incorporating a new year of data. Covers both the
  admission threshold side (new gel-{YEAR}.xlsx) and the grade distribution
  side (updated distributions.xlsx). Run after each year's results are published.
inputs:
  - name: year
    description: The new year being added (e.g. 2026)
    required: true
---

## Prerequisites

Before running this workflow:

1. Download `gel-{year}.xlsx` from the ministry website and place it in `data/baseis-raw/`.
2. Add the new year's student grade distribution rows to `data/distributions.xlsx`
   (sheet `data-StudentsDistribution`) — 48 rows: 12 bins × 4 subjects.

## Steps

### 1. Rebuild master baseis

**Skill:** `load-baseis`

```bash
uv run python load_baseis.py
```

Verify: `data/baseis-master.csv` contains rows for `{year}`.

---

### 2. Rebuild grade distribution pivot

**Skill:** `pivot-distributions`

```bash
uv run python pivot_distributions.py
```

Verify: `output/distributions_wide.xlsx` index includes `{year}`.

---

### 3. Run percentile analysis

**Skill:** `run-profile-analysis`

```bash
uv run python analyse.py --profile <name>
```

Verify: `profiles/{name}/analysis.xlsx` — check `percentile_scores` and `high_end_metric`
to see where the new year falls relative to prior years.

---

### 4. Regenerate distribution plots

**Skill:** `plot-distributions`

```bash
uv run python plot_distributions.py
```

Verify: `output/distributions_plot.png` — confirm the new year's line is visible
and positioned as expected relative to prior years.

---

## Interpreting results

After a successful run, compare `high_end_metric` across years:

- **Metric increased vs prior year** → scores shifted up → expect higher βάσεις.
- **Metric decreased vs prior year** → scores shifted down → expect lower βάσεις.

Cross-check against `percentile_shifts`: if the 90th-percentile bin moved up by 1
for most subjects, the drop in βάσεις will likely be smaller than the metric alone suggests.
