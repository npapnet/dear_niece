# Architecture

> This document is the **main entry point** for both Claude Code (`CLAUDE.md`) and Antigravity (`.agents/config.yml`). Start here.

## Scope

Each year, Greek university admission thresholds (βάσεις) shift up or down. The shift correlates with how the national student grade distributions changed that year. This repository estimates the **expected delta in βάσεις** for a target year by:

1. Measuring the year-over-year change in the national student mark distributions (per subject: Biology, Physics, Chemistry, Greek Language).
2. Correlating those distribution shifts with the observed βάσεις deltas from prior years where both are known.
3. Applying that relationship to the most recent distribution data (which is always available one year ahead of the published βάσεις) to predict the upcoming threshold changes.

The repository is designed to serve **multiple people targeting different schools**. The shared national data (distributions, raw βάσεις) is processed once; each person maintains a profile declaring their schools of interest, and analysis is scoped to that profile.

## Goal

Maintain a running database of Greek university admission thresholds (βάσεις) that can be updated each year by downloading one file, with no structural changes to the code.


## Data sources

| File | Origin | Cadence |
|---|---|---|
| `data/baseis-raw/gel-{YEAR}.xlsx` | Published annually by the ministry | Download once per year after results |
| `data/Bro-Maria.xlsx` (sheet `data-StudentsDistribution`) | Manually collected grade distributions | Update once per year |


## Directory layout

```
data/
  baseis-raw/              # raw ministry downloads, one file per year
    gel-2023.xlsx
    gel-2024.xlsx
    gel-2025.xlsx
    ...
  distributions.xlsx       # national student mark distributions (rename from Bro-Maria.xlsx)
  _pipeline_cache/         # gitignored — generated intermediates, never edit by hand
    baseis-master.csv      # combined long-format master
    distributions_wide.xlsx  # grade distribution pivot

output/                    # gitignored — final deliverables
  distributions_plot.png   # complementary CDF plots per subject

weights/                   # gitignored — content-addressable weight store ({hash}.npy + {hash}.yml sidecar)

profiles/
  maria/
    schools.yml            # committed input — prediction_year, 4-digit ministry codes, optional metric_weights override
    analysis-2025-{hash}.xlsx  # gitignored output — analysis workbook ({hash} = weight-set id)
    report-2025-{hash}.md      # gitignored output — markdown summary ({hash} = weight-set id)
  _golden/                 # committed synthetic test profile (not a real person)
    schools.yml            # fixed synthetic parameters
    README.md              # documents the exact synthetic inputs + expected predictions
    expected-report-2025.md  # frozen golden report — diffed by tests/test_golden_profile.py

metric_weights.yml         # committed — global default high-end metric weights (sparse YAML, per-class)

design/                    # committed — refactor specs, implementation notes, and design docs
  metrics_refactor/        #   configurable metric-weights refactor (Phases 0–2, done)
    refactor_metrics.md
  future_work/             #   deferred / not-yet-started designs
    refactor_package.md    #     Phase 3: src/ package + dn CLI

national_load_baseis.py             # loader module — the only place that knows the raw baseis format
national_pivot_distributions.py     # reads distributions.xlsx → data/_pipeline_cache/distributions_wide.xlsx
analyse.py                 # reads _pipeline_cache → profiles/{name}/analysis-{YEAR}-{hash}.xlsx + report-{YEAR}-{hash}.md
                           #   (importable functions; compute core is run_analysis(), CLI under main())
metrics.py                 # weight logic: load_weights (config + per-profile override), dense
                           #   materialization, compute_metric (name-aligned dot product), weights_hash
national_plot_distributions.py      # reads _pipeline_cache/distributions_wide.xlsx → output/distributions_plot.png

tests/                     # pytest suite — synthetic data, no real-cache dependency
  conftest.py              # synthetic distributions_wide + baseis fixtures
  test_metrics_pipeline.py # metric / weights / regression unit + integration tests
  test_metrics.py          # metrics.py units: config load/override, materialization, compute_metric, hash
  test_golden_profile.py   # end-to-end golden-report backup
  _golden_helpers.py       # shared synthetic-run logic
  _regen_golden.py         # regenerate the golden report after an intended change
```


## Raw file format

Each `gel-{YEAR}.xlsx` has:

- **Row 1**: title cell (merged across all columns), e.g. `ΒΑΣΕΙΣ -- ΕΠΙΛΟΓΗ ΓΕΛ-ΗΜΕΡΗΣΙΑ -- ΠΑΝΕΛΛΑΔΙΚΕΣ 2025`
- **Rows 2–3**: two-row merged-cell header. Some columns span both rows (standalone headers); score columns are split into `ΜΟΡΙΑ` / `ΚΡΙΤΗΡΙΑ ΙΣΟΒΑΘΜΙΑΣ` sub-headers in row 3.
- **Row 4+**: one department × position-type combination per row.

The column count has changed over time (12 cols in 2023–2024, 14 in 2025 which adds `ΚΕΝΑ` and `ΙΣΟΒΑΘ.`). The loader handles this automatically.

