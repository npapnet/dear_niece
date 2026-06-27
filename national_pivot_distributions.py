#%%
import numpy as np
import pathlib
import pandas as pd

#%%
ROOTDIR = pathlib.Path(__file__).parent
DATADIR = ROOTDIR / 'data'
OUTDIR = ROOTDIR / 'output'
STUDENT_DATA = DATADIR / 'distributions.xlsx'

CLASS_NAMES_DICT = {
    'Βιολογία': 'bio',
    'Φυσική':   'phys',
    'Χημεία':   'chem',
    'γλώσσα':   'lang',
}

DISTRIBUTIONS_WIDE = ROOTDIR / 'data' / '_pipeline_cache' / 'distributions_wide.xlsx'


# %%
def get_percentage_by_class_year(df, class_name, year):
    subset = df[(df['class'] == class_name) & (df['year'] == year)]
    return subset[['marks_bin_start', 'percentage']]


def massage_data_for_class_year(df, class_name, year):
    """Return marks_bin_start and cumulative percentage for the specified class and year."""
    subset = get_percentage_by_class_year(df, class_name, year)
    subset = subset[['marks_bin_start', 'percentage']]
    subset = subset.sort_values(by='marks_bin_start')
    subset['cumulative_percentage'] = subset['percentage'].cumsum()
    subset['cumulative_percentage'] = subset['cumulative_percentage'].shift(1).fillna(0)
    return subset


def get_wide_format(df):
    """Return a wide-format DataFrame with columns class_name_marks_bin_start and rows as year."""
    df['class_marks_bin'] = df.apply(lambda row: f"{row['class']}_{row['marks_bin_start']:02d}", axis=1)
    wide_df = df.pivot_table(index='year', columns='class_marks_bin', values='percentage')
    return wide_df


if __name__ == '__main__':
    df = pd.read_excel(STUDENT_DATA, sheet_name='data-StudentsDistribution')
    df.drop(columns=['Column1', 'excludde'], inplace=True)
    df.rename(columns={'Επίδοση': 'marks_bin', 'Πλήθος': 'count', 'Ποσοστό': 'percentage', 'Μαθημα ': 'class', 'Ετος': 'year'}, inplace=True)

    df['class'] = df['class'].replace(CLASS_NAMES_DICT)
    df['marks_bin_start'] = df['marks_bin'].str.split('-').str[0].astype(int)

    wide_df = get_wide_format(df)

    DISTRIBUTIONS_WIDE.parent.mkdir(exist_ok=True)
    wide_df.to_excel(DISTRIBUTIONS_WIDE, index=True)
    print(f"Saved → {DISTRIBUTIONS_WIDE}  {wide_df.shape}")
