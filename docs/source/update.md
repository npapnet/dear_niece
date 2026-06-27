# Annual Update

Each year, two new data inputs become available. The pipeline is designed so that
adding them requires no code changes — only new data files and a re-run.

## When to update

| Event | Timing | Action |
|---|---|---|
| Exam results published | May–June | Add distribution rows to `distributions.xlsx` |
| Ministry baseis file published | August | Download `gel-YEAR.xlsx` to `data/baseis-raw/` |

Distributions arrive first. You can run the distribution part of the pipeline
immediately and generate a prediction before the baseis file exists for that year.
The baseis step is added later when the ministry publishes.

## Step-by-step

```{mermaid}
flowchart TD
    A["1. Download gel-YEAR.xlsx\nfrom ministry website"] --> B["Place in\ndata/baseis-raw/"]
    C["2. Add YEAR rows\nto data/distributions.xlsx\nsheet: data-StudentsDistribution"] 
    B --> D["uv run python national_load_baseis.py"]
    C --> E["uv run python national_pivot_distributions.py"]
    D --> F["data/_pipeline_cache/baseis-master.csv\nupdated"]
    E --> G["data/_pipeline_cache/distributions_wide.xlsx\nupdated"]
    F --> H["uv run python analyse.py\n--profile NAME"]
    G --> H
    H --> I["profiles/NAME/analysis-YEAR-HASH.xlsx\nwith updated predictions"]
    H --> R["profiles/NAME/report-YEAR-HASH.md\nmarkdown summary"]
    G --> J["uv run python national_plot_distributions.py"]
    J --> K["output/distributions_plot.png\nupdated"]
```

### 1. Add baseis data

Download the new `gel-{YEAR}.xlsx` from the Ministry of Education website and
place it in `data/baseis-raw/`. The file name must match the pattern `gel-*.xlsx`.

Then run:
```bash
uv run python national_load_baseis.py
```

This regenerates `data/_pipeline_cache/baseis-master.csv` with the new year appended.
The console shows a one-line progress indicator (year and position) while each file loads.

### 2. Add distribution data

Open `data/distributions.xlsx` and navigate to the `data-StudentsDistribution` sheet.
Add 48 rows (4 subjects × 12 bins) for the new year, following the existing format:

| Column | Example | Notes |
|---|---|---|
| `Ετος` | `2026` | The exam year |
| `Μαθημα ` | `Βιολογία` | Subject name in Greek — must match existing values exactly |
| `Επίδοση` | `14-15` | Bin range string, e.g. `0-5`, `10-11`, `19-20` |
| `Πλήθος` | `12450` | Number of students in this bin |
| `Ποσοστό` | `6.23` | Percentage of total students |

Then run:
```bash
uv run python national_pivot_distributions.py
```

This regenerates `data/_pipeline_cache/distributions_wide.xlsx`.

### 3. Rerun analysis and plot

```bash
uv run python analyse.py --profile maria
uv run python analyse.py --profile manou2026
uv run python national_plot_distributions.py
```

Repeat the `analyse.py` call for each profile.

## Verifying the update

The quickest sanity check is `report-{prediction_year}-{hash}.md` (the hash is printed
at the end of the run; glob `report-{prediction_year}-*.md` to find it) — open it in any
markdown viewer and confirm the prediction period label and the predicted entries look
reasonable.

For a deeper check, open `analysis-{prediction_year}-{hash}.xlsx` and verify:

1. **`high_end_metric` sheet** — the new year appears as a row with a valid `metric`
   and `metric_shift` value. If `metric_shift` is NaN, the year was added but there
   is no preceding year in the distribution data.

2. **`baseis` sheet** — the new year appears as a row if `gel-YEAR.xlsx` was loaded.
   If only distributions were added (baseis not yet published), this sheet will not
   have the new year — that is expected.

3. **`predictions` sheet** — `metric_shift (YEAR-PREV)` reflects the latest period
   and `predicted_entry_YEAR` shows the forecast. Compare against the training range
   visible in `high_end_metric` to assess extrapolation risk.

## No code changes needed

The loaders infer the year from file titles, so adding `gel-2027.xlsx` is enough —
no constant, no list, no config needs updating. The only structural change that would
require code edits is if the ministry changes the column layout of the baseis file
again; in that case, only `_build_columns()` in `national_load_baseis.py` needs updating.
