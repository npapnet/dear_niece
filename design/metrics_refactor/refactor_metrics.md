# Refactor: configurable high-end metric weights

> Design document / plan for the metric-weights refactor. See
> [`architecture.md`](../../architecture.md) for the surrounding pipeline.

## Context

`analyse.py` computes a *weighted high-end metric* from the national mark
distributions and regresses its year-over-year shift against βάσεις shifts to
predict admission thresholds. The weights currently live in a hardcoded
`METRIC_WEIGHTS` dict (`analyse.py:91-96`) as a sparse `{class: {bin: weight}}`
mapping. Motivations for this refactor:

1. **Weights are not configurable** — changing them requires editing code, and
   every profile is forced to share one weight set.
2. **No way to compare weight sets** — re-running with different weights
   overwrites the previous `analysis-{year}.xlsx` / `report-{year}.md`.
3. **No tests.** The weights convention is about to change substantially, with no
   safety net guaranteeing that the *same input still yields the same output*.
   This refactor is therefore sequenced **testing-first** (see Phase 0).
4. **Make the future weight-optimization / NN commit trivial.** The metric is
   already a tiny linear net (weights × per-bin features); the planned NN
   (`TODOS.md`) will *learn* the weights. If weights are exposed as a dense,
   content-addressable array now, the trainer can simply emit weight arrays that
   the existing pipeline consumes **with no structural change**. The NN training
   itself is out of scope for this sprint — this refactor only lays the
   foundation so that commit is easy.

Two clarifications shape the representation:

- **Weights are real-valued (floats), not integers.** The current integer
  defaults are just one case; the config and validation must accept floats.
- **The metric will expand from a few high-end bins to all schools/bins.** When
  it does, weights become *dense and ~1 everywhere* rather than a sparse integer
  dict — so a dense `float64` array over all 48 bins is the right internal
  representation from the start.

**Intended outcome.** Weights are loaded from config (global default +
per-profile override), the metric is computed via a dense dot product over the
per-year distribution, every weight array used is persisted as a
content-addressable artifact, and outputs are suffixed with a short hash of the
weight array so different weight sets coexist without clobbering one another.

## Decisions

| Topic | Decision |
|---|---|
| **Config location** | Global `metric_weights.yml` at repo root holds defaults; `schools.yml` may carry an optional `metric_weights:` block that overrides. |
| **Representation** | Author **sparse YAML** (readable, floats allowed); materialize a **dense `float64` array/DataFrame** internally (bins × classes, zero-filled), aligned to the 48 `{class}_{bin:02d}` columns. The dense 48-vector is the canonical form. |
| **Weight store** | Content-addressable folder `weights/{hash}.npy` — each dense weight array actually used is persisted there (with a sparse-YAML sidecar for readability). This is the drop-zone the future NN writes into. |
| **Hash** | Computed from the **canonical numpy array**, not any string/YAML form: fixed `CLASSES×BINS` column order, `float64`, C-contiguous, rounded to 6 decimals, then `sha256(arr.tobytes())`, first 6 hex chars. |
| **Output differentiation** | **Always** append the hash: `analysis-{year}-{hash}.xlsx`, `report-{year}-{hash}.md`. |
| **Override semantics** | Per-class replace. If `schools.yml` names a class, its mapping fully replaces the global mapping for that class; unnamed classes fall back to global. |

### Authoring (sparse YAML) vs internal (dense array)

These are two layers, not two competing choices. The YAML — both
`metric_weights.yml` and any `schools.yml` override — is only how a *human types*
weights. `dense_weights()` is a one-way bridge that expands it into the dense
`float64` 48-vector the code computes with; sparse YAML is just a compact
spelling of that dense array (`{19: 1.0}` ≡ `[0,…,0,1.0]`). So a sparse default
file does not contradict the dense internal form — it *materializes* into it.

YAML is the authoring surface because it is readable and states intent (`phys:
{17:1,18:2,19:3}` reads as a ramp), and because the current metric genuinely is
sparse (bins 0,5,10–13 weigh 0 for every subject). Genuinely-dense or
machine-generated weights have their own home — `weights/{hash}.npy`. Humans
author sparse YAML; machines emit dense `.npy`.

