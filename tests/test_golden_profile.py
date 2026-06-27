"""End-to-end golden-report backup test (synthetic, committed, deterministic).

Runs the full `analyse.main()` path for the committed `profiles/_golden`
profile against synthetic data and diffs the produced report against the frozen
`expected-report-2025.md`. If this fails after an *intended* change, regenerate
with `uv run python tests/_regen_golden.py` (see profiles/_golden/README.md).
"""

from _golden_helpers import EXPECTED, normalise, produce_report


def test_golden_report_matches(tmp_path):
    produced = produce_report(tmp_path)
    expected = EXPECTED.read_text(encoding='utf-8')
    assert normalise(produced) == normalise(expected), (
        "Report changed. If intended, run: uv run python tests/_regen_golden.py"
    )
