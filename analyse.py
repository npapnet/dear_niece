#%%
"""
High-end metric and baseis shift analysis with least-squares prediction.

For each subject and year, compute the weighted high-end metric, then use
year-over-year metric shifts as the independent variable in a per-school
least-squares regression against observed baseis shifts. The most recent
metric shift (distributions typically available one year ahead of baseis)
is used to predict the upcoming admission threshold change.
"""

import argparse
import yaml
import pandas as pd
import numpy as np
import pathlib

# %%
ROOTDIR = pathlib.Path(__file__).parent
DATADIR = ROOTDIR / 'data'
CACHE_DIR = DATADIR / '_pipeline_cache'
BASEIS_MASTER = CACHE_DIR / 'baseis-master.csv'
DISTRIBUTIONS_WIDE = CACHE_DIR / 'distributions_wide.xlsx'

CLASSES = ['bio', 'phys', 'chem', 'lang']
BINS = [0, 5, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19]

# %%
parser = argparse.ArgumentParser()
parser.add_argument('--profile', required=True)
args = parser.parse_args()

profile_dir = ROOTDIR / 'profiles' / args.profile
_profile_cfg = yaml.safe_load((profile_dir / 'schools.yml').read_text())
schools = _profile_cfg['schools']
prediction_year = int(_profile_cfg['prediction_year'])

for _cache_file in (BASEIS_MASTER, DISTRIBUTIONS_WIDE):
    if not _cache_file.exists():
        _hint = 'national_load_baseis.py' if 'baseis' in _cache_file.name else 'national_pivot_distributions.py'
        raise FileNotFoundError(f"{_cache_file.name} not found — run {_hint} first")

master = pd.read_csv(BASEIS_MASTER, encoding='utf-8-sig')
_sc = master['school_code'].astype('Int64').astype(str).str.zfill(4)
baseis_df = master.loc[_sc.isin(schools), ['year', 'school_code', 'institution', 'department', 'entry']].copy()
baseis_df['school_code'] = _sc[baseis_df.index]
baseis_df = baseis_df[baseis_df['year'] <= prediction_year - 1]
analysis_out = profile_dir / f'analysis-{prediction_year}.xlsx'
profile_dir.mkdir(parents=True, exist_ok=True)

# %%
wide_df = pd.read_excel(DISTRIBUTIONS_WIDE, sheet_name=0, index_col=0)
wide_df.index = wide_df.index.astype(int)
wide_df = wide_df[wide_df.index <= prediction_year]

if prediction_year not in wide_df.index:
    raise ValueError(
        f"prediction_year={prediction_year} requires distributions data for that year, "
        f"but distributions_wide only covers up to {wide_df.index.max()}. "
        f"Add the {prediction_year} rows to data/distributions.xlsx and re-run national_pivot_distributions.py."
    )

print("Years:", wide_df.index.tolist())
print("Shape:", wide_df.shape)

# %%
def get_class_distribution(wide_df, year, class_name):
    """Return a Series indexed by bin number with the percentage for each bin."""
    cols = [f'{class_name}_{b:02d}' for b in BINS]
    return wide_df.loc[year, cols].rename(lambda c: int(c.split('_')[1]))


# %%
# --- Year-over-year differences (raw percentage shift per bin) ---
years = wide_df.index.tolist()

diffs = {}
for i in range(1, len(years)):
    label = f'{years[i]}-{years[i-1]}'
    diffs[label] = wide_df.iloc[i] - wide_df.iloc[i - 1]

diff_df = pd.DataFrame(diffs).T
diff_df.index.name = 'period'
print("\nYear-over-year percentage shifts (selected high bins):")
high_bins = [c for c in diff_df.columns if any(c.endswith(f'_{b:02d}') for b in [17, 18, 19])]
print(diff_df[high_bins].round(2).to_string())

# %%
# --- Weighted high-end metric ---
METRIC_WEIGHTS = {
    'bio':  {18: 0, 19: 1},
    'chem': {18: 0, 19: 1},
    'lang': {14: 0, 15: 1, 16: 2, 17: 3, 18: 4, 19: 5},
    'phys': {16: 0, 17: 1, 18: 2, 19: 3},
}

metric_records = []
for year in years:
    total = 0.0
    for cls, weights in METRIC_WEIGHTS.items():
        dist = get_class_distribution(wide_df, year, cls)
        for bin_label, weight in weights.items():
            total += dist[bin_label] * weight
    metric_records.append({'year': year, 'metric': round(total, 2)})

metric_df = pd.DataFrame(metric_records).set_index('year')
metric_df['metric_shift'] = metric_df['metric'].diff()
print("\nWeighted high-end metric by year:")
print(metric_df.to_string())

# %%
# --- Baseis data ---
print("\nAdmission thresholds (baseis):")
baseis_wide = baseis_df.pivot_table(index='year', columns='school_code', values='entry', aggfunc='max')
print(baseis_wide.to_string())

baseis_shift = baseis_wide.diff().dropna()
print("\nYear-over-year change in baseis:")
print(baseis_shift.to_string())

baseis_detail = (
    baseis_df.groupby(['year', 'school_code'])
    .agg(institution=('institution', 'first'),
         department=('department', 'first'),
         entry=('entry', 'max'))
    .reset_index()
    .sort_values(['year', 'school_code'])
)

# %%
# --- Least-squares regression: metric_shift → baseis_shift per school ---
#
# Training: years where both metric_shift and baseis_shift are available.
# Prediction: most recent metric_shift year (distributions are published one
# year ahead of baseis, so this is typically the upcoming unpublished year).
metric_shift_series = metric_df['metric_shift'].dropna()

common_years = metric_shift_series.index.intersection(baseis_shift.index)
X_train = metric_shift_series.loc[common_years].values
A_matrix = np.column_stack([X_train, np.ones_like(X_train)])

prediction_year = int(metric_shift_series.index.max())
x_pred = float(metric_shift_series.loc[prediction_year])
pred_label = f'{prediction_year}-{prediction_year - 1}'
last_baseis_year = int(baseis_wide.index.max())

print(f"\nTraining years: {common_years.tolist()}")
print(f"Prediction period: {pred_label}, metric_shift = {x_pred:.4f}")
print(f"Last known baseis year: {last_baseis_year}")

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
print("\nPredictions:")
print(prediction_df.to_string())

# %%
# --- Save results ---
with pd.ExcelWriter(analysis_out) as writer:
    metric_df.to_excel(writer, sheet_name='high_end_metric')
    diff_df.to_excel(writer, sheet_name='bin_diffs')
    baseis_wide.to_excel(writer, sheet_name='baseis')
    baseis_shift.to_excel(writer, sheet_name='baseis_shifts')
    baseis_detail.to_excel(writer, sheet_name='baseis_detail', index=False)
    prediction_df.to_excel(writer, sheet_name='predictions', index=False)

print(f"\nSaved: {analysis_out}")