**Baseline fill for the dense regime.** The `absent ⇒ 0` convention suits the
current high-end metric, but once the metric expands to all schools and weights
cluster near 1, a 0-default forces you to list all 48 entries. To keep authoring
sparse *relative to a baseline* in both regimes, the YAML supports an optional
`default:` fill value; `dense_weights()` fills the array with it, then overlays
the listed bins:

```yaml
default: 0.0                 # current regime (also the implicit default)
bio:  {19: 1.0}
...
```
```yaml
default: 1.0                 # future all-schools regime: everything ~1
phys: {17: 0.9, 19: 1.2}     # only the deviations from 1
```

### Why hash the array, not the string

String/YAML reprs are lossy and depend on key order, float formatting, and
locale, so equivalent weights could hash differently. Hashing the canonicalized
`float64` array (fixed order + rounding) is representation-independent: any two
spellings that yield the same dense weights produce the same hash, and the
rounding prevents float-noise from exploding the hash space.

### Config shape

`metric_weights.yml` (repo root — global default; floats accepted, current
values shown verbatim):

```yaml
# verbatim from analyse.py:91-96; explicit 0s mark "considered but unweighted".
# values are real-valued — integers here are just the current default.
bio:  {18: 0.0, 19: 1.0}
chem: {18: 0.0, 19: 1.0}
lang: {14: 0.0, 15: 1.0, 16: 2.0, 17: 3.0, 18: 4.0, 19: 5.0}
phys: {16: 0.0, 17: 1.0, 18: 2.0, 19: 3.0}
```

`profiles/<name>/schools.yml` (optional override; backward compatible — absent
key ⇒ use global):

```yaml
prediction_year: 2025
metric_weights:          # optional; per-class replace; floats fine
  phys: {18: 0.7, 19: 1.3}
schools:
  - "0302"
  - "0295"
```

## Phased scope

Sequenced **testing-first**: the safety net (Phase 0) lands before any weights
change, so "same input → same output" is enforced mechanically. The deep
restructure (package + `dn` CLI) is deliberately **last** — it is the
highest-risk change and should happen *under* the tests, not before them.

### Phase 0 — Testing foundation + shallow restructure ✅ done

Implemented and green (`uv run pytest` → 7 passed). What landed:

- **pytest wired** via `[dependency-groups] dev` and `[tool.pytest.ini_options]`
  (`pythonpath = "."`, `testpaths = ["tests"]`).
- **`analyse.py` restructured** into importable, side-effect-free functions —
  `get_class_distribution`, `compute_bin_diffs`, `compute_metric_df`,
  `load_wide_df`, `read_master`, `load_baseis_df`, `compute_baseis`, `predict`,
  `run_analysis(...) -> dict`, `write_workbook`, `build_report` — with all file
  IO and the CLI under `main()` (which accepts injected cache/profile paths).
  **Verified behaviour-preserving:** the maria workbook and report came out
  byte-identical to the pre-restructure output (generated-date aside).
- **Synthetic fixtures** in `tests/conftest.py` (`make_wide_df`, `make_master_df`)
  — no dependency on the gitignored cache; values chosen so the metric,
  bin_diffs, and regression are independently hand-computable.
- **Weights/metric unit + integration tests** in `tests/test_metrics_pipeline.py`
  (hand-computed expected values for the weighting, bin_diffs, the per-school
  regression, and end-to-end `run_analysis`).
- **End-to-end golden backup** — `profiles/_golden/` (committed `schools.yml`,
  `README.md` documenting the exact synthetic parameters, frozen
  `expected-report-2025.md`); `tests/test_golden_profile.py` runs the full
  `main()` path on synthetic data and diffs the report (normalising the
  `_Generated:` date); `tests/_golden_helpers.py` + `tests/_regen_golden.py`
  share the run logic and regenerate the golden after intended changes.

### Phase 1 — Config-loaded weights + `metrics.py` (dense representation) ✅ done

Implemented and green (`uv run pytest` → 22 passed); `analyse.py --profile maria`
runs clean. As planned, the golden report was regenerated — the **only** change is
the Metric Weights table now rendering 2-decimal floats (`1.00` vs `1`); all
numeric sections (diffs, baseis shifts, predictions) are byte-identical. The
`metric_weights.yml` no-drift, override, validation, materialization, name-aligned
`compute_metric`, and `weights_hash` representation-independence tests all pass.
`weights_hash` is built but not yet consumed (Phase 2).

