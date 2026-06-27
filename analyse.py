#%%
"""
High-end metric and baseis shift analysis with least-squares prediction.

For each subject and year, compute the weighted high-end metric, then use
year-over-year metric shifts as the independent variable in a per-school
least-squares regression against observed baseis shifts. The most recent
metric shift (distributions typically available one year ahead of baseis)
is used to predict the upcoming admission threshold change.

The compute functions take their inputs as arguments (DataFrames) and are
free of file IO so they can be unit-tested; all reading/writing lives in
`main()`.
"""

import argparse
import datetime
import yaml
import pandas as pd
import numpy as np
import pathlib

import metrics
from metrics import CLASSES, BINS

# %%
ROOTDIR = pathlib.Path(__file__).parent
DATADIR = ROOTDIR / 'data'
CACHE_DIR = DATADIR / '_pipeline_cache'
BASEIS_MASTER = CACHE_DIR / 'baseis-master.csv'
DISTRIBUTIONS_WIDE = CACHE_DIR / 'distributions_wide.xlsx'

# Default weights live in metrics.py (mirrored by metric_weights.yml); aliased
# here so run_analysis's default and the tests/fixtures keep their old name.
METRIC_WEIGHTS = metrics.DEFAULT_WEIGHTS


# %%
def get_class_distribution(wide_df, year, class_name, bins=BINS):
    """Return a Series indexed by bin number with the percentage for each bin."""
    cols = [f'{class_name}_{b:02d}' for b in bins]
    return wide_df.loc[year, cols].rename(lambda c: int(c.split('_')[1]))


def compute_bin_diffs(wide_df):
    """Year-over-year raw percentage shift per bin. Index = 'YYYY-YYYY' periods."""
    years = wide_df.index.tolist()
    diffs = {}
    for i in range(1, len(years)):
        label = f'{years[i]}-{years[i - 1]}'
        diffs[label] = wide_df.iloc[i] - wide_df.iloc[i - 1]
    diff_df = pd.DataFrame(diffs).T
    diff_df.index.name = 'period'
    return diff_df


def compute_metric_df(wide_df, metric_weights=METRIC_WEIGHTS, bins=BINS):
    """Weighted high-end metric per year, plus its year-over-year shift.

    Delegates the weighting to ``metrics.compute_metric`` (name-aligned dense dot
    product); ``bins`` is accepted for signature compatibility but the canonical
    48-column set is owned by ``metrics``.
    """
    metric_df = metrics.compute_metric(wide_df, metric_weights).round(2).rename('metric').to_frame()
    metric_df.index.name = 'year'
    metric_df['metric_shift'] = metric_df['metric'].diff()
    return metric_df


def load_wide_df(path, prediction_year):
    """Read distributions_wide, coerce the year index, and clip to prediction_year."""
    wide_df = pd.read_excel(path, sheet_name=0, index_col=0)
    wide_df.index = wide_df.index.astype(int)
    wide_df = wide_df[wide_df.index <= prediction_year]
    if prediction_year not in wide_df.index:
        raise ValueError(
            f"prediction_year={prediction_year} requires distributions data for that year, "
            f"but distributions_wide only covers up to {wide_df.index.max()}. "
            f"Add the {prediction_year} rows to data/distributions.xlsx and re-run national_pivot_distributions.py."
        )
    if len(wide_df) < 2:
        raise ValueError(
            f"distributions_wide must contain at least 2 years of data to compute "
            f"year-over-year shifts, but only {len(wide_df)} year(s) found (up to {prediction_year})."
        )
    years = sorted(wide_df.index.tolist())
    for i in range(1, len(years)):
        if years[i] != years[i - 1] + 1:
            raise ValueError(
                f"distributions_wide has a gap: year {years[i - 1] + 1} is missing "
                f"(found {years[i - 1]} followed by {years[i]}). "
                f"Add the missing year(s) to data/distributions.xlsx and re-run "
                f"national_pivot_distributions.py."
            )
    return wide_df


def read_master(path):
    """Read the baseis master CSV (utf-8-sig for the Greek text)."""
    return pd.read_csv(path, encoding='utf-8-sig')


