# Code review findings

Reviewed 2026-06-27. Scope: full codebase (`analyse.py`, `metrics.py`,
`national_load_baseis.py`, `national_pivot_distributions.py`, `tests/`).
Ranked most-severe first.

---

## 1 · `national_pivot_distributions.py:21` — No `__main__` guard; all side-effects run on import

All module-level statements (lines 21–95) execute unconditionally: `pd.read_excel`,
`df.drop`, `print`, `get_wide_format`, and `wide_df.to_excel`. Two helper functions
(`get_percentage_by_class_year`, `massage_data_for_class_year`) are defined but only
consumed by that dead exploratory top-level code.

**Failure scenario:** Any future `import national_pivot_distributions` — from a test,
a CLI entry point, or a pipeline orchestrator — reads `distributions.xlsx`, prints to
stdout, and overwrites the cache file. If the source Excel is absent the import crashes
with `FileNotFoundError`. All code past line 20 should move inside
`if __name__ == '__main__':`.

---

## 2 · `analyse.py:128` — `predict()` raises `KeyError` when only one year of distribution data exists

```python
x_pred = float(metric_shift_series.loc[prediction_year])
```

`metric_shift_series` is `metric_df['metric_shift'].dropna()`. With a single-row
`wide_df`, `.diff()` produces one NaN; after `.dropna()` the series is empty.
`.loc[prediction_year]` raises `KeyError` with no useful message.

**Failure scenario:** `distributions_wide.xlsx` contains only `prediction_year` (e.g.
first year of use). `load_wide_df` validates that the year is present but has no
minimum-rows guard, so the file passes and the crash is silent and uninformative.
Fix: add a `≥ 2 rows` check in `load_wide_df` with a clear error.

---

## 3 · `analyse.py:101` — `dropna(how='any')` discards valid training rows

```python
baseis_shift = baseis_wide.diff().dropna()
```

`dropna()` defaults to `how='any'`: a row is dropped if *any* school has a NaN shift.
`predict()` already contains a per-school NaN mask (lines 146–151) designed to handle
exactly these per-school gaps, but it can only act on rows that survive `dropna`.

**Failure scenario:** School A has no entry for 2020, so the 2020 diff row is NaN for
column A. `dropna(how='any')` removes the entire 2020 row, so schools B, C, D also
lose 2020 as a training point even though their data is complete. Fix:
`baseis_shift = baseis_wide.diff().dropna(how='all')` — only drop rows where *every*
school is missing.

---

## 4 · `analyse.py:129` — `pred_label` hardcodes `prediction_year - 1`; wrong with non-consecutive years

```python
pred_label = f'{prediction_year}-{prediction_year - 1}'
```

`compute_bin_diffs` labels periods from actual adjacent years in the index:
`f'{years[i]}-{years[i-1]}'`. If there is a gap in the distribution data (e.g.
`[2019, 2021, 2025]`), the last period is `'2025-2021'`, but `pred_label` is
`'2025-2024'`.

**Failure scenario:** The `'← prediction period'` annotation in the report never fires
(no period matches `pred_label`). The `metric_shift (2025-2024)` column in
`prediction_df` is factually mislabelled. Fix: derive `pred_label` from the actual
last two entries of `wide_df.index` rather than from arithmetic.

---

## 5 · `national_pivot_distributions.py:86` — `fill_value=0` silently imputes missing bins as 0%

```python
wide_df = df.pivot_table(index='year', columns='class_marks_bin',
                          values='percentage', fill_value=0)
```

A class/year/bin combination not present in the source data is filled with `0.0`
rather than `NaN`.

**Failure scenario:** A subject not administered in a given year (or a bin with no
reported students) appears as a genuine 0% across all bins rather than as absent data.
The weighted metric treats those cells as real observations, silently biasing scores.
Downstream code has no way to detect or filter the imputation. Drop `fill_value` and
handle NaNs explicitly.

---

## 6 · `metrics.py:41` — `_validate` is a denylist; never checks that all `CLASSES` are present

```python
def _validate(weights):
    for cls, mapping in weights.items():
        if cls not in CLASSES: raise ValueError(...)
```

Only listed classes are validated. A `metric_weights.yml` that omits a class entirely
(e.g. `chem` deleted by mistake) passes without error.

**Failure scenario:** `weight_vector` zero-fills the absent class, silently setting all
`chem` weights to 0.0. The metric is numerically wrong with no diagnostic. The same
omission later crashes `build_report` (see #7). Fix: add a membership check after
loading — `for cls in CLASSES: assert cls in weights`.

---

## 7 · `analyse.py:267` — `build_report` raises `KeyError` when a class is absent from loaded weights

```python
{cls: {b: metric_weights[cls].get(b, '') for b in weight_bins} for cls in classes}
```

`classes` is the module-level `CLASSES` constant (all four subjects). `metric_weights`
is the dict returned by `load_weights`, which allows partial coverage (see #6).

**Failure scenario:** A `metric_weights.yml` missing `'phys'` passes `_validate`,
produces a wrong metric silently, then crashes `build_report` with
`KeyError: 'phys'` when the report is rendered. The crash is a consequence of #6; the
fix to #6 eliminates this path too, but `build_report` should also use `.get(cls, {})`
defensively.

---

## 8 · `national_load_baseis.py:78` — `_extract_year` matches the *first* 4-digit group, not the last

```python
match = re.search(r'(\d{4})', title)
```

The docstring says the title "always ends with the 4-digit year", but `re.search`
returns the first match, not the last.

**Failure scenario:** A title whose format changes to include a 4-digit code before
the year (e.g. a ministry file-ID prefix) silently returns the wrong year. All rows
from that file get an incorrect `year` column, corrupting the master CSV with no
error. Fix: `re.search(r'(\d{4})\s*$', title)` anchors the match to the end.

---

## 9 · `analyse.py:91` — `isin` type mismatch when `schools.yml` codes are unquoted integers

```python
_sc = master['school_code'].astype('Int64').astype(str).str.zfill(4)
baseis_df = master.loc[_sc.isin(schools), ...]
```

`schools` comes from YAML. Unquoted numeric values in YAML are parsed as Python `int`
(e.g. `- 302`). `_sc` is a `str` Series after `.astype(str)`; `isin([302, 295])` against
strings returns all-`False`.

**Failure scenario:** A new profile written with unquoted school codes (natural YAML
style) produces an empty `baseis_df` with no error or warning. `predict()` runs on
zero schools and returns an empty `prediction_df`; the report is silently empty. Fix:
coerce `schools` to strings on load, or validate that `_sc.isin(schools)` yields at
least one match before proceeding.

---

## 10 · `metrics.py:119` — Parameter `hash` shadows the Python built-in

```python
def persist_weights(weights, hash=None, weights_dir=WEIGHTS_DIR):
```

The name `hash` resolves to the parameter (a `str` or `None`) for the entire function
scope, shadowing `builtins.hash`.

**Failure scenario:** Any future code added inside `persist_weights` that calls
`hash(...)` for a standard equality check or dict lookup will invoke the string
parameter instead, raising `TypeError: 'str' object is not callable` with a confusing
message. Rename to `h` or `weight_hash`.