Re-scoped to the post-Phase-0 code: `run_analysis(...)` already accepts
`metric_weights` and `compute_metric_df` already isolates the metric — so Phase 1
is a new module + config file + wiring, **not** a rewrite of the compute path.

**New `metrics.py`** (repo root) owns the weight logic and the shared constants,
imported one-way (`analyse → metrics`) to avoid an import cycle:

- Move `CLASSES`, `BINS`, and the default weights into `metrics.py` as
  `DEFAULT_WEIGHTS` — **float-valued** (e.g. `{18: 0.0, 19: 1.0}`), mirroring the
  real-valued `metric_weights.yml` rather than today's int literals. `analyse.py`
  imports them and keeps `METRIC_WEIGHTS = metrics.DEFAULT_WEIGHTS` as an alias so
  `run_analysis`'s default and the synthetic fixtures keep working. Float vs int
  weights yield the identical rounded metric/diffs/predictions, so the hand-computed
  tests are unaffected; the only visible change is the report's weights-table
  rendering (see Guard).
- `load_weights(profile_cfg, default_path=METRIC_WEIGHTS_YML) -> dict` — read
  `metric_weights.yml`, apply the per-class override from `profile_cfg`, validate
  class ∈ `CLASSES`, bin ∈ `BINS`, weight numeric (clear error otherwise).
- `dense_weights(weights) -> pd.DataFrame` — sparse dict → dense `float64`
  `BINS × CLASSES` table (implicit-0 fill); the readable form for the workbook
  sheet.
- `weight_vector(weights) -> pd.Series` — the same weights as a Series indexed by
  the 48 `{class}_{bin:02d}` names (fixed canonical order). This **name-indexed**
  form drives `compute_metric` and `weights_hash`, so both are column-order
  independent (fixes the silent-misalignment trap).
- `compute_metric(wide_df, weights) -> pd.Series` — name-aligned dot product
  `(wide_df.reindex(columns=weight_vector.index, fill_value=0) * weight_vector).sum(axis=1)`;
  a bin absent from `wide_df` counts as 0 (a percentage bin that never appeared is
  genuinely 0%), so it's robust to missing columns, not just to column order.
- `weights_hash(weights) -> str` — `weight_vector` → `float64`, C-contiguous,
  `round(6)` (and `+ 0.0` to collapse `-0.0`) → `sha256(.tobytes())`, first 6 hex.
  Built now, consumed in Phase 2.

**`analyse.py` changes:**

- Import `CLASSES`/`BINS`/defaults from `metrics.py`; drop the local copies.
- `compute_metric_df` delegates to `metrics.compute_metric`, then appends
  `.diff()` (no inline loop); rounding preserved.
- `main()` loads weights via `load_weights(_profile_cfg, …)` and threads them to
  `run_analysis(metric_weights=weights)` and `build_report`.
- Add a `metric_weights` sheet (the `dense_weights` table) to the workbook.

**New `metric_weights.yml`** (repo root, committed) — the canonical default,
mirroring `DEFAULT_WEIGHTS`.

**Tests** (`tests/test_metrics.py`):

- `load_weights` override semantics + validation errors.
- `dense_weights` / `weight_vector` materialization (implicit-0 fill, name
  alignment).
- `compute_metric` against a hand-computed value **and** equal to
  `compute_metric_df`'s metric on synthetic data.
- `weights_hash` stability + representation-independence (key order; `1` vs `1.0`).
- **No-drift:** `metric_weights.yml` parses to exactly `DEFAULT_WEIGHTS`.

**Guard:** default weights ⇒ identical *numeric* metric/diffs/predictions, so the
synthetic hand-computed tests stay green unchanged. **The golden report does change
in one cosmetic way and is regenerated in this phase:** because weights are now
real-valued (`DEFAULT_WEIGHTS` and `metric_weights.yml` are float-authored), the
report's existing "## Metric Weights" table renders 2-decimal floats (`1.00` instead
of `1`) — consistent with the report's house style, since the Distribution Diffs and
Predictions tables already render `.2f`. This is an *intended* change isolated to the
weights-table cells: regen with `uv run python tests/_regen_golden.py` and confirm the
diff touches only those cells (metric/diffs/predictions values unchanged). The new
`metric_weights` *workbook sheet* is additive — the golden test diffs only the report
`.md`, so the sheet can't affect it.

