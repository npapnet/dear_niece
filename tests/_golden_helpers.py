"""Shared logic for the end-to-end golden-report test and its regen script.

Builds the synthetic cache, runs the full `analyse.main()` path for the
committed `profiles/_golden` profile, and returns the produced report text.
"""

import shutil
from pathlib import Path

import analyse
from conftest import make_wide_df, make_master_df, SYNTH_PREDICTION_YEAR

REPO = Path(__file__).resolve().parents[1]
GOLDEN_PROFILE = REPO / 'profiles' / '_golden'
EXPECTED = GOLDEN_PROFILE / f'expected-report-{SYNTH_PREDICTION_YEAR}.md'


def normalise(text: str) -> str:
    """Drop the volatile `_Generated:` date line so comparisons are stable."""
    return '\n'.join(
        '' if line.startswith('_Generated:') else line
        for line in text.splitlines()
    )


def produce_report(work_dir) -> str:
    """Run the synthetic pipeline under `work_dir` and return the report text."""
    work_dir = Path(work_dir)
    cache = work_dir / 'cache'
    cache.mkdir(parents=True, exist_ok=True)
    wide_path = cache / 'distributions_wide.xlsx'
    master_path = cache / 'baseis-master.csv'
    make_wide_df().to_excel(wide_path)
    make_master_df().to_csv(master_path, index=False, encoding='utf-8-sig')

    profiles_dir = work_dir / 'profiles'
    (profiles_dir / '_golden').mkdir(parents=True, exist_ok=True)
    shutil.copy(GOLDEN_PROFILE / 'schools.yml', profiles_dir / '_golden' / 'schools.yml')

    analyse.main(
        ['--profile', '_golden'],
        baseis_master=master_path,
        distributions_wide=wide_path,
        profiles_dir=profiles_dir,
    )
    report = profiles_dir / '_golden' / f'report-{SYNTH_PREDICTION_YEAR}.md'
    return report.read_text(encoding='utf-8')
