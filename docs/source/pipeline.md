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

    B --> E["data/baseis-master.csv\nLong-format, all years, all departments"]
    D --> F["output/distributions_wide.xlsx\nOne row per year, one column per subject×bin"]

    E --> G["analyse.py --profile NAME"]
    F --> G
    F --> H["national_plot_distributions.py"]

    G --> I["profiles/NAME/analysis.xlsx\nMetric, baseis, predictions for this profile"]
    H --> J["output/distributions_plot.png\nComplementary CDF curves, all subjects"]
```

## Scripts in detail

### `national_load_baseis.py`

Reads every `data/baseis-raw/gel-*.xlsx` file and concatenates them into a single
long-format CSV at `data/baseis-master.csv`.

Each raw file has a two-row merged-cell header, which varies slightly across years
(the ministry added two columns in 2025). The loader handles all known variants
automatically through `_build_columns()` — the only place that knows the raw format.

Key output columns:

| Column | Description |
|---|---|
| `year` | Extracted from the file title |
| `school_code` | 4-digit ministry code — stable across years, used as the join key |
| `institution` | University abbreviation |
| `department` | Full department name (Greek, includes city) |
| `position_type` | Admission track (e.g. `ΓΕΛ ΓΕΝΙΚΗ ΣΕΙΡΑ ΗΜ.`) |
| `field_1`–`field_4` | Boolean: which scientific fields grant access to this department |
| `entry` | **The admission threshold** — lowest score admitted (μόρια) |

### `national_pivot_distributions.py`

Reads `data/distributions.xlsx` (sheet `data-StudentsDistribution`) and produces a
wide-format table at `output/distributions_wide.xlsx`.

In the wide format, each row is one year and each column is `{subject}_{bin}` — for
example `bio_19` holds the percentage of students who scored in the 19–20 bracket in
Biology. This is the format consumed by `analyse.py`.

### `analyse.py --profile NAME`

The analysis script. It reads both intermediate outputs and produces the profile's
`analysis.xlsx`. See {doc}`methodology` for a full description of what it computes.

Output sheets:

| Sheet | Contents |
|---|---|
| `high_end_metric` | Weighted metric value and year-over-year shift per year |
| `bin_diffs` | Raw percentage-point shift per bin, per year transition |
| `baseis` | Wide table: entry score per school per year |
| `baseis_shifts` | Year-over-year change in entry score per school |
| `baseis_detail` | Long-format table with institution and department names |
| `predictions` | Per-school regression coefficients, predicted shift, predicted entry |

### `national_plot_distributions.py`

Reads `output/distributions_wide.xlsx` and plots the complementary CDF (percentage
of students scoring *at or above* each threshold) for each of the four subjects, with
one line per year. The two most recent years are drawn thicker.

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