Standardised columns after loading:

| Column | Type | Description |
|---|---|---|
| `year` | int | Extracted from the file title |
| `school_code` | str | 4-digit ministry code (stable across years) |
| `institution` | str | University abbreviation |
| `department` | str | Full department name (including city) |
| `position_type` | str | Admission track (e.g. `ΓΕΛ ΓΕΝΙΚΗ ΣΕΙΡΑ ΗΜ.`) |
| `field_1` … `field_4` | bool | One-hot: which scientific fields grant access to this department |
| `initial_slots` | float | Announced positions |
| `slots` | float | Positions after transfers |
| `admitted` | float | Number admitted |
| `vacancies` | float | Unfilled seats (2025+, NaN for earlier years) |
| `top_score` | float | Highest score admitted (μόρια) |
| `entry` | float | **Admission threshold** — lowest score admitted (μόρια) |

Tiebreak-criteria columns (`ΚΡΙΤΗΡΙΑ ΙΣΟΒΑΘΜΙΑΣ` for both first and last place, and the `ΙΣΟΒΑΘ.` count column added in 2025) are dropped on load — they are free-text strings with no analytical value.


## Running the pipeline

The scripts run in sequence; each feeds the next:

```
national_load_baseis.py          →  data/_pipeline_cache/baseis-master.csv
national_pivot_distributions.py  →  data/_pipeline_cache/distributions_wide.xlsx
analyse.py              →  profiles/{name}/analysis-{YEAR}-{hash}.xlsx + report-{YEAR}-{hash}.md
national_plot_distributions.py   →  output/distributions_plot.png
```

All outputs are gitignored and always regenerated from source.

## Testing

The repository has a pytest suite — run it with `uv run pytest` (pytest lives in
the `dev` dependency group). It is built on **synthetic data** and never depends
on the gitignored pipeline cache:

- `analyse.py` is structured as importable, side-effect-free functions — the
  compute core is `run_analysis(...)` — with all file IO and the CLI under
  `main()`. Tests call the functions directly with synthetic DataFrames.
- `tests/conftest.py` builds a small synthetic `distributions_wide` + `baseis`
  master whose metric, bin_diffs, and per-school regression are hand-computable,
  so the assertions check **correctness**, not merely "same as before".
- `tests/test_golden_profile.py` is an end-to-end backup: it runs the full
  `main()` path for the committed `profiles/_golden/` synthetic profile and diffs
  the produced report against the frozen
  `profiles/_golden/expected-report-2025.md` (the `_Generated:` date line is
  normalised). After an *intended* change to the output, regenerate the golden
  with `uv run python tests/_regen_golden.py`.

## Key conventions

