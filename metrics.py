"""Metric weights: config loading, dense materialization, the metric, and hashing.

Imported one-way by ``analyse.py`` (``analyse -> metrics``) to avoid an import
cycle. Weights are **real-valued (float)**. A weight set is *authored* as a
sparse YAML mapping ``{class: {bin: weight}}`` and *materialized* internally into
a dense ``float64`` vector over the 48 canonical ``{class}_{bin:02d}`` columns.
That canonical array is the basis for both the metric dot-product and the
content-addressable hash, so equivalent spellings behave identically.
"""

import hashlib
import pathlib

import numpy as np
import pandas as pd
import yaml

ROOTDIR = pathlib.Path(__file__).parent
METRIC_WEIGHTS_YML = ROOTDIR / 'metric_weights.yml'
WEIGHTS_DIR = ROOTDIR / 'weights'  # content-addressable store: {hash}.npy + {hash}.yml

CLASSES = ['bio', 'phys', 'chem', 'lang']
BINS = [0, 5, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19]

# Default high-end metric weights (global). Mirrored by ``metric_weights.yml``.
# Real-valued: the original integer metric is spelled as floats here so the
# loaded config and this in-code default share one type.
DEFAULT_WEIGHTS = {
    'bio':  {18: 0.0, 19: 1.0},
    'chem': {18: 0.0, 19: 1.0},
    'lang': {14: 0.0, 15: 1.0, 16: 2.0, 17: 3.0, 18: 4.0, 19: 5.0},
    'phys': {16: 0.0, 17: 1.0, 18: 2.0, 19: 3.0},
}


def _col_names():
    """The 48 canonical column names in fixed ``CLASSES`` x ``BINS`` order."""
    return [f'{cls}_{b:02d}' for cls in CLASSES for b in BINS]


def _validate(weights):
    """Reject unknown classes/bins, non-numeric weights, and missing classes with a clear error."""
    for cls, mapping in weights.items():
        if cls not in CLASSES:
            raise ValueError(f"unknown class {cls!r} in weights; expected one of {CLASSES}")
        for b, w in mapping.items():
            if b not in BINS:
                raise ValueError(f"unknown bin {b!r} for class {cls!r}; expected one of {BINS}")
            if isinstance(w, bool) or not isinstance(w, (int, float)):
                raise ValueError(f"weight for {cls}_{b:02d} must be numeric, got {w!r}")
    for cls in CLASSES:
        if cls not in weights:
            raise ValueError(f"class {cls!r} missing from weights; all classes must be present: {CLASSES}")


def load_weights(profile_cfg, default_path=METRIC_WEIGHTS_YML):
    """Load the global default weights, then overlay the profile's override.

    ``profile_cfg`` is the parsed ``schools.yml`` dict. An optional
    ``metric_weights:`` block overrides **per class**: a named class fully
    replaces the global mapping for that class; unnamed classes fall back to the
    global default. Validates membership and numeric weights before returning.
    """
    loaded = yaml.safe_load(pathlib.Path(default_path).read_text())
    weights = {cls: dict(mapping) for cls, mapping in loaded.items()}
    override = (profile_cfg or {}).get('metric_weights') or {}
    for cls, mapping in override.items():
        weights[cls] = dict(mapping)  # per-class replace
    _validate(weights)
    return weights


def weight_vector(weights):
    """Sparse weights -> name-indexed ``float64`` Series over the 48 canonical cols.

    Name-indexed (not positional) so callers align by column *name* and are
    immune to column-order differences in the distribution frame. Listed bins
    overlay an implicit-0 fill.
    """
    s = pd.Series(0.0, index=_col_names(), dtype='float64')
    for cls, mapping in weights.items():
        for b, w in mapping.items():
            s[f'{cls}_{b:02d}'] = float(w)
    return s


def dense_weights(weights):
    """Sparse weights -> dense ``BINS`` x ``CLASSES`` ``float64`` table (readable form)."""
    df = pd.DataFrame(0.0, index=BINS, columns=CLASSES, dtype='float64')
    for cls, mapping in weights.items():
        for b, w in mapping.items():
            df.loc[b, cls] = float(w)
    df.index.name = 'bin'
    return df


def compute_metric(wide_df, weights):
    """Weighted high-end metric per year: ``sum_col(dist[col] * weight[col])``.

    Aligns by column name; a bin absent from ``wide_df`` counts as 0 (a
    percentage bin that never appeared is genuinely 0%). Returns a Series indexed
    by year.
    """
    wv = weight_vector(weights)
    aligned = wide_df.reindex(columns=wv.index, fill_value=0.0)
    return (aligned * wv).sum(axis=1)


def weights_hash(weights):
    """Representation-independent short hash of a weight set.

    Canonical ``float64`` array (fixed order) -> ``round(6)`` -> ``sha256`` ->
    first 6 hex chars. Any two spellings that yield the same dense weights hash
    identically. Built in Phase 1; consumed by the content-addressable store in
    Phase 2.
    """
    arr = np.ascontiguousarray(weight_vector(weights).to_numpy(dtype='float64'))
    arr = np.round(arr, 6) + 0.0  # + 0.0 collapses any -0.0 so it can't perturb the bytes
    return hashlib.sha256(arr.tobytes()).hexdigest()[:6]


def persist_weights(weights, weight_hash=None, weights_dir=WEIGHTS_DIR):
    """Persist a weight set to the content-addressable store; return its hash.

    Writes two files under ``weights_dir`` (created if needed), keyed by the
    weight hash:

    - ``{weight_hash}.npy`` — the canonical ``float64`` 48-vector (``weight_vector``
      order): the exact array ``weights_hash`` digests and the form the future
      NN emits/consumes, so reload -> rehash is stable.
    - ``{weight_hash}.yml`` — the sparse authored mapping, for human readability.

    The store is immutable per hash: existing files are left untouched. This is
    the drop-zone the future trainer writes into.
    """
    if weight_hash is None:
        weight_hash = weights_hash(weights)
    weights_dir = pathlib.Path(weights_dir)
    weights_dir.mkdir(parents=True, exist_ok=True)
    npy_path = weights_dir / f'{weight_hash}.npy'
    yml_path = weights_dir / f'{weight_hash}.yml'
    if not npy_path.exists():
        np.save(npy_path, weight_vector(weights).to_numpy(dtype='float64'))
    if not yml_path.exists():
        yml_path.write_text(yaml.safe_dump(weights, sort_keys=True), encoding='utf-8')
    return weight_hash
