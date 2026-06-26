#%%
"""
Percentile-based analysis of student grade distributions.

For each subject and year, compute the cumulative distribution and find which
score bin corresponds to specified percentile thresholds (e.g. top 10%).
Then track year-over-year shifts in those percentile scores to project
how admission thresholds (baseis) are likely to move.
"""

import argparse
import yaml
import pandas as pd
import numpy as np
import pathlib

# %%
ROOTDIR = pathlib.Path(__file__).parent
DATADIR = ROOTDIR / 'data'
OUTDIR = ROOTDIR / 'output'
DISTRIBUTIONS_WIDE = OUTDIR / 'distributions_wide.xlsx'
BASEIS_XLSX = DATADIR / 'baseis.xlsx'
ANALYSIS_OUTPUT = OUTDIR / 'analysis.xlsx'

CLASSES = ['bio', 'phys', 'chem', 'lang']
BINS = [0, 5, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19]
PERCENTILES = [85, 90, 95]

# %%
parser = argparse.ArgumentParser()
parser.add_argument('--profile', default=None)
args = parser.parse_args()

if args.profile:
    profile_dir = ROOTDIR / 'profiles' / args.profile
    schools = yaml.safe_load((profile_dir / 'schools.yml').read_text())['schools']
    master = pd.read_csv(ROOTDIR / 'data' / 'baseis-master.csv', encoding='utf-8-sig')
    _sc = master['school_code'].astype('Int64').astype(str).str.zfill(4)
    baseis_df = master.loc[_sc.isin(schools), ['year', 'school_code', 'entry']].copy()
    baseis_df['school_code'] = _sc[baseis_df.index]
    baseis_col = 'school_code'
    analysis_out = profile_dir / 'analysis.xlsx'
    profile_dir.mkdir(parents=True, exist_ok=True)
else:
    baseis_df = pd.read_excel(BASEIS_XLSX, sheet_name='data-baseis')
    baseis_col = 'School'
    analysis_out = ANALYSIS_OUTPUT

# %%
wide_df = pd.read_excel(DISTRIBUTIONS_WIDE, sheet_name=0, index_col=0)
wide_df.index = wide_df.index.astype(int)
print("Years:", wide_df.index.tolist())
print("Shape:", wide_df.shape)

# %%
def get_class_distribution(wide_df, year, class_name):
    """Return a Series indexed by bin number with the percentage for each bin."""
    cols = [f'{class_name}_{b:02d}' for b in BINS]
    return wide_df.loc[year, cols].rename(lambda c: int(c.split('_')[1]))


def find_percentile_bin(distribution, percentile):
    """Return the bin label where the cumulative distribution first reaches `percentile`."""
    cumulative = distribution.cumsum()
    for bin_label, cum_val in cumulative.items():
        if cum_val >= percentile:
            return bin_label
    return BINS[-1]


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
# --- Percentile analysis ---
records = []
for year in years:
    for cls in CLASSES:
        dist = get_class_distribution(wide_df, year, cls)
        cumulative = dist.cumsum()
        for pct in PERCENTILES:
            bin_label = find_percentile_bin(dist, pct)
            records.append({
                'year': year,
                'class': cls,
                'percentile': pct,
                'score_bin': bin_label,
            })

percentile_df = pd.DataFrame(records)

# %%
# Wide table: rows=year, cols=(class, percentile)
pivot = percentile_df.pivot_table(
    index='year', columns=['class', 'percentile'], values='score_bin'
)
print("\nScore bin at each percentile, by year and subject:")
print(pivot.to_string())

# %%
# Year-over-year change in percentile score bins
shifts = pivot.diff().dropna()
shifts.index.name = 'from_prev_year'
print("\nYear-over-year shift in percentile score bin (positive = harder year):")
print(shifts.to_string())

# %%
# --- Weighted high-end metric (reproduces the manual calculation in wide_df-work.xlsx) ---
# Weights penalise lower bins less; higher bins count more toward the index.
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
baseis_wide = baseis_df.pivot_table(index='year', columns=baseis_col, values='entry', aggfunc='max')
print(baseis_wide.to_string())

baseis_shift = baseis_wide.diff().dropna()
print("\nYear-over-year change in baseis:")
print(baseis_shift.to_string())

# %%
# --- Save results ---
with pd.ExcelWriter(analysis_out) as writer:
    pivot.to_excel(writer, sheet_name='percentile_scores')
    shifts.to_excel(writer, sheet_name='percentile_shifts')
    metric_df.to_excel(writer, sheet_name='high_end_metric')
    diff_df.to_excel(writer, sheet_name='bin_diffs')
    baseis_wide.to_excel(writer, sheet_name='baseis')
    baseis_shift.to_excel(writer, sheet_name='baseis_shifts')

print(f"\nSaved → {analysis_out}")