def load_baseis_df(master, schools, prediction_year):
    """Filter the master to the profile's schools and to years < prediction_year."""
    schools = [str(s).zfill(4) for s in schools]
    _sc = master['school_code'].astype('Int64').astype(str).str.zfill(4)
    baseis_df = master.loc[_sc.isin(schools), ['year', 'school_code', 'institution', 'department', 'entry']].copy()
    baseis_df['school_code'] = _sc[baseis_df.index]
    baseis_df = baseis_df[baseis_df['year'] <= prediction_year - 1]
    return baseis_df


def compute_baseis(baseis_df):
    """Return (baseis_wide, baseis_shift, baseis_detail)."""
    baseis_wide = baseis_df.pivot_table(index='year', columns='school_code', values='entry', aggfunc='max')
    baseis_shift = baseis_wide.diff().dropna(how='all')
    baseis_detail = (
        baseis_df.groupby(['year', 'school_code'])
        .agg(institution=('institution', 'first'),
             department=('department', 'first'),
             entry=('entry', 'max'))
        .reset_index()
        .sort_values(['year', 'school_code'])
    )
    return baseis_wide, baseis_shift, baseis_detail


def predict(metric_df, baseis_wide, baseis_shift, baseis_df, prediction_year):
    """Per-school least-squares regression of baseis_shift on metric_shift.

    Returns (prediction_df, pred_label, last_baseis_year).

    Training: years where both metric_shift and baseis_shift are available.
    Prediction: most recent metric_shift year (distributions are published one
    year ahead of baseis, so this is typically the upcoming unpublished year).
    """
    metric_shift_series = metric_df['metric_shift'].dropna()

    common_years = metric_shift_series.index.intersection(baseis_shift.index)
    X_train = metric_shift_series.loc[common_years].values
    A_matrix = np.column_stack([X_train, np.ones_like(X_train)])

    x_pred = float(metric_shift_series.loc[prediction_year])
    pred_label = f'{prediction_year}-{prediction_year - 1}'
    last_baseis_year = int(baseis_wide.index.max())

    school_info = (
        baseis_df[baseis_df['year'] == last_baseis_year]
        .groupby('school_code')
        .agg(institution=('institution', 'first'), department=('department', 'first'))
    )

    prediction_records = []
    for school in baseis_shift.columns:
        y_train = baseis_shift.loc[common_years, school].values

        if len(common_years) < 2 or np.all(np.isnan(y_train)):
            a, b, r2 = np.nan, np.nan, np.nan
        else:
            # Drop rows where y is NaN (school missing in some years)
            mask = ~np.isnan(y_train)
            A_fit = A_matrix[mask]
            y_fit = y_train[mask]
            if len(y_fit) < 2:
                a, b, r2 = np.nan, np.nan, np.nan
            else:
                coeffs, _, _, _ = np.linalg.lstsq(A_fit, y_fit, rcond=None)
                a, b = coeffs
                y_pred_train = A_fit @ coeffs
                ss_res = float(np.sum((y_fit - y_pred_train) ** 2))
                ss_tot = float(np.sum((y_fit - y_fit.mean()) ** 2))
                r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else np.nan

        predicted_shift = a * x_pred + b if not np.isnan(a) else np.nan
        last_entry = (
            baseis_wide.loc[last_baseis_year, school]
            if last_baseis_year in baseis_wide.index else np.nan
        )
        predicted_entry = last_entry + predicted_shift if not (np.isnan(last_entry) or np.isnan(predicted_shift)) else np.nan

        inst = school_info.loc[school, 'institution'] if school in school_info.index else ''
        dept = school_info.loc[school, 'department'] if school in school_info.index else ''

        prediction_records.append({
            'school_code': school,
            'institution': inst,
            'department': dept,
            'a': round(float(a), 4) if not np.isnan(a) else np.nan,
            'b': round(float(b), 4) if not np.isnan(b) else np.nan,
            'r2': round(float(r2), 4) if not np.isnan(r2) else np.nan,
            f'metric_shift ({pred_label})': round(x_pred, 4),
            'predicted_shift': round(float(predicted_shift), 2) if not np.isnan(predicted_shift) else np.nan,
            f'entry_{last_baseis_year}': last_entry,
            f'predicted_entry_{prediction_year}': round(float(predicted_entry), 2) if not np.isnan(predicted_entry) else np.nan,
        })

    prediction_df = pd.DataFrame(prediction_records)
    return prediction_df, pred_label, last_baseis_year


