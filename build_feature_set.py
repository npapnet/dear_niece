"""Export the per-school feature set to Excel for inspection / external modelling.

For every field-3 school and every year-over-year period, assemble one row of:

- the 48 national distribution diffs (``{class}_{bin:02d}``, ``metrics.col_names()``
  order) for that period — *global*, identical for every school in the period;
- ``entry_prev`` — the school's admission threshold for the earlier year (Y-1);
- ``entry`` — the threshold for the later year (Y), the absolute target;
- ``shift`` — ``entry - entry_prev``, the same target `analyse.py` regresses on.

This is a pure data-preparation step: it produces the feature table only and does
no modelling. The diff and weighting logic is reused from ``analyse``/``metrics``
so the columns match the rest of the pipeline exactly.

Run from the repo root:

    uv run python build_feature_set.py            # -> output/feature_set.xlsx

Inputs (regenerate first if missing):
    data/_pipeline_cache/distributions_wide.xlsx  (national_pivot_distributions.py)
    data/_pipeline_cache/baseis-master.csv        (national_load_baseis.py)
"""

import argparse
import pathlib

import pandas as pd

import metrics
from analyse import read_master, compute_bin_diffs

ROOTDIR = pathlib.Path(__file__).parent
CACHE_DIR = ROOTDIR / 'data' / '_pipeline_cache'
BASEIS_MASTER = CACHE_DIR / 'baseis-master.csv'
DISTRIBUTIONS_WIDE = CACHE_DIR / 'distributions_wide.xlsx'
OUTPUT_DIR = ROOTDIR / 'output'

ID_COLS = ['school_code', 'institution', 'department', 'period', 'year_prev', 'year']
TARGET_COLS = ['entry', 'shift']

# The 48 canonical distribution-diff columns in fixed CLASSES x BINS order — the
# same order the rest of the pipeline uses (metrics materialises weights over it).
DIFF_COLS = [f'{cls}_{b:02d}' for cls in metrics.CLASSES for b in metrics.BINS]


def load_distributions_wide(path):
    """Read distributions_wide, coerce the year index to int, sort ascending.

    Sorting matters: ``compute_bin_diffs`` diffs positionally, so the index must
    be in ascending year order for each diff to mean ``year - (year-1)``.
    """
    wide_df = pd.read_excel(path, sheet_name=0, index_col=0)
    wide_df.index = wide_df.index.astype(int)
    wide_df = wide_df.sort_index()
    years = wide_df.index.tolist()
    for i in range(1, len(years)):
        if years[i] != years[i - 1] + 1:
            raise ValueError(
                f"distributions_wide has a gap: year {years[i - 1] + 1} is missing "
                f"(found {years[i - 1]} followed by {years[i]}). A gap would mislabel "
                f"a multi-year diff as a one-year shift. Add the missing year(s) to "
                f"data/distributions.xlsx and re-run national_pivot_distributions.py."
            )
    return wide_df


def field3_entries(master):
    """Field-3 schools only: (year, 4-digit school_code, institution, department, entry)."""
    sc = master['school_code'].astype('Int64').astype(str).str.zfill(4)
    df = master[master['field_3']].copy()
    df['school_code'] = sc[df.index]
    return df[['year', 'school_code', 'institution', 'department', 'entry']]


def build_feature_set(wide_df, master):
    """Assemble the feature table: one row per (field-3 school, period).

    A row is kept only where both ``entry_prev`` (Y-1) and ``entry`` (Y) exist;
    rows with a missing threshold are dropped, not imputed. Distribution-diff
    cells that are missing in the source stay blank (a missing observation is not
    a real 0%).
    """
    feat_cols = DIFF_COLS
    diff_df = compute_bin_diffs(wide_df)  # index 'YYYY-YYYY', one row per period

    f3 = field3_entries(master)
    entry_wide = f3.pivot_table(index='year', columns='school_code', values='entry', aggfunc='max')
    info = (
        f3.sort_values('year')
        .groupby('school_code')
        .agg(institution=('institution', 'last'), department=('department', 'last'))
    )

    records = []
    for period in diff_df.index:
        year_to, year_from = (int(p) for p in period.split('-'))
        if year_from not in entry_wide.index or year_to not in entry_wide.index:
            continue
        diff_row = diff_df.loc[period].reindex(feat_cols)

        for school in entry_wide.columns:
            entry_prev = entry_wide.loc[year_from, school]
            entry_curr = entry_wide.loc[year_to, school]
            if pd.isna(entry_prev) or pd.isna(entry_curr):
                continue

            rec = {
                'school_code': school,
                'institution': info.loc[school, 'institution'] if school in info.index else '',
                'department': info.loc[school, 'department'] if school in info.index else '',
                'period': period,
                'year_prev': year_from,
                'year': year_to,
            }
            rec.update({c: diff_row[c] for c in feat_cols})
            rec['entry_prev'] = float(entry_prev)
            rec['entry'] = float(entry_curr)
            rec['shift'] = float(entry_curr - entry_prev)
            records.append(rec)

    columns = ID_COLS + feat_cols + ['entry_prev'] + TARGET_COLS
    return pd.DataFrame(records, columns=columns).sort_values(['period', 'school_code']).reset_index(drop=True)


def main(argv=None, *, baseis_master=BASEIS_MASTER, distributions_wide=DISTRIBUTIONS_WIDE,
         output_dir=OUTPUT_DIR):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--output', type=pathlib.Path, default=None,
                        help='Output .xlsx path (default: output/feature_set.xlsx)')
    args = parser.parse_args(argv)

    for cache_file in (baseis_master, distributions_wide):
        if not pathlib.Path(cache_file).exists():
            hint = ('national_load_baseis.py' if 'baseis' in pathlib.Path(cache_file).name
                    else 'national_pivot_distributions.py')
            raise FileNotFoundError(f"{pathlib.Path(cache_file).name} not found — run {hint} first")

    wide_df = load_distributions_wide(distributions_wide)
    master = read_master(baseis_master)
    df = build_feature_set(wide_df, master)

    out_path = args.output or (pathlib.Path(output_dir) / 'feature_set.xlsx')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(out_path, sheet_name='feature_set', index=False)

    n_features = len(DIFF_COLS) + 1  # 48 diffs + entry_prev
    print(f'Rows        : {len(df)}')
    print(f'Schools     : {df["school_code"].nunique()} field-3 schools')
    print(f'Periods     : {sorted(df["period"].unique())}')
    print(f'Features    : {n_features} (48 distribution diffs + entry_prev)')
    print(f'Targets     : entry (absolute Y), shift (Y - (Y-1))')
    print(f'Saved       : {out_path}')


if __name__ == '__main__':
    main()
