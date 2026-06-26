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
  baseis-master.csv        # combined long-format master (auto-generated, do not edit)
  baseis.xlsx              # legacy hand-maintained subset; superseded by profiles

output/                    # all generated — gitignored
  distributions_wide.xlsx  # grade distribution pivot
  analysis.xlsx            # percentile analysis and baseis trend (legacy, no --profile)
  distributions_plot.png   # complementary CDF plots per subject

profiles/
  maria/
    schools.yml            # committed input — 4-digit ministry codes for schools of interest
    analysis.xlsx          # gitignored output — profile-scoped analysis

load_baseis.py             # loader module — the only place that knows the raw baseis format
pivot_distributions.py     # reads distributions.xlsx → output/distributions_wide.xlsx
analyse.py                 # reads distributions_wide.xlsx → profiles/{name}/analysis.xlsx
plot_distributions.py      # reads distributions_wide.xlsx → output/distributions_plot.png
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
load_baseis.py          →  data/baseis-master.csv
pivot_distributions.py  →  output/distributions_wide.xlsx
analyse.py              →  output/analysis.xlsx
plot_distributions.py   →  output/distributions_plot.png
```

All outputs are gitignored and always regenerated from source.

## Key conventions

- **`load_baseis.py` is the only file that knows the raw xlsx format.** All header-parsing logic lives in `_build_columns()`. If the ministry changes the layout again, fix it there only.
- **`school_code` is the stable cross-year join key.** Department names and institution abbreviations drift across years; the 4-digit ministry code does not.
- **`field_1`–`field_4` are bool columns.** The raw `ΕΠΙΣΤΗΜΟΝΙΚΑ ΠΕΔΙΑ` value (e.g. `'2/3'`) is one-hot encoded on load to avoid Excel date-coercion. Field 3 = natural sciences (biology).
- **Greek text throughout.** All `department`, `institution`, and `position_type` values are in Greek. Note: the K in `ΓΕΝIKH` switched from a Latin K (2023–2024) to a Greek Κ (2025+); if filtering by position_type, use `.str.contains('ΓΕΝΙ[KΚ]', na=False, regex=True)`.
- **`data/baseis.xlsx`** is hand-curated for the 7 schools of interest and is never overwritten by any script.

## Update procedure (each year)

1. Download the new `gel-{YEAR}.xlsx` from the ministry website and place it in `data/baseis-raw/`.
2. Add the new year's 48 distribution rows to `data/distributions.xlsx` (sheet `data-StudentsDistribution`).
3. Run the full pipeline:
   ```bash
   uv run python load_baseis.py
   uv run python pivot_distributions.py
   uv run python analyse.py --profile maria
   uv run python plot_distributions.py
   ```

No code changes are needed for a routine yearly update. See the [`yearly-update`](.agents/workflows/yearly-update.md) workflow for the full checklist.


## Querying the master

```python
import pandas as pd

master = pd.read_csv('data/baseis-master.csv', encoding='utf-8-sig')

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
All header-parsing logic lives in `load_baseis.py`. If the ministry changes the layout again, only that file needs updating.

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
| [`load-baseis`](.agents/skills/load-baseis.md) | `load_baseis.py` | New `gel-{YEAR}.xlsx` added to `data/baseis-raw/` |
| [`pivot-distributions`](.agents/skills/process-distributions.md) | `pivot_distributions.py` | New rows added to `distributions.xlsx` |
| [`run-profile-analysis`](.agents/skills/run-profile-analysis.md) | `analyse.py --profile <name>` | Either of the above ran |
| [`run-analysis`](.agents/skills/run-analysis.md) | `analyse.py` | Legacy — no profile; use `run-profile-analysis` instead |
| [`plot-distributions`](.agents/skills/plot-distributions.md) | `plot_distributions.py` | After `pivot-distributions` runs |

### Workflows

Multi-step sequences that chain skills together.

| Workflow | Description |
|---|---|
| [`yearly-update`](.agents/workflows/yearly-update.md) | Full pipeline for a new year: load → distributions → analysis |