def run_analysis(wide_df, baseis_df, prediction_year, metric_weights=METRIC_WEIGHTS, bins=BINS):
    """Pure analysis core: DataFrames in, result DataFrames out (no file IO)."""
    diff_df = compute_bin_diffs(wide_df)
    metric_df = compute_metric_df(wide_df, metric_weights, bins)
    baseis_wide, baseis_shift, baseis_detail = compute_baseis(baseis_df)
    prediction_df, pred_label, last_baseis_year = predict(
        metric_df, baseis_wide, baseis_shift, baseis_df, prediction_year
    )
    return {
        'high_end_metric': metric_df,
        'metric_weights': metrics.dense_weights(metric_weights),
        'bin_diffs': diff_df,
        'baseis': baseis_wide,
        'baseis_shifts': baseis_shift,
        'baseis_detail': baseis_detail,
        'predictions': prediction_df,
        'pred_label': pred_label,
        'last_baseis_year': last_baseis_year,
    }


def write_workbook(results, path, weights_hash=None):
    """Write the analysis result sheets to an Excel workbook.

    When ``weights_hash`` is given it is stamped into cell A1 of the
    ``metric_weights`` sheet (the table then starts one row lower).
    """
    with pd.ExcelWriter(path) as writer:
        results['high_end_metric'].to_excel(writer, sheet_name='high_end_metric')
        _wt_startrow = 1 if weights_hash else 0
        results['metric_weights'].to_excel(writer, sheet_name='metric_weights', startrow=_wt_startrow)
        if weights_hash:
            writer.sheets['metric_weights'].cell(row=1, column=1, value=f'weights hash: {weights_hash}')
        results['bin_diffs'].to_excel(writer, sheet_name='bin_diffs')
        results['baseis'].to_excel(writer, sheet_name='baseis')
        results['baseis_shifts'].to_excel(writer, sheet_name='baseis_shifts')
        results['baseis_detail'].to_excel(writer, sheet_name='baseis_detail', index=False)
        results['predictions'].to_excel(writer, sheet_name='predictions', index=False)


# %%
# --- Markdown report ---

def _md_table(df: pd.DataFrame) -> str:
    """Render a DataFrame as a GitHub-flavoured markdown table."""
    def _fmt(v):
        if isinstance(v, float) and pd.isna(v):
            return ''
        if isinstance(v, float):
            return f'{v:.2f}'
        return str(v)

    headers = [str(df.index.name or '')] + [str(c) for c in df.columns]
    rows = [[str(idx)] + [_fmt(v) for v in row] for idx, row in zip(df.index, df.values)]
    widths = [max(len(h), max((len(r[i]) for r in rows), default=0)) for i, h in enumerate(headers)]

    def _row(cells):
        return '| ' + ' | '.join(c.ljust(w) for c, w in zip(cells, widths)) + ' |'

    sep = '|' + '|'.join('-' * (w + 2) for w in widths) + '|'
    return '\n'.join([_row(headers), sep] + [_row(r) for r in rows])


