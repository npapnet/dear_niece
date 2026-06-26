---
name: load-baseis
description: >
  Rebuild the master baseis CSV from all raw ministry xlsx files in
  data/baseis-raw/. Run this whenever a new gel-{YEAR}.xlsx is added.
inputs:
  - name: raw_dir
    description: Path to the folder containing gel-*.xlsx files
    required: false
    default: data/baseis-raw/
outputs:
  - name: master_csv
    description: data/baseis-master.csv — long-format table, one row per (year, school, position_type)
---

## What this skill does

Calls `national_load_baseis.py`, which:

1. Globs all `gel-*.xlsx` files in `data/baseis-raw/`.
2. For each file, resolves the two-row merged-cell header automatically (handles the 12-col 2023/2024 layout and the 14-col 2025+ layout).
3. Drops tiebreak-criteria columns (no analytical value).
4. One-hot encodes the `ΕΠΙΣΤΗΜΟΝΙΚΑ ΠΕΔΙΑ` field into `field_1`–`field_4` bool columns.
5. Concatenates all years into a single long-format DataFrame.
6. Writes `data/baseis-master.csv` (UTF-8 with BOM for Excel compatibility).

## Command

```bash
uv run python national_load_baseis.py
```

## Notes

- The output CSV is gitignored — it is always regenerated from the raw files.
- See `architecture.md` → *Raw file format* for the column schema.
