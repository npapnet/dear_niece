"""Synthetic fixtures for the analysis pipeline tests.

The data is hand-designed so that the metric, bin_diffs, and per-school
regression are independently computable (see comments below). Nothing here
depends on the real, gitignored pipeline cache.

Design (see tests for the worked arithmetic):

  distributions: all 48 bins are 0 except ``bio_19`` — and the default
  METRIC_WEIGHTS give ``bio_19`` weight 1 with every other bin weight 0 — so the
  weighted metric for a year equals that year's ``bio_19`` value.

      year : 2021 2022 2023 2024 2025
      bio_19 / metric :  10   12   15   19   24
      metric_shift    :  --    2    3    4    5

  baseis (entry, max per year): two schools whose year-over-year shift is an
  exact linear function of the metric_shift, so the regression is exact (r2=1):

      school 9001 : shift = 10 * metric_shift + 5   -> entries 1000/1025/1060/1105
      school 9002 : shift = 20 * metric_shift + 0   -> entries 2000/2040/2100/2180

  Prediction period 2025-2024 uses metric_shift = 5:
      9001 -> predicted_shift 55,  predicted_entry 1160
      9002 -> predicted_shift 100, predicted_entry 2280
"""

import pandas as pd
import pytest

from analyse import CLASSES, BINS, load_baseis_df

SYNTH_YEARS = [2021, 2022, 2023, 2024, 2025]
SYNTH_PREDICTION_YEAR = 2025
SYNTH_SCHOOLS = ["9001", "9002"]

_BIO19_BY_YEAR = {2021: 10.0, 2022: 12.0, 2023: 15.0, 2024: 19.0, 2025: 24.0}
_ENTRIES = {
    "9001": {2021: 1000.0, 2022: 1025.0, 2023: 1060.0, 2024: 1105.0},
    "9002": {2021: 2000.0, 2022: 2040.0, 2023: 2100.0, 2024: 2180.0},
}


def make_wide_df():
    """Synthetic distributions_wide: zeros everywhere except bio_19."""
    cols = [f'{cls}_{b:02d}' for cls in CLASSES for b in BINS]
    df = pd.DataFrame(0.0, index=list(SYNTH_YEARS), columns=cols)
    df.index.name = 'year'
    for year, value in _BIO19_BY_YEAR.items():
        df.loc[year, 'bio_19'] = value
    return df


def make_master_df():
    """Synthetic baseis master (long format), two schools."""
    rows = []
    for code, by_year in _ENTRIES.items():
        for year, entry in by_year.items():
            rows.append({
                'year': year,
                'school_code': int(code),
                'institution': 'TST',
                'department': f'Dept {code} (City)',
                'entry': entry,
            })
    return pd.DataFrame(rows)


@pytest.fixture
def wide_df():
    return make_wide_df()


@pytest.fixture
def master_df():
    return make_master_df()


@pytest.fixture
def baseis_df(master_df):
    return load_baseis_df(master_df, SYNTH_SCHOOLS, SYNTH_PREDICTION_YEAR)
