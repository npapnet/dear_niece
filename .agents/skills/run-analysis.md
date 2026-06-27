---
name: run-analysis
description: >
  DEPRECATED — superseded by run-profile-analysis. analyse.py requires --profile,
  so there is no profile-less analysis path. Use run-profile-analysis instead.
inputs:
  - name: profile
    description: Profile name — must match a directory under profiles/ containing schools.yml
    required: true
outputs:
  - name: analysis
    description: profiles/{name}/analysis-{year}-{hash}.xlsx (see run-profile-analysis)
---

## Deprecated

This skill is kept only as a redirect. `analyse.py` always runs against a profile
(`--profile` is required), so the historical "run-analysis without a profile" idea no
longer exists.

Use **[`run-profile-analysis`](run-profile-analysis.md)** — it documents the current
inputs (`data/_pipeline_cache/distributions_wide.xlsx`,
`data/_pipeline_cache/baseis-master.csv`), the seven workbook sheets, the markdown
report, and the weight-set hash suffix on the outputs.

## Command

```bash
uv run python analyse.py --profile <name>
```
