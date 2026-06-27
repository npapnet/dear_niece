# Refactor: package + `dn` CLI (deferred future work)

> Design document / plan for the packaging refactor. This is **Phase 3** of the
> metric-weights refactor, extracted into its own spec because it is deferred to a
> separate commit *after* the weights work (Phases 0–2) has landed. See
> [`design/archive/refactor_metrics.md`](../archive/refactor_metrics.md)
> for Phases 0–2 and [`architecture.md`](../../architecture.md) for the surrounding
> pipeline.

## Status

Deferred. Phases 0–2 (testing foundation, config-loaded weights + `metrics.py`,
content-addressable weight store + hash-suffixed outputs) are complete. This phase
is the highest-risk change — a structural move — and is deliberately sequenced
**last**, so it happens *under* the Phase 0 tests rather than before them.

## Goal

Promote the already-importable modules into a `src/dear_niece/` package with
console subcommands (`dn load_baseis`, `dn pivot_distributions`,
`dn analyze --profile maria`, later `dn train`). Done **after** the weights work,
guarded by the Phase 0 tests.

## Plan

- **The blocker is path handling.** Every script currently derives the project
  root as `Path(__file__).parent`, which breaks under a `src/` layout (`__file__`
  then points inside the package, not the repo root). Switch to a deliberate
  project-root strategy — CWD by default, overridable via a `--root` flag or
  `DN_PROJECT_ROOT` env var — and thread paths through the loaders. Phase 0's
  path injection already pre-pays part of this rework.
- Add `[project.scripts]` entry points in `pyproject.toml`; update the run
  commands in [`architecture.md`](../../architecture.md).
- **NN relevance:** a package gives the trainer a clean import surface and a
  `dn train` home, but it is **not required** for the NN — the dense-array +
  `weights/{hash}.npy` design (Phases 1–2) is what actually enables it. That is
  why packaging is deferred rather than done first.

## Critical files

- `analyse.py`, `national_load_baseis.py`, `national_pivot_distributions.py`,
  `national_plot_distributions.py`, `metrics.py` — modules to relocate under
  `src/dear_niece/`; each currently uses `Path(__file__).parent` for the root.
- `pyproject.toml` — add `[project.scripts]` entry points.
- [`architecture.md`](../../architecture.md) — update the run commands and the
  directory layout once the package lands.

## New / changed (Phase 3)

- New: `src/dear_niece/` package.
- Changed: `[project.scripts]` in `pyproject.toml`; run commands in
  [`architecture.md`](../../architecture.md).
