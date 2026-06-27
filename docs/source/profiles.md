# Profiles

A *profile* scopes the analysis to a specific person's list of target schools.
Shared national data (baseis master, distributions) is processed once; each
profile filters and analyses only the schools that matter to that person.

## Directory layout

```
profiles/
  maria/
    schools.yml            # committed — prediction year + school codes
    analysis-2025.xlsx     # gitignored — generated workbook
    report-2025.md         # gitignored — generated markdown summary
  manou2026/
    schools.yml
    analysis-2026.xlsx
    report-2026.md
```

## `schools.yml` format

```yaml
prediction_year: 2025
schools:
  - "0302"
  - "0295"
  - "0297"
```

**`prediction_year`** controls the analysis window:
- Distribution diffs are computed up to `prediction_year − (prediction_year−1)`.
- Βάσεις data is used only up to `prediction_year − 1`, since the upcoming year's
  thresholds are not yet published when the prediction is made.
- Both output files are named after this year: `analysis-{prediction_year}.xlsx`
  and `report-{prediction_year}.md`.

To predict for a different year, change only this field — no code changes are needed.

Each school entry is a 4-digit ministry code, given as a quoted string to prevent
YAML from interpreting leading zeros as octal. The school code is the stable
cross-year identifier — department names and institution abbreviations drift across
years, but the code does not.

## Finding school codes

The easiest way to find codes is to run `national_load_baseis.py` once and inspect
`data/baseis-master.csv`. Filter by institution name or department keywords:

```python
import pandas as pd
master = pd.read_csv('data/_pipeline_cache/baseis-master.csv', encoding='utf-8-sig')

# Find all medicine programs
mask = master['department'].str.contains('ΙΑΤΡ', na=False)
print(master.loc[mask, ['school_code', 'institution', 'department']].drop_duplicates())
```

Field 3 (natural sciences / Biology field) is the typical filter for science programs:

```python
# Departments accessible from the Biology scientific field
field3 = master[master['field_3']]
print(field3[['school_code', 'institution', 'department']].drop_duplicates())
```

## Creating a new profile

1. Create the directory:
   ```bash
   mkdir profiles/NAME
   ```

2. Create `profiles/NAME/schools.yml`:
   ```yaml
   prediction_year: 2025
   schools:
     - "XXXX"
     - "YYYY"
   ```
   Set `prediction_year` to the year you want to predict (typically the current year).

3. Run the analysis:
   ```bash
   uv run python analyse.py --profile NAME
   ```

Two files are created automatically:
- `profiles/NAME/analysis-{prediction_year}.xlsx` — full workbook with metric, baseis and prediction sheets
- `profiles/NAME/report-{prediction_year}.md` — markdown summary with weights, distribution diffs, baseis shifts and predictions

## Reading the outputs

The quickest way to review results is `report-{prediction_year}.md` — a single markdown
file containing four sections:

| Section | Contents |
|---|---|
| **Metric Weights** | Weights per subject and bin used to compute the high-end metric |
| **Distribution Diffs** | Year-over-year percentage-point shifts, one table per period; the prediction period is flagged |
| **Baseis Shifts** | Year-over-year change in admission thresholds per school |
| **Predictions** | Predicted shift, last known threshold, and predicted threshold for each school |

The full workbook (`analysis-{prediction_year}.xlsx`) contains the same data plus the
raw regression coefficients and long-format detail sheets. See {doc}`methodology` for
a full explanation of how predictions are calculated.
