# Methodology

## Why distributions predict thresholds

Greek university admission thresholds (*βάσεις*) reflect supply and demand: a department
has a fixed number of places, and the threshold is the score of the last student admitted.
When the national student population performs better across the board — more students achieve
high marks — competition for every seat intensifies and thresholds rise.

The national grade distributions, published before the thresholds, capture exactly this
effect: they show, for each exam subject, what fraction of students landed in each score
bracket. A year where the high end of the Biology distribution is heavier than usual means
more students can plausibly compete for Biology-field programs, which pushes βάσεις upward.

The core question this pipeline answers is: **by how much?**

---

## Score bins

The Greek exams are graded on a 0–20 scale. The distribution data groups students into
score brackets defined by their lower bound:

| Bin label | Score range | Notes |
|---|---|---|
| `0` | 0 – 5 | Very low performance |
| `5` | 5 – 10 | Below average |
| `10` | 10 – 11 | Passing threshold |
| `11` | 11 – 12 | |
| `12` | 12 – 13 | |
| `13` | 13 – 14 | |
| `14` | 14 – 15 | |
| `15` | 15 – 16 | |
| `16` | 16 – 17 | |
| `17` | 17 – 18 | |
| `18` | 18 – 19 | High performance |
| `19` | 19 – 20 | Top performance |

Note that the bins become finer at the high end (each covering one mark unit rather than
five). This is because the high-score region is where university-competitive students sit —
small shifts there have a disproportionate effect on thresholds.

The column name in `distributions_wide.xlsx` is `{subject}_{bin:02d}`, so `lang_15` is the
percentage of students who scored between 15 and 16 in Greek Language.

---

## The high-end metric

### Purpose

The metric reduces the four per-subject distributions for a given year into a single scalar
that captures the *strength of the high-scoring tail*. A higher metric means more students
achieved top marks, implying stronger competition for university places and upward pressure
on βάσεις.

### Formula

$$
\text{metric}(y) = \sum_{s \in S} \sum_{b \in B_s} w_{s,b} \cdot p_{s,b,y}
$$

Where:
- $y$ is the year
- $S = \{\text{bio, phys, chem, lang}\}$ is the set of subjects
- $B_s$ is the set of bins defined for subject $s$ (see the weights table below)
- $w_{s,b}$ is the weight assigned to bin $b$ for subject $s$
- $p_{s,b,y}$ is the percentage of students in bin $b$ for subject $s$ in year $y$

The result is a dimensionless number (a weighted sum of percentages).

### The metric weights

The weights are **configuration, not code**. The global defaults live in
`metric_weights.yml` at the repo root, authored as a sparse `{subject: {bin: weight}}`
mapping (mirrored in code by `DEFAULT_WEIGHTS` in `metrics.py`):

```yaml
bio:  {18: 0.0, 19: 1.0}
chem: {18: 0.0, 19: 1.0}
lang: {14: 0.0, 15: 1.0, 16: 2.0, 17: 3.0, 18: 4.0, 19: 5.0}
phys: {16: 0.0, 17: 1.0, 18: 2.0, 19: 3.0}
```

Each entry is `bin_label: weight`. Weights are **real-valued** (floats accepted); the
integers shown are just the current defaults. **A weight of 0 marks the lower
observation boundary** for that subject: the bin is in scope and can be promoted to a
non-zero weight trivially, but currently contributes nothing to the metric. Bins below
the lowest key are not tracked at all.

`metrics.py` is the single owner of the weight logic. It materializes the sparse YAML
into a dense `float64` vector over the 48 `{subject}_{bin:02d}` columns, computes the
metric as a name-aligned dot product (so column order in the distribution frame cannot
silently misalign it), and hashes the weight set. That hash suffixes the output
filenames and keys the content-addressable `weights/` store. A profile can override the
weights per-subject — see {doc}`profiles`.

### Per-subject rationale