> Note: the "no-drift" test (`metric_weights.yml` parses to `DEFAULT_WEIGHTS`) is now
> an exact float-to-float equality; it would *not* by itself catch an int-vs-float
> spelling slip (`1 == 1.0`), so the regenerated golden report is what actually pins
> the rendered table.

**Deferred:** the `default:` baseline-fill (see §"Baseline fill for the dense
regime") — its interaction with per-class override is under-specified and
unnecessary while weights are sparse. Implement only implicit-0 now; revisit for
the all-schools regime.

### Phase 2 — Content-addressable store + hash-suffixed outputs ✅ done

Implemented and green (`uv run pytest` → 24 passed); `analyse.py --profile maria`
writes `analysis-2025-32edbf.xlsx` / `report-2025-32edbf.md` and the store
`weights/32edbf.{npy,yml}` (default-weights hash `32edbf`). What landed:
`metrics.persist_weights` (immutable per hash, canonical `.npy` + sparse `.yml`);
`main()` persists + hash-suffixes both outputs and prints the hash;
`build_report` stamps `_Weights hash: \`…\`_` in the header and `write_workbook`
stamps it into cell A1 of the `metric_weights` sheet; `.gitignore` ignores
`weights/`; `tests/_golden_helpers.py` globs the hash-suffixed report and sandboxes
the store under a tmp `weights_dir`; golden regenerated (sole diff: the new hash
header line); `architecture.md` updated for the naming convention + `weights/` dir.
The "find the current output" UX is handled by printing the hash and globbing
`report-{year}-*.md`.

> Phase 2 review (vs the post-Phase-1 code/architecture): no blockers — the design
> stands. Refinements folded in below: signature of `persist_weights` (it needs the
> dict, not a bare array, to write both forms), removal of stale line-number
> references (the code moved in Phases 0–1), the `metric_weights` sheet already
> existing, the "find the current output" UX gap, and a tightened docs scope.

- `persist_weights(weights, hash=None) -> str` in `metrics.py` — takes the **weights
  dict** (not a bare array) so it can write *both* forms: persist the canonical
  48-vector `weight_vector(weights).to_numpy()` to `weights/{hash}.npy` (this is the
  form the NN emits/consumes and the exact array `weights_hash` hashes, so
  reload→rehash is stable) **and** dump the sparse dict to a `weights/{hash}.yml`
  sidecar for readability. Compute the hash internally via `weights_hash` when not
  supplied; skip writing if the files already exist; return the hash.
- Compute `hash = weights_hash(weights)` in `main()` and name outputs
  `analysis-{prediction_year}-{hash}.xlsx` and `report-{prediction_year}-{hash}.md`
  (the output-naming + `write_workbook` / `report_out.write_text` calls all live in
  `main()` now — reference by symbol, not line number; Phases 0–1 moved the code).
- Surface the weights + hash: add the hash to the report (extend the `build_report`
  header — it already renders a "## Metric Weights" table) and to the **existing**
  `metric_weights` workbook sheet (Phase 1 added the sheet; Phase 2 only adds the
  hash label, it does not create the sheet).
- **Finding "the" output (UX gap).** Hash suffixes let weight sets coexist but break
  the "one predictably-named file per year" assumption in the [Goal](../../architecture.md)
  and the `yearly-update` workflow. Settle + document how the current run is located
  when Phase 2 starts — e.g. print the hash at the end of `main()` and have consumers
  glob `report-{year}-*.md` (newest), since the default-weights hash is stable.
- `.gitignore`: add `weights/` (generated, reproducible from YAML; pin a specific
  experiment by committing its `{hash}.*` if desired). `profiles/*/analysis-*.xlsx`
  and `profiles/*/report-*.md` already match the hash-suffixed names (and
  `report-*.md` does **not** match the committed `expected-report-*.md`, so the
  golden stays tracked).
- **Golden test plumbing:** `tests/_golden_helpers.py` hardcodes the output name
  `report-{year}.md` (the `report = … / f'report-{SYNTH_PREDICTION_YEAR}.md'` line);
  update it to resolve the hash-suffixed file (e.g. glob `report-{year}-*.md`). The
  report header now carries the (deterministic) hash, so regenerate the golden once
  with `tests/_regen_golden.py`.
- Docs: update `architecture.md` for the hash-suffixed convention — the directory-layout
  `profiles/*/analysis-*.xlsx` / `report-*.md` lines, a new gitignored `weights/`
  entry, and the `prediction_year` Key-convention bullet (which names the output
  files). **Out of scope here:** the `.agents/skills/*` and
  `.agents/workflows/yearly-update.md` docs are *already* stale (they reference
  `output/distributions_wide.xlsx`, `data/baseis-master.csv`, `analysis.xlsx` with no
  year, and non-existent `percentile_*` sheets); refreshing them is a **separate
  doc-cleanup task**, not part of Phase 2's weights work.

### Phase 3 — (Deferred, separate commit) package + `dn` CLI

**Moved out.** Phase 3 is deferred future work and now lives in its own spec:
[`design/future_work/refactor_package.md`](../future_work/refactor_package.md).
It promotes the already-importable modules into a `src/dear_niece/` package with
console subcommands and is done **after** the weights work, guarded by the Phase 0
tests. See that document for the path-handling blocker, the `[project.scripts]`
wiring, and why packaging is not required for the NN.

### How this makes the future NN commit easy

The NN trainer (separate, future) produces a dense weight array per school/run.
It hashes and drops each array into `weights/{hash}.npy` using the same
`weights_hash` / `persist_weights` helpers, then runs `analyse.py` pointed at
that weight set. No change to the metric computation, the output naming, or the
regression — the array *is* the learned linear layer.

## Critical files

- `analyse.py` — `compute_metric_df` (delegates to `metrics` in Phase 1),
  `run_analysis` (already takes `metric_weights`), `write_workbook` (sheets),
  `main` (config load + output names), `build_report`.
- `national_pivot_distributions.py:85-87` — defines the `{class}_{bin:02d}`
  column convention the dense vector must align to.
- `architecture.md`, `.agents/skills/run-profile-analysis.md` — naming/config docs.
- Added (Phase 0): `tests/conftest.py`, `tests/test_metrics_pipeline.py`,
  `tests/test_golden_profile.py`, `tests/_golden_helpers.py`, `tests/_regen_golden.py`,
  `profiles/_golden/{schools.yml,README.md,expected-report-2025.md}`; pytest in
  `pyproject.toml`.
- New (Phase 1): `metrics.py`, `metric_weights.yml`, `tests/test_metrics.py`.
- New (Phase 2): `weights/` (generated).
- Phase 3 (deferred): see [`design/future_work/refactor_package.md`](../future_work/refactor_package.md)
  — `src/dear_niece/`, `[project.scripts]` in `pyproject.toml`.

## Verification

1. **Test suite green:** `uv run pytest` passes — the Phase 0 synthetic
   unit/integration tests and golden-report backup, plus the Phase 1
   `tests/test_metrics.py`.
2. **Same input → same output (the headline guarantee):** with default weights,
   the synthetic golden report and the hand-computed metric/regression assertions
   stay green across the weights refactor (Phases 1–2). The golden report is
   unchanged by Phase 1 (the `metric_weights` sheet is workbook-only); Phase 2's
   report-header + filename changes are absorbed by regenerating the golden and
   by pinning **values**, tolerant of the hash-suffixed filename.
3. `uv run python analyse.py --profile maria` runs clean, prints the metric table
   as before, and writes `weights/{hash}.npy`.
4. **Float weights work:** an override with non-integer weights runs and produces
   a sensible metric.
5. **Override works:** add a `metric_weights:` block to
   `profiles/maria/schools.yml`, re-run, confirm a *different* hash suffix, a
   changed metric, a new `weights/{hash}.npy`, and that the default output is not
   overwritten.
6. **Hash stability & representation-independence:** identical weights → identical
   hash across runs; reordering YAML keys or re-spelling integers as floats
   (`1` vs `1.0`) yields the *same* hash (canonical array + rounding).
