# Profiles

A *profile* scopes the analysis to a specific person's list of target schools.
Shared national data (baseis master, distributions) is processed once; each
profile filters and analyses only the schools that matter to that person.

## Directory layout

```
profiles/
  maria/
    schools.yml          # committed — the list of school codes
    analysis.xlsx        # gitignored — generated output
  manou2026/
    schools.yml
    analysis.xlsx
```

## `schools.yml` format

```yaml
schools:
  - "0302"
  - "0295"
  - "0297"
```

Each entry is a 4-digit ministry school code, given as a quoted string to prevent
YAML from interpreting leading zeros as octal. The school code is the stable
cross-year identifier — department names and institution abbreviations drift across
years, but the code does not.

## Finding school codes

The easiest way to find codes is to run `national_load_baseis.py` once and inspect
`data/baseis-master.csv`. Filter by institution name or department keywords:

```python
import pandas as pd
master = pd.read_csv('data/baseis-master.csv', encoding='utf-8-sig')

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
   schools:
     - "XXXX"
     - "YYYY"
   ```

3. Run the analysis:
   ```bash
   uv run python analyse.py --profile NAME
   ```

The `analysis.xlsx` file is created automatically at `profiles/NAME/analysis.xlsx`.

## The `predictions` sheet

The most important output for a profile is the `predictions` sheet, which contains
one row per school with:

- The fitted regression slope (`a`) and intercept (`b`)
- The metric shift used for prediction
- The predicted threshold shift
- The last known threshold and the predicted threshold for the upcoming year

See {doc}`methodology` for a full explanation of how predictions are calculated.
