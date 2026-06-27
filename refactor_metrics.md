# Refactor: configurable high-end metric weights

> Design document / plan for the metric-weights refactor. See
> [`architecture.md`](architecture.md) for the surrounding pipeline.

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

### Phase 0 — Testing foundation + shallow restructure (do first)

Goal: a green characterization net before the weights convention changes. **No
behavioural change in this phase.**

- Add **pytest** as a dev dependency (`.pytest_cache/` is already gitignored).
- **Capture a golden master from the *current* code, via subprocess.** Build a
  small committed fixture under `tests/fixtures/` (a trimmed `distributions_wide`
  + `baseis-master` + a `schools.yml`), run `analyse.py --profile <fixture>` as a
  subprocess, and snapshot the analytical outputs (`high_end_metric`,
  `bin_diffs`, `predictions` sheet values) as the expected baseline. Running the
  flat script as a subprocess lets this test protect the *very first* restructure
  without needing to import the script.
- **Shallow restructure** `analyse.py` into importable, side-effect-free
  functions that take inputs as arguments (DataFrames/paths injected, not read
  from module-level constants), with the CLI under a `main()` guard. Strictly
  behaviour-preserving; the subprocess golden master stays green throughout.
  This is Option 1 ("importable functions + `main()`") and is a strict *subset*
  of the eventual package work (Phase 3) — nothing here is throwaway.
- **Unit tests** on the now-importable pure functions (regression, bin_diffs,
  baseis pivot/shift) with fixture DataFrames.

Pin **values, not filenames or sheet sets** — Phases 1–2 intentionally rename
outputs (hash suffix) and add a `metric_weights` sheet, so the golden master
asserts the numbers and tolerates additive sheets / renamed files.

Representative new files: `tests/conftest.py`, `tests/fixtures/…`,
`tests/test_characterization.py`, `tests/test_analysis.py`.

### Phase 1 — Config + dense metric computation

New module **`metrics.py`** (repo root), so the logic is reusable (by the future
NN) and out of the `analyse.py` script body:

- `load_weights(profile_cfg, default_path) -> dict` — read `metric_weights.yml`,
  apply per-class override from `profile_cfg`, validate every class ∈ `CLASSES`,
  every bin ∈ `BINS`, and every weight is numeric/float (clear error otherwise).
- `dense_weights(weights) -> pd.DataFrame` — sparse dict → dense `float64`
  DataFrame indexed by `BINS`, columns `CLASSES`, zero-filled. Also exposes the
  flattened canonical vector aligned to the 48 `{class}_{bin:02d}` columns.
- `compute_metric(wide_df, weights) -> pd.Series` — per-year metric = dot product
  of the dense weight vector with each year's distribution row.
- `weights_hash(dense_vector) -> str` — canonical `float64`, C-contiguous,
  `round(6)` → `sha256(.tobytes())`, first 6 hex chars.

Add **unit tests for `metrics.py`** (`tests/test_metrics.py`): `load_weights`
override semantics + validation errors, `dense_weights` materialization and
baseline-`default` fill, `compute_metric` against a hand-computed value, and
`weights_hash` stability/representation-independence.

`analyse.py` changes:

- Delete the hardcoded `METRIC_WEIGHTS` (lines 91-96) and the inline nested-loop
  metric (lines 98-110); call `metrics.py` instead. `metric_shift` stays
  `metric.diff()` exactly as today.
- Load weights right after `schools.yml` is parsed (near `analyse.py:35-37`).
- Add a `metric_weights` sheet (the dense df) to the workbook for traceability.
- Keep the existing `high_end_metric` and `bin_diffs` sheets unchanged in shape.

### Phase 2 — Content-addressable store + hash-suffixed outputs

- `persist_weights(dense_array, hash)` in `metrics.py` — write
  `weights/{hash}.npy` (dense array) plus a `weights/{hash}.yml` sidecar (sparse,
  human-readable) if not already present.
- Compute `hash = weights_hash(...)` and name outputs
  `analysis-{prediction_year}-{hash}.xlsx` and
  `report-{prediction_year}-{hash}.md` (replaces `analyse.py:49`, `:311`).
- Put the weights + hash in the report header (extend `build_report`,
  `analyse.py:240-308`) and the `metric_weights` workbook sheet.
- `.gitignore`: add `weights/` (generated, reproducible from YAML; pin a specific
  experiment by committing its `{hash}.*` if desired). `profiles/*/analysis-*.xlsx`
  and `profiles/*/report-*.md` already match the hash-suffixed names.
- Docs: update the naming convention in `architecture.md` (lines 47-53, 95,
  102-103) and the output-file references in
  `.agents/skills/run-profile-analysis.md` and `run-analysis.md`.

### Phase 3 — (Deferred, separate commit) package + `dn` CLI

Promote the already-importable modules into a `src/dear_niece/` package with
console subcommands (`dn load_baseis`, `dn pivot_distributions`,
`dn analyze --profile maria`, later `dn train`). Done **after** the weights work,
guarded by the Phase 0 tests.

- **The blocker is path handling.** Every script currently derives the project
  root as `Path(__file__).parent`, which breaks under a `src/` layout (`__file__`
  then points inside the package, not the repo root). Switch to a deliberate
  project-root strategy — CWD by default, overridable via a `--root` flag or
  `DN_PROJECT_ROOT` env var — and thread paths through the loaders. Phase 0's
  path injection already pre-pays part of this rework.
- Add `[project.scripts]` entry points in `pyproject.toml`; update the run
  commands in `architecture.md`.
- **NN relevance:** a package gives the trainer a clean import surface and a
  `dn train` home, but it is **not required** for the NN — the dense-array +
  `weights/{hash}.npy` design (Phases 1–2) is what actually enables it. That is
  why packaging is deferred rather than done first.

### How this makes the future NN commit easy

The NN trainer (separate, future) produces a dense weight array per school/run.
It hashes and drops each array into `weights/{hash}.npy` using the same
`weights_hash` / `persist_weights` helpers, then runs `analyse.py` pointed at
that weight set. No change to the metric computation, the output naming, or the
regression — the array *is* the learned linear layer.

## Critical files

- `analyse.py` — `:27` BINS, `:35-37` config load, `:49`/`:311` output names,
  `:91-110` weights+metric, `:207-213` workbook sheets, `:240-326` report.
- `national_pivot_distributions.py:85-87` — defines the `{class}_{bin:02d}`
  column convention the dense vector must align to.
- `architecture.md`, `.agents/skills/run-profile-analysis.md` — naming/config docs.
- New (Phase 0): `tests/` (`conftest.py`, `fixtures/…`, `test_characterization.py`,
  `test_analysis.py`, `test_metrics.py`); pytest in `pyproject.toml`.
- New (Phase 1–2): `metrics.py`, `metric_weights.yml`, `weights/` (generated).
- New (Phase 3, deferred): `src/dear_niece/`, `[project.scripts]` in `pyproject.toml`.

## Verification

1. **Test suite green:** `uv run pytest` passes — the Phase 0 characterization
   golden master and unit tests, then the Phase 1 `metrics.py` tests.
2. **Same input → same output (the headline guarantee):** the characterization
   test, captured from the *current* code, still passes after the shallow
   restructure (Phase 0) and after the weights refactor with default weights
   (Phases 1–2) — pinning **values**, tolerant of the hash-suffixed filename and
   the additive `metric_weights` sheet.
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
