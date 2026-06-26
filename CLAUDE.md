# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Read [`architecture.md`](architecture.md) before making any changes — it is the authoritative design document and the shared entry point for both Claude Code and Antigravity clients.

## Environment

```bash
uv sync
uv run python national_load_baseis.py          # data/baseis-master.csv
uv run python national_pivot_distributions.py  # output/distributions_wide.xlsx
uv run python analyse.py --profile maria       # profiles/maria/analysis.xlsx
uv run python national_plot_distributions.py   # output/distributions_plot.png
```