```{mermaid}
flowchart LR
    A["distributions_wide.xlsx"] --> B["get_class_distribution\nfor year Y"]
    B --> C["Biology\nbins 18–19"]
    B --> D["Chemistry\nbins 18–19"]
    B --> E["Physics\nbins 16–19"]
    B --> F["Language\nbins 14–19"]
    C --> G["× {18:0, 19:1}"]
    D --> H["× {18:0, 19:1}"]
    E --> I["× {16:0, 17:1, 18:2, 19:3}"]
    F --> J["× {14:0, 15:1, 16:2, 17:3, 18:4, 19:5}"]
    G --> K["metric(Y)"]
    H --> K
    I --> K
    J --> K
```

**Biology and Chemistry** — only bin 19 (scores 19–20) receives a non-zero weight.
These subjects tend to follow a bimodal distribution: most students cluster at middling
scores, and a small elite reaches the very top. Only that top bracket shifts enough
year-to-year to reliably signal changes in competitive pressure. Bin 18 is included
with weight 0 to mark the observation threshold without inflating the metric with a
noisier bin.

**Physics** — the relevant tail starts at bin 17, with bin 19 weighted three times as
much as bin 17. Physics scores are harder to achieve at the top, and each additional
mark unit in the 17–20 range represents a larger difficulty jump, so a linear weight
ramp reflects increasing marginal significance.

**Greek Language** — the competitive range is wider (bins 15–19) and gets a steeper
weight ramp (1–5). Language scores are more normally distributed than the sciences,
meaning more students land in the 15–18 range; those bins genuinely signal competitive
pressure, not just a noise floor. Bin 14 is the zero-weight threshold.

### Worked example

Suppose in year *Y* the percentages for Language are:

| Bin | Score range | % of students | Weight | Contribution |
|---|---|---|---|---|
| 14 | 14–15 | 8.1 | 0 | 0.0 |
| 15 | 15–16 | 7.4 | 1 | 7.4 |
| 16 | 16–17 | 6.3 | 2 | 12.6 |
| 17 | 17–18 | 4.9 | 3 | 14.7 |
| 18 | 18–19 | 2.8 | 4 | 11.2 |
| 19 | 19–20 | 0.8 | 5 | 4.0 |

Language contribution for year *Y*: **49.9**. The other three subjects contribute their
own weighted sums, and the four contributions are summed to produce the total metric.

---

## Year-over-year metric shift

After computing the metric for each year, the year-over-year shift is:

$$
\Delta\text{metric}(y) = \text{metric}(y) - \text{metric}(y - 1)
$$

A positive $\Delta\text{metric}$ means the high-scoring tail grew — more students
performed well — which is expected to push βάσεις upward. A negative value means the
tail shrank (a harder year, or a year where fewer students aced the exams), which
historically correlates with falling thresholds.

---

## Per-school regression

### Setup

For each school in the profile, the pipeline fits:

$$
\Delta\text{baseis}(y) = a \cdot \Delta\text{metric}(y) + b
$$

using ordinary least squares over all years where both quantities are known —
the *training years*. Typically, distributions arrive one year ahead of thresholds,
so the most recent distribution shift (the *prediction year*) falls outside the
training set.

```{mermaid}
flowchart TD
    A["metric(y) for all years"] --> B["diff ➜ Δmetric(y)"]
    C["entry score per school per year"] --> D["diff ➜ Δbaseis(school, y)"]
    B --> E["align on common years\n(both Δmetric and Δbaseis known)"]
    D --> E
    E --> F["lstsq per school\nΔbaseis = a·Δmetric + b"]
    F --> G["coefficients a, b\nand R² per school"]
    B --> H["latest Δmetric\n(prediction period)"]
    G --> I["predicted shift\n= a·Δmetric_latest + b"]
    H --> I
    C --> J["last known entry\nper school"]
    I --> K["predicted entry\n= last entry + predicted shift"]
    J --> K
    K --> L["predictions sheet\nin the analysis workbook"]
```

### Least squares with `numpy`

The design matrix for a school with $n$ training years is:

$$
\mathbf{A} =
\begin{bmatrix}
\Delta\text{metric}(y_1) & 1 \\
\Delta\text{metric}(y_2) & 1 \\
\vdots & \vdots \\
\Delta\text{metric}(y_n) & 1 \\
\end{bmatrix},
\quad
\mathbf{y} =
\begin{bmatrix}
\Delta\text{baseis}(y_1) \\
\Delta\text{baseis}(y_2) \\
\vdots \\
\Delta\text{baseis}(y_n) \\
\end{bmatrix}
$$

