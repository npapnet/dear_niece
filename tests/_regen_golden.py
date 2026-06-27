"""Regenerate profiles/_golden/expected-report-2025.md.

Run only when a change *intentionally* alters the report:

    uv run python tests/_regen_golden.py
"""

import pathlib
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))          # tests/ -> _golden_helpers, conftest
sys.path.insert(0, str(HERE.parent))   # repo root -> analyse

from _golden_helpers import EXPECTED, produce_report  # noqa: E402


def main():
    with tempfile.TemporaryDirectory() as work_dir:
        text = produce_report(work_dir)
    EXPECTED.write_text(text, encoding='utf-8')
    print(f'Wrote {EXPECTED}')


if __name__ == '__main__':
    main()