- **`prediction_year` in `schools.yml` controls the analysis window.** `analyse.py` uses distribution data up to and including `prediction_year`, and βάσεις data up to `prediction_year - 1` (since the upcoming year's βάσεις are not yet published). Both output files are named after the year **and the weight-set hash**: `analysis-{prediction_year}-{hash}.xlsx` and `report-{prediction_year}-{hash}.md`, so runs with different weights coexist without clobbering one another. The hash is printed at the end of the run (and stamped into the report header / `metric_weights` sheet); to find the latest, glob `report-{prediction_year}-*.md`. To target a different year, change only this field.
- **Metric weights are configurable and real-valued.** The high-end metric weights live in `metric_weights.yml` (repo-root global default) and may be overridden per-profile via an optional `metric_weights:` block in `schools.yml` (per-class replace; unnamed classes fall back to the global default). `metrics.py` is the single owner of the weight logic: it materializes the sparse YAML into a dense `float64` vector over the 48 `{class}_{bin:02d}` columns and computes the metric as a name-aligned dot product (so column order in the distribution frame can't silently misalign it). Every weight set actually used is persisted to the content-addressable `weights/{hash}.npy` (canonical dense array) with a sparse `.yml` sidecar, and that hash suffixes the output filenames — so weight sets are reproducible and never clobber one another. This is also the drop-zone the future weight-optimiser writes into. See [`design/metrics_refactor/refactor_metrics.md`](design/metrics_refactor/refactor_metrics.md) for the design.
- **`design/` holds the design specs.** Refactor specifications, implementation notes, and design docs live under `design/`, one subfolder per effort (e.g. `design/metrics_refactor/`). Deferred or not-yet-started designs go under `design/future_work/`. When starting a refactor, write its spec there first and link it from the relevant Key-convention bullet; when it ships, the spec stays as the record of *why*.
- **`national_load_baseis.py` is the only file that knows the raw xlsx format.** All header-parsing logic lives in `_build_columns()`. If the ministry changes the layout again, fix it there only.
- **`school_code` is the stable cross-year join key.** Department names and institution abbreviations drift across years; the 4-digit ministry code does not.
- **`field_1`–`field_4` are bool columns.** The raw `ΕΠΙΣΤΗΜΟΝΙΚΑ ΠΕΔΙΑ` value (e.g. `'2/3'`) is one-hot encoded on load to avoid Excel date-coercion. Field 3 = natural sciences (biology).
- **Greek text throughout.** All `department`, `institution`, and `position_type` values are in Greek. Note: the K in `ΓΕΝIKH` switched from a Latin K (2023–2024) to a Greek Κ (2025+); if filtering by position_type, use `.str.contains('ΓΕΝΙ[KΚ]', na=False, regex=True)`.

## Update procedure (each year)

1. Download the new `gel-{YEAR}.xlsx` from the ministry website and place it in `data/baseis-raw/`.
2. Add the new year's 48 distribution rows to `data/distributions.xlsx` (sheet `data-StudentsDistribution`).
3. Run the full pipeline:
   ```bash
   uv run python national_load_baseis.py
   uv run python national_pivot_distributions.py
   uv run python analyse.py --profile maria
   uv run python national_plot_distributions.py
   ```

No code changes are needed for a routine yearly update. See the [`yearly-update`](.agents/workflows/yearly-update.md) workflow for the full checklist.


## Querying the master

```python
import pandas as pd

master = pd.read_csv('data/_pipeline_cache/baseis-master.csv', encoding='utf-8-sig')

# Filter to the general-admission track and biology-accessible departments
gel = master[
    master['position_type'].str.contains('ΓΕΝΙ[KΚ]', na=False, regex=True) &
    master['field_3']  # field 3 = natural sciences (biology)
]

# Wide format: departments as rows, years as columns, entry score as values
wide = gel.pivot_table(
    index=['school_code', 'institution', 'department'],
    columns='year',
    values='entry',
)
```


## Design decisions

### Long format as master
One row per observation. Wide format is derived on-demand via `pivot_table`. This keeps the master append-only and year-agnostic — adding a new year never changes the schema.

### `school_code` as stable join key
Department names and institution abbreviations drift slightly across years. The 4-digit ministry code is stable and the correct key for cross-year joins.

### `field` as one-hot booleans
The raw field column contains strings like `'2/3'` or `'1/2/4'` indicating that a department accepts students from multiple scientific fields. Storing these as-is in CSV risks automatic date parsing by spreadsheet software (e.g. Excel reads `'1/2'` as 1 February). One-hot encoding into `field_1`…`field_4` avoids this, is type-safe, and makes field-based filtering trivial.

### Tiebreak columns dropped
The `ΚΡΙΤΗΡΙΑ ΙΣΟΒΑΘΜΙΑΣ` columns contain free-text tiebreak criteria strings (e.g. `'18,2 19,4 19,7 1 16,1'`). They carry no analytical value for threshold prediction and are discarded on load.

### Loader owns the format knowledge
All header-parsing logic lives in `national_load_baseis.py`. If the ministry changes the layout again, only that file needs updating.

### CSV vs Parquet for the master file

At the current scale (~500 rows/year, growing ~500/year), CSV is the right choice:

- Human-readable and inspectable without tooling.
- Openable directly in Excel for spot-checking.
- No extra dependency (pyarrow/fastparquet).

The `field` date-coercion risk — the main argument for parquet's type safety — is fully resolved by one-hot encoding.

**When to reconsider parquet**: if the dataset grows beyond ~10 years and downstream scripts start showing noticeable load times, or if the master is shared with other tools that already use pyarrow (e.g. a pandas pipeline that reads many files). At that point, switching is a one-line change in the loader and the query snippet above.

### `baseis.xlsx` kept as a hand-curated subset
It holds only the schools relevant to the analysis and is not auto-generated, so it can carry extra annotations (notes, flags) without being overwritten by the loader.


## Agent compatibility

This repository is designed to work with both **Claude Code** and **Antigravity** clients.

| Client | Entry point | Config |
|---|---|---|
| Claude Code | `CLAUDE.md` | Points here for architecture |
| Antigravity | `.agents/config.yml` | Points here for architecture |

### Skills

Atomic, single-script operations. Each skill maps directly to one Python script.

| Skill | Script | Trigger |
|---|---|---|
| [`load-baseis`](.agents/skills/load-baseis.md) | `national_load_baseis.py` | New `gel-{YEAR}.xlsx` added to `data/baseis-raw/` |
| [`pivot-distributions`](.agents/skills/process-distributions.md) | `national_pivot_distributions.py` | New rows added to `distributions.xlsx` |
| [`run-profile-analysis`](.agents/skills/run-profile-analysis.md) | `analyse.py --profile <name>` | Either of the above ran |
| [`run-analysis`](.agents/skills/run-analysis.md) | `analyse.py` | Legacy — no profile; use `run-profile-analysis` instead |
| [`plot-distributions`](.agents/skills/plot-distributions.md) | `national_plot_distributions.py` | After `pivot-distributions` runs |

### Workflows

Multi-step sequences that chain skills together.

| Workflow | Description |
|---|---|
| [`yearly-update`](.agents/workflows/yearly-update.md) | Full pipeline for a new year: load → distributions → analysis |