def build_report(
    profile: str,
    prediction_year: int,
    metric_weights: dict,
    classes: list[str],
    bins: list[int],
    diff_df: pd.DataFrame,
    pred_label: str,
    baseis_shift: pd.DataFrame,
    prediction_df: pd.DataFrame,
    last_baseis_year: int,
    weights_hash: str = None,
) -> str:
    """Return the full markdown report as a string."""

    # Weights table: rows = bins that carry any weight, cols = subjects
    weight_bins = sorted({b for w in metric_weights.values() for b in w})
    weights_table = pd.DataFrame(
        {cls: {b: metric_weights.get(cls, {}).get(b, '') for b in weight_bins} for cls in classes},
        index=weight_bins,
    )
    weights_table.index.name = 'bin'

    # Distribution diffs: one sub-table per period, rows = bins, cols = subjects
    def _diff_period_table(row: pd.Series) -> pd.DataFrame:
        df = pd.DataFrame(
            {cls: {b: row.get(f'{cls}_{b:02d}', float('nan')) for b in bins} for cls in classes},
            index=bins,
        )
        df.index.name = 'bin'
        return df

    # Predictions: reader-facing columns only (drop raw regression coefficients)
    pred_cols = [
        'school_code', 'institution', 'department',
        f'metric_shift ({pred_label})',
        'predicted_shift',
        f'entry_{last_baseis_year}',
        f'predicted_entry_{prediction_year}',
        'r2',
    ]
    pred_table = prediction_df[[c for c in pred_cols if c in prediction_df.columns]].set_index('school_code')

    lines = [
        f'# Analysis Report — {profile} — {prediction_year}',
        f'',
        f'_Generated: {datetime.date.today()}_',
    ]
    if weights_hash:
        lines += [f'_Weights hash: `{weights_hash}`_']
    lines += [
        f'',
        f'## Metric Weights',
        f'',
        _md_table(weights_table),
        f'',
        f'## Distribution Diffs',
        f'',
    ]
    for period in diff_df.index:
        suffix = ' ← prediction period' if period == pred_label else ''
        lines += [f'### {period}{suffix}', '', _md_table(_diff_period_table(diff_df.loc[period])), '']

    lines += [
        f'## Baseis Shifts',
        f'',
        _md_table(baseis_shift.rename_axis('year')),
        f'',
        f'## Predictions',
        f'',
        _md_table(pred_table),
        f'',
    ]
    return '\n'.join(lines)


# %%
def main(argv=None, *, baseis_master=BASEIS_MASTER, distributions_wide=DISTRIBUTIONS_WIDE,
         profiles_dir=ROOTDIR / 'profiles', weights_dir=metrics.WEIGHTS_DIR):
    parser = argparse.ArgumentParser()
    parser.add_argument('--profile', required=True)
    args = parser.parse_args(argv)

    profile_dir = profiles_dir / args.profile
    _profile_cfg = yaml.safe_load((profile_dir / 'schools.yml').read_text())
    schools = _profile_cfg['schools']
    prediction_year = int(_profile_cfg['prediction_year'])
    weights = metrics.load_weights(_profile_cfg)
    w_hash = metrics.persist_weights(weights, weights_dir=weights_dir)

    for _cache_file in (baseis_master, distributions_wide):
        if not pathlib.Path(_cache_file).exists():
            _hint = 'national_load_baseis.py' if 'baseis' in pathlib.Path(_cache_file).name else 'national_pivot_distributions.py'
            raise FileNotFoundError(f"{pathlib.Path(_cache_file).name} not found — run {_hint} first")

    master = read_master(baseis_master)
    baseis_df = load_baseis_df(master, schools, prediction_year)
    wide_df = load_wide_df(distributions_wide, prediction_year)

    print("Years:", wide_df.index.tolist())
    print("Shape:", wide_df.shape)

    results = run_analysis(wide_df, baseis_df, prediction_year, metric_weights=weights)

    print("\nWeighted high-end metric by year:")
    print(results['high_end_metric'].to_string())
    print("\nPredictions:")
    print(results['predictions'].to_string())

    print(f"\nWeights hash: {w_hash}  (stored under {pathlib.Path(weights_dir)})")

    profile_dir.mkdir(parents=True, exist_ok=True)
    analysis_out = profile_dir / f'analysis-{prediction_year}-{w_hash}.xlsx'
    write_workbook(results, analysis_out, weights_hash=w_hash)
    print(f"Saved: {analysis_out}")

    report_out = profile_dir / f'report-{prediction_year}-{w_hash}.md'
    report_out.write_text(
        build_report(
            profile=args.profile,
            prediction_year=prediction_year,
            metric_weights=weights,
            classes=CLASSES,
            bins=BINS,
            diff_df=results['bin_diffs'],
            pred_label=results['pred_label'],
            baseis_shift=results['baseis_shifts'],
            prediction_df=results['predictions'],
            last_baseis_year=results['last_baseis_year'],
            weights_hash=w_hash,
        ),
        encoding='utf-8',
    )
    print(f'Saved: {report_out}')


if __name__ == '__main__':
    main()
