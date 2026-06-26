---
name: plot-distributions
description: >
  Generate a 4-subplot complementary CDF figure showing, per subject,
  the percentage of students scoring at or above each high-end threshold
  across all available years.
inputs:
  - name: distributions_wide
    description: Path to the wide-format distribution pivot
    required: false
    default: output/distributions_wide.xlsx
  - name: from_bin
    description: Lowest score bin to include on the x-axis (default 16)
    required: false
    default: 16
outputs:
  - name: plot
    description: output/distributions_plot.png
---

## What this skill does

Calls `national_plot_distributions.py`, which:

1. Loads `output/distributions_wide.xlsx`.
2. For each subject (bio, phys, chem, lang) and year, computes
   `P[score ≥ threshold]` for all bins from `from_bin` upward — the
   complementary CDF of the high-scoring tail.
3. Renders a 2×2 figure with one subplot per subject, one line per year.
4. Saves to `output/distributions_plot.png` at 150 dpi.

## Command

```bash
uv run python national_plot_distributions.py
```

## Notes

- This reproduces the `Final` sheet from the original `Bro-Maria.xlsx` workbook.
- Output is national (not profile-specific) and is gitignored.
- Requires `matplotlib` (declared in `pyproject.toml`).
