---
name: process-distributions
description: >
  Build the wide-format grade distribution pivot from Bro-Maria.xlsx.
  Run this whenever new student distribution data is added to the Excel file.
inputs:
  - name: student_data
    description: Path to the student distribution Excel file
    required: false
    default: data/Bro-Maria.xlsx
outputs:
  - name: wide_df
    description: output/wide_df.xlsx — rows=year, cols=subject_scorebin, values=percentage
---

## What this skill does

Calls `process-pre.py`, which:

1. Reads the `data-StudentsDistribution` sheet from `data/Bro-Maria.xlsx`.
2. Renames Greek column headers and maps subject names to abbreviations
   (`Βιολογία`→`bio`, `Φυσική`→`phys`, `Χημεία`→`chem`, `γλώσσα`→`lang`).
3. Parses the score bin label (e.g. `'10 - 10.9'` → `10`) into `marks_bin_start`.
4. Pivots to wide format: index=year, columns=`{subject}_{bin:02d}`, values=percentage.
5. Writes `output/wide_df.xlsx`.

## Command

```bash
uv run python process-pre.py
```

## Notes

- 12 bins per subject: `00`, `05`, `10`–`19` (48 columns total for 4 subjects).
- Data currently covers 2022–2025 (48 rows per year, 192 rows total in the source sheet).
- Output is gitignored and always regenerated.
