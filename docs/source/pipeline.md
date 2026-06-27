# Pipeline

## Script map

Four scripts form a linear pipeline. Each script reads from permanent source files
and writes to the `output/` directory or a profile folder — both gitignored and always
regenerated from source.

```{mermaid}
flowchart TD
    A["🗂 data/baseis-raw/gel-YEAR.xlsx\nMinistry download, one file per year"]
    C["📋 data/distributions.xlsx\nManually maintained distribution data"]

    A --> B["national_load_baseis.py"]
    C --> D["national_pivot_distributions.py"]

    B --> E["data/_pipeline_cache/baseis-master.csv\nLong-format, all years, all departments"]
    D --> F["data/_pipeline_cache/distributions_wide.xlsx\nOne row per year, one column per subject×bin"]

    E --> G["analyse.py --profile NAME"]
    F --> G
    F --> H["national_plot_distributions.py"]

    G --> I["profiles/NAME/analysis-YEAR-HASH.xlsx\nMetric, baseis, predictions for this profile"]
    G --> R["profiles/NAME/report-YEAR-HASH.md\nMarkdown summary"]
    H --> J["output/distributions_plot.png\nComplementary CDF curves, all subjects"]
```

## Scripts in detail

### `national_load_baseis.py`

Reads every `data/baseis-raw/gel-*.xlsx` file and concatenates them into a single
long-format CSV at `data/_pipeline_cache/baseis-master.csv`.

Each raw file has a two-row merged-cell header, which varies slightly across years
(the ministry added two columns in 2025). The loader handles all known variants
automatically through `_build_columns()` — the only place that knows the raw format.

While loading, the console shows an inline progress indicator — the year currently
being processed and its position in the file list.

Key output columns:

| Column              | Description                                                       |
| ------------------- | ----------------------------------------------------------------- |
| `year`              | Extracted from the file title                                     |
| `school_code`       | 4-digit ministry code — stable across years, used as the join key |
| `institution`       | University abbreviation                                           |
| `department`        | Full department name (Greek, includes city)                       |
| `position_type`     | Admission track (e.g. `ΓΕΛ ΓΕΝΙΚΗ ΣΕΙΡΑ ΗΜ.`)                     |
| `field_1`–`field_4` | Boolean: which scientific fields grant access to this department  |
| `entry`             | **The admission threshold** — lowest score admitted (μόρια)       |

### `national_pivot_distributions.py`

Reads `data/distributions.xlsx` (sheet `data-StudentsDistribution`) and produces a
wide-format table at `data/_pipeline_cache/distributions_wide.xlsx`.

In the wide format, each row is one year and each column is `{subject}_{bin}` — for
example `bio_19` holds the percentage of students who scored in the 19–20 bracket in
Biology. This is the format consumed by `analyse.py`.

### `analyse.py --profile NAME`

The analysis script. It reads both cache files and the profile's `schools.yml`, then
writes two output files. The metric weights are loaded from `metric_weights.yml`
(optionally overridden per-profile — see {doc}`profiles`) by `metrics.py`, and the
weight set is persisted to the content-addressable `weights/` store. See
{doc}`methodology` for a full description of what it computes.

The profile's `schools.yml` must declare a `prediction_year`. The script uses
distribution data up to and including that year, and βάσεις data up to
`prediction_year − 1`. Both outputs are named after the prediction year **and the
weight-set hash** (`{prediction_year}-{hash}`), so different weight sets coexist; the
hash is printed at the end of the run. If `distributions_wide.xlsx` does not contain
data for `prediction_year`, the script exits with an error and a message directing
you to update `data/distributions.xlsx`.

**`analysis-{prediction_year}-{hash}.xlsx`** — full workbook:

| Sheet             | Contents                                                             |
| ----------------- | -------------------------------------------------------------------- |
| `high_end_metric` | Weighted metric value and year-over-year shift per year              |
| `metric_weights`  | The weight set used (dense table), with its hash stamped in cell A1  |
| `bin_diffs`       | Raw percentage-point shift per bin, per year transition              |
| `baseis`          | Wide table: entry score per school per year                          |
| `baseis_shifts`   | Year-over-year change in entry score per school                      |
| `baseis_detail`   | Long-format table with institution and department names              |
| `predictions`     | Per-school regression coefficients, predicted shift, predicted entry |

**`report-{prediction_year}-{hash}.md`** — markdown summary with four sections (the
weight-set hash is stamped in the header):

| Section            | Contents                                                          |
| ------------------ | ----------------------------------------------------------------- |
| Metric Weights     | Weights per subject and bin, table format                         |
| Distribution Diffs | Percentage-point shifts per bin and subject, one table per period |
| Baseis Shifts      | Year-over-year threshold changes per school                       |
| Predictions        | Predicted shift and predicted entry per school                    |

### `national_plot_distributions.py`

Reads `data/_pipeline_cache/distributions_wide.xlsx` and plots the complementary CDF
(percentage of students scoring *at or above* each threshold) for each of the four
subjects, with one line per year. The two most recent years are drawn thicker.

The script raises a `FileNotFoundError` with a helpful message if the cache file is
missing — run `national_pivot_distributions.py` first.

## Running the pipeline

```bash
uv run python national_load_baseis.py
uv run python national_pivot_distributions.py
uv run python analyse.py --profile maria
uv run python national_plot_distributions.py
```

Scripts are independent except for the dependency order shown in the diagram above.
`analyse.py` must run after both loaders; the plot script can run in parallel with
`analyse.py` once `national_pivot_distributions.py` has finished.
