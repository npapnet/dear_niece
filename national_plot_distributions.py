"""
Plot the complementary CDF of student mark distributions for the high-scoring tail.

For each subject, shows the percentage of students scoring AT OR ABOVE each
score threshold, across all available years. Reproduces the 'Final' sheet from
the original Bro-Maria.xlsx workbook.

Output: output/distributions_plot.png
"""

import pathlib
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd

# %%
ROOTDIR = pathlib.Path(__file__).parent
OUTDIR = ROOTDIR / 'output'
DISTRIBUTIONS_WIDE = ROOTDIR / 'data' / '_pipeline_cache' / 'distributions_wide.xlsx'
PLOT_OUTPUT = OUTDIR / 'distributions_plot.png'

CLASSES = ['bio', 'phys', 'chem', 'lang']
CLASS_LABELS = {
    'bio':  'Βιολογία',
    'phys': 'Φυσική',
    'chem': 'Χημεία',
    'lang': 'Γλώσσα',
}
ALL_BINS = [0, 5, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19]

# Lowest bin to include on the x-axis (mirrors the 'Final' Excel sheet)
PLOT_FROM_BIN = 16


def complementary_cdf(wide_row: pd.Series, class_name: str, from_bin: int) -> tuple[list, list]:
    """
    Return (thresholds, pct_at_or_above) for all bins >= from_bin.

    pct_at_or_above[i] = sum of percentages for all bins >= thresholds[i].
    This is P[score >= threshold], the complementary CDF evaluated at each threshold.
    """
    thresholds = [b for b in ALL_BINS if b >= from_bin]
    pct = []
    for t in thresholds:
        cols = [f'{class_name}_{b:02d}' for b in ALL_BINS if b >= t]
        pct.append(wide_row[cols].sum())
    return thresholds, pct


def _year_style(i: int, n: int, color) -> dict:
    """Return line style kwargs for year at index i out of n total years.

    All years keep their tab10 colour so they remain distinguishable.
    Last year: thick dashed — primary focus.
    Year before last: thick solid — comparison baseline.
    Older years: thin solid — background context.
    """
    if i == n - 1:
        return dict(color=color, linewidth=2.5, linestyle='--', markersize=6, zorder=3)
    if i == n - 2:
        return dict(color=color, linewidth=2.5, linestyle='-',  markersize=6, zorder=2)
    return dict(color=color, linewidth=1.0, linestyle='-', markersize=3, zorder=1)


def plot_distributions(wide_df: pd.DataFrame, from_bin: int = PLOT_FROM_BIN) -> plt.Figure:
    """
    4-subplot figure: one panel per subject, lines per year.
    Y-axis: % of students scoring at or above the x-axis threshold.
    The two most recent years are drawn thicker; the last year is also dashed.
    """
    years = wide_df.index.tolist()
    n = len(years)
    cmap = matplotlib.colormaps['tab10'].resampled(n)

    fig, axes = plt.subplots(2, 2, figsize=(12, 8), sharex=False, sharey=False)
    fig.suptitle('Student score distributions — proportion scoring at or above threshold',
                 fontsize=13, y=1.01)

    for ax, cls in zip(axes.flat, CLASSES):
        for i, year in enumerate(years):
            thresholds, pct = complementary_cdf(wide_df.loc[year], cls, from_bin)
            ax.plot(thresholds, pct, marker='o', label=str(year),
                    **_year_style(i, n, cmap(i)))

        ax.set_title(CLASS_LABELS[cls], fontsize=11)
        ax.set_xlabel('Score threshold')
        ax.set_ylabel('% students scoring ≥ threshold')
        ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.1f%%'))
        ax.set_xticks(thresholds)
        ax.set_xticklabels([f'≥{t}' for t in thresholds])
        ax.legend(title='Year', fontsize=8)
        ax.grid(True, alpha=0.3)

    fig.tight_layout()
    return fig


# %%
if __name__ == '__main__':
    if not DISTRIBUTIONS_WIDE.exists():
        raise FileNotFoundError(
            f"{DISTRIBUTIONS_WIDE} not found — run national_pivot_distributions.py first"
        )
    wide_df = pd.read_excel(DISTRIBUTIONS_WIDE, sheet_name=0, index_col=0)
    wide_df.index = wide_df.index.astype(int)
    print(f"Loaded distributions_wide: {wide_df.shape}, years={wide_df.index.tolist()}")

    fig = plot_distributions(wide_df)
    fig.savefig(PLOT_OUTPUT, dpi=150, bbox_inches='tight')
    print(f"Saved → {PLOT_OUTPUT}")
