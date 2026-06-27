"""Unit tests for metrics.py: config loading, materialization, metric, hashing.

Expected values are hand-computed independently of the production code, so these
assert correctness rather than "same as before".
"""

import numpy as np
import pandas as pd
import pytest

import metrics
from metrics import (
    CLASSES,
    BINS,
    DEFAULT_WEIGHTS,
    load_weights,
    weight_vector,
    dense_weights,
    compute_metric,
    weights_hash,
)
from analyse import compute_metric_df
from conftest import make_wide_df


# --- config loading / no-drift ------------------------------------------------

def test_yaml_no_drift():
    """metric_weights.yml parses to exactly DEFAULT_WEIGHTS (no global override)."""
    assert load_weights({}) == DEFAULT_WEIGHTS


def test_load_weights_no_metric_block():
    """A schools.yml without a metric_weights block falls back to the default."""
    assert load_weights({'schools': ['0302'], 'prediction_year': 2025}) == DEFAULT_WEIGHTS


def test_load_weights_override_is_per_class():
    cfg = {'metric_weights': {'phys': {18: 0.7, 19: 1.3}}}
    w = load_weights(cfg)
    assert w['phys'] == {18: 0.7, 19: 1.3}          # phys fully replaced
    assert w['bio'] == DEFAULT_WEIGHTS['bio']        # unnamed classes unchanged
    assert w['lang'] == DEFAULT_WEIGHTS['lang']


def test_load_weights_rejects_unknown_class():
    with pytest.raises(ValueError, match='unknown class'):
        load_weights({'metric_weights': {'nope': {19: 1.0}}})


def test_load_weights_rejects_unknown_bin():
    with pytest.raises(ValueError, match='unknown bin'):
        load_weights({'metric_weights': {'bio': {99: 1.0}}})


def test_load_weights_rejects_non_numeric():
    with pytest.raises(ValueError, match='numeric'):
        load_weights({'metric_weights': {'bio': {19: 'x'}}})


# --- dense materialization ----------------------------------------------------

def test_weight_vector_names_and_fill():
    wv = weight_vector({'phys': {17: 1.0, 19: 3.0}})
    assert list(wv.index) == [f'{c}_{b:02d}' for c in CLASSES for b in BINS]
    assert wv['phys_17'] == 1.0
    assert wv['phys_19'] == 3.0
    assert wv['phys_18'] == 0.0      # implicit-0 fill for a listed class
    assert wv['bio_19'] == 0.0       # implicit-0 fill for an absent class
    assert wv.dtype == np.float64


def test_dense_weights_shape_and_values():
    d = dense_weights(DEFAULT_WEIGHTS)
    assert list(d.columns) == CLASSES
    assert list(d.index) == BINS
    assert d.index.name == 'bin'
    assert d.loc[19, 'lang'] == 5.0
    assert d.loc[0, 'bio'] == 0.0    # unweighted bin


# --- compute_metric -----------------------------------------------------------

def test_compute_metric_hand_value():
    cols = [f'{c}_{b:02d}' for c in CLASSES for b in BINS]
    df = pd.DataFrame(0.0, index=[2020], columns=cols)
    df.loc[2020, 'phys_17'] = 2.0
    df.loc[2020, 'phys_19'] = 1.0
    m = compute_metric(df, {'phys': {17: 1.0, 19: 3.0}})
    assert m.loc[2020] == 2.0 * 1.0 + 1.0 * 3.0      # 5.0


def test_compute_metric_column_order_independent():
    """Shuffled distribution columns -> identical metric (name alignment)."""
    df = make_wide_df()
    shuffled = df[list(reversed(df.columns))]
    pd.testing.assert_series_equal(
        compute_metric(df, DEFAULT_WEIGHTS),
        compute_metric(shuffled, DEFAULT_WEIGHTS),
    )


def test_compute_metric_matches_compute_metric_df():
    """The dense metric equals analyse.compute_metric_df's 'metric' column."""
    df = make_wide_df()
    direct = compute_metric(df, DEFAULT_WEIGHTS).round(2)
    via_df = compute_metric_df(df, DEFAULT_WEIGHTS)['metric']
    pd.testing.assert_series_equal(direct, via_df, check_names=False)


# --- weights_hash -------------------------------------------------------------

def test_weights_hash_stable():
    assert weights_hash(DEFAULT_WEIGHTS) == weights_hash(DEFAULT_WEIGHTS)


def test_weights_hash_representation_independent():
    """Key order and int-vs-float spelling don't change the hash."""
    a = {'phys': {17: 1, 19: 3}}                  # ints, this order
    b = {'phys': {19: 3.0, 17: 1.0}}              # floats, reversed
    assert weights_hash(a) == weights_hash(b)


def test_weights_hash_changes_with_weights():
    base = weights_hash(DEFAULT_WEIGHTS)
    changed = weights_hash({**DEFAULT_WEIGHTS, 'phys': {19: 9.0}})
    assert base != changed


def test_weights_hash_format():
    h = weights_hash(DEFAULT_WEIGHTS)
    assert len(h) == 6
    assert all(c in '0123456789abcdef' for c in h)


# --- persist_weights (content-addressable store) ------------------------------

def test_persist_weights_writes_both_forms(tmp_path):
    import yaml
    h = metrics.persist_weights(DEFAULT_WEIGHTS, weights_dir=tmp_path)
    assert h == weights_hash(DEFAULT_WEIGHTS)

    npy, yml = tmp_path / f'{h}.npy', tmp_path / f'{h}.yml'
    assert npy.exists() and yml.exists()

    # .npy is the canonical vector and reload -> rehash is stable
    arr = np.load(npy)
    np.testing.assert_array_equal(
        arr, weight_vector(DEFAULT_WEIGHTS).to_numpy(dtype='float64')
    )
    # .yml sidecar round-trips to the authored mapping
    assert yaml.safe_load(yml.read_text()) == DEFAULT_WEIGHTS


def test_persist_weights_is_immutable_per_hash(tmp_path):
    h = metrics.persist_weights(DEFAULT_WEIGHTS, weights_dir=tmp_path)
    mtime = (tmp_path / f'{h}.npy').stat().st_mtime_ns
    h2 = metrics.persist_weights(DEFAULT_WEIGHTS, weights_dir=tmp_path)
    assert h2 == h
    assert (tmp_path / f'{h}.npy').stat().st_mtime_ns == mtime  # not rewritten
