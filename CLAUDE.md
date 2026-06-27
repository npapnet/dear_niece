# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Read [`architecture.md`](architecture.md) before making any changes — it is the authoritative design document and the shared entry point for both Claude Code and Antigravity clients.

Read [`.agents/rules.md`](.agents/rules.md) for behavioural rules that apply to all interactions in this repository.

## Environment

```bash
uv sync
uv run python national_load_baseis.py          # data/_pipeline_cache/baseis-master.csv
uv run python national_pivot_distributions.py  # data/_pipeline_cache/distributions_wide.xlsx
uv run python analyse.py --profile maria       # profiles/maria/analysis-2025-{hash}.xlsx + report-2025-{hash}.md
uv run python national_plot_distributions.py   # output/distributions_plot.png
uv run pytest                                  # run the test suite
```