`numpy.linalg.lstsq(A, y)` returns the $[a, b]$ vector that minimises
$\|\mathbf{A}[a,b]^\top - \mathbf{y}\|^2$.

With $n = 2$ training points the system is exactly determined (2 equations, 2 unknowns)
and the fit passes through both points. With $n \geq 3$ it is a proper least-squares
regression.

### Prediction

Once $a$ and $b$ are known, the predicted threshold shift for year $y^*$ is:

$$
\hat{\Delta}\text{baseis}(y^*) = a \cdot \Delta\text{metric}(y^*) + b
$$

And the predicted entry score:

$$
\hat{\text{entry}}(y^*) = \text{entry}(y^* - 1) + \hat{\Delta}\text{baseis}(y^*)
$$

### Output columns in the `predictions` sheet

| Column | Description |
|---|---|
| `school_code` | 4-digit ministry code |
| `institution` | University abbreviation |
| `department` | Full department name |
| `a` | Slope of the fitted line |
| `b` | Intercept of the fitted line |
| `r2` | R² on the training set |
| `metric_shift (YEAR-PREV)` | The $\Delta\text{metric}$ used for prediction |
| `predicted_shift` | $\hat{\Delta}\text{baseis}$ |
| `entry_LASTYEAR` | Most recent known threshold |
| `predicted_entry_YEAR` | Forecast threshold |

---

## Limitations and interpretation

**Small training set.** With typically 2–4 training years per school, the regression
has almost no degrees of freedom. The coefficients $a$ and $b$ should be read as
descriptive summaries of the historical relationship, not statistically robust estimates.

**Extrapolation risk.** If the prediction-year $\Delta\text{metric}$ falls well outside
the range seen in the training years, the linear model extrapolates and predictions
become unreliable. Always compare `metric_shift (YEAR-PREV)` against the historical
values in the `high_end_metric` sheet before trusting the output.

**One predictor.** The model uses only $\Delta\text{metric}$ as a predictor. Real
threshold shifts also depend on the number of applicants, policy changes (new departments,
quota adjustments), and individual school factors not captured here.

---

## Modifying the metric

The weights are configuration. Edit `metric_weights.yml` (repo root) to change the
**global** default for every profile, or add a `metric_weights:` block to a profile's
`schools.yml` to override **just that profile** (per-subject replace — see
{doc}`profiles`). No Python code needs to change. Each distinct weight set produces a
distinct output `{hash}`, so changing weights never overwrites a previous run's output.

### Changing a weight

Increase a weight to give that bin more influence over the metric. For example, to make
Biology more sensitive to the 18–19 bracket:

```yaml
bio: {18: 1.0, 19: 3.0}
```

This triples the weight of the top bin and adds the 18–19 bin as a minor contributor.

### Extending the range of a subject

Add lower bins to capture a wider scoring tail. For Chemistry, to watch from bin 17:

```yaml
chem: {17: 0.0, 18: 1.0, 19: 2.0}
```

Bin 17 carries weight 0 (observation boundary only); bins 18 and 19 contribute 1× and 2×.

### Narrowing the range

Remove bins that add noise. If Physics bin 17 turns out to be uncorrelated with threshold
changes, drop it:

```yaml
phys: {16: 0.0, 18: 2.0, 19: 3.0}
```

### Weight-of-zero convention

A weight of 0 is intentional, not a placeholder for "not yet decided". It says:
*this bin is in scope — we watch it — but it does not currently drive the metric.*
Promoting it to a non-zero weight is a deliberate modelling decision, not a bug fix.

### After any change

Rerun the full pipeline from `analyse.py` onwards:

```bash
uv run python analyse.py --profile NAME
```

The `high_end_metric` sheet will show the recalculated metric and shifts; compare the
new values against the observed baseis shifts in `baseis_shifts` to assess whether the
modified weights improve the historical fit before trusting the new predictions.
