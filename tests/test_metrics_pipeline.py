"""Unit + integration tests for the metric/weights pipeline, on synthetic data.

Expected values are computed independently of the production code (see
conftest for the design), so these assert correctness, not merely "same as
before".
"""

import numpy as np
import pandas as pd
import pytest

from analyse import (
    CLASSES,
    BINS,
    compute_bin_diffs,
    compute_metric_df,
    run_analysis,
)
from conftest import make_wide_df, SYNTH_PREDICTION_YEAR


# --- metric / weights ---------------------------------------------------------

def test_compute_metric_df_default_weights(wide_df):
    """With default weights only bio_19 carries the signal -> metric == bio_19."""
    m = compute_metric_df(wide_df)
    assert m['metric'].tolist() == [10.0, 12.0, 15.0, 19.0, 24.0]
    # first shift is NaN, then the year-over-year differences
    shifts = m['metric_shift'].tolist()
    assert np.isnan(shifts[0])
    assert shifts[1:] == [2.0, 3.0, 4.0, 5.0]


def test_compute_metric_df_custom_weights():
    """Hand-checked weighting: total = sum(dist[bin] * weight) per year."""
    cols = [f'{cls}_{b:02d}' for cls in CLASSES for b in BINS]
    df = pd.DataFrame(0.0, index=[2020, 2021], columns=cols)
    df.loc[2020, 'phys_17'] = 2.0
    df.loc[2020, 'phys_19'] = 1.0
    df.loc[2021, 'phys_17'] = 4.0
    df.loc[2021, 'phys_19'] = 3.0

    weights = {'phys': {17: 1, 19: 3}}
    m = compute_metric_df(df, weights)

    assert m.loc[2020, 'metric'] == 5.0    # 2*1 + 1*3
    assert m.loc[2021, 'metric'] == 13.0   # 4*1 + 3*3
    assert m.loc[2021, 'metric_shift'] == 8.0


def test_compute_bin_diffs(wide_df):
    diff = compute_bin_diffs(wide_df)
    # periods are 'newer-older'
    assert diff.index.tolist() == ['2022-2021', '2023-2022', '2024-2023', '2025-2024']
    assert diff['bio_19'].tolist() == [2.0, 3.0, 4.0, 5.0]
    # every other column is unchanged year-over-year
    others = [c for c in diff.columns if c != 'bio_19']
    assert (diff[others] == 0.0).all().all()


# --- regression / predictions -------------------------------------------------

def test_run_analysis_predictions(wide_df, baseis_df):
    results = run_analysis(wide_df, baseis_df, SYNTH_PREDICTION_YEAR)
    preds = results['predictions'].set_index('school_code')

    pred_col = f'predicted_entry_{SYNTH_PREDICTION_YEAR}'
    shift_col = f'metric_shift ({results["pred_label"]})'

    assert results['pred_label'] == '2025-2024'
    assert results['last_baseis_year'] == 2024

    # school 9001: a=10, b=5, exact fit
    assert preds.loc['9001', 'a'] == 10.0
    assert preds.loc['9001', 'b'] == 5.0
    assert preds.loc['9001', 'r2'] == 1.0
    assert preds.loc['9001', shift_col] == 5.0
    assert preds.loc['9001', 'predicted_shift'] == 55.0
    assert preds.loc['9001', 'entry_2024'] == 1105.0
    assert preds.loc['9001', pred_col] == 1160.0

    # school 9002: a=20, b=0, exact fit
    assert preds.loc['9002', 'a'] == 20.0
    assert preds.loc['9002', 'b'] == 0.0
    assert preds.loc['9002', 'r2'] == 1.0
    assert preds.loc['9002', 'predicted_shift'] == 100.0
    assert preds.loc['9002', 'entry_2024'] == 2180.0
    assert preds.loc['9002', pred_col] == 2280.0


def test_run_analysis_result_keys(wide_df, baseis_df):
    results = run_analysis(wide_df, baseis_df, SYNTH_PREDICTION_YEAR)
    for key in ('high_end_metric', 'bin_diffs', 'baseis', 'baseis_shifts',
                'baseis_detail', 'predictions'):
        assert key in results
        assert isinstance(results[key], pd.DataFrame)


def test_load_wide_df_requires_prediction_year(tmp_path):
    """Asking for a year beyond the distributions data is a clear error."""
    from analyse import load_wide_df
    wide = make_wide_df()
    path = tmp_path / 'distributions_wide.xlsx'
    wide.to_excel(path)
    with pytest.raises(ValueError, match='requires distributions data'):
        load_wide_df(path, 2099)
