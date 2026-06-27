# `_golden` — end-to-end regression profile (synthetic)

This is **not a real person's profile**. It is a committed, deterministic,
end-to-end backup test for `analyse.py`: a fixed synthetic input is run through
the full `main()` path and the produced report is diffed against the frozen
`expected-report-2025.md`. It complements the synthetic unit tests in
`tests/test_metrics_pipeline.py`.

Driven by `tests/test_golden_profile.py`. The synthetic data is built in
`tests/conftest.py` (`make_wide_df`, `make_master_df`) — **not** read from the
real (gitignored) pipeline cache — so the golden is reproducible anywhere.

## Exact parameters

- `prediction_year`: **2025**
- `schools`: **9001, 9002** (synthetic ministry codes)
- Weights: the default `METRIC_WEIGHTS` in `analyse.py`.

## Synthetic data (so the numbers are hand-checkable)

Distributions: every one of the 48 `{class}_{bin:02d}` bins is 0 except
`bio_19`, which the default weights give weight 1 (all other weighted bins are
0), so the weighted metric for a year equals that year's `bio_19`:

| year | 2021 | 2022 | 2023 | 2024 | 2025 |
|------|------|------|------|------|------|
| metric (`bio_19`) | 10 | 12 | 15 | 19 | 24 |
| metric_shift | — | 2 | 3 | 4 | 5 |

Baseis (`entry`, max per year) — chosen so each school's shift is an exact
linear function of `metric_shift` (hence `r2 = 1`):

| school | 2021 | 2022 | 2023 | 2024 | shift law | predicted_entry_2025 |
|--------|------|------|------|------|-----------|----------------------|
| 9001 | 1000 | 1025 | 1060 | 1105 | `10·Δ + 5` | **1160** |
| 9002 | 2000 | 2040 | 2100 | 2180 | `20·Δ + 0` | **2280** |

Prediction period `2025-2024` uses `metric_shift = 5`.

## Regenerating the golden

If a change *intentionally* alters the report, regenerate and re-commit:

```bash
uv run python -m pytest tests/test_golden_profile.py        # fails, shows the diff
# inspect the diff; if the change is intended:
uv run python tests/_regen_golden.py                        # rewrites expected-report-2025.md
```

The `_Generated:` date line is normalised away during comparison, so it never
causes spurious failures.
