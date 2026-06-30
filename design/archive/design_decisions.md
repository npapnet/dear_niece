# Design decisions

Frozen rationale behind the data model and storage choices made during initial development. Superseded decisions should be updated here, not in `architecture.md`.

## Long format as master

One row per observation. Wide format is derived on-demand via `pivot_table`. This keeps the master append-only and year-agnostic — adding a new year never changes the schema.

## `school_code` as stable join key

Department names and institution abbreviations drift slightly across years. The 4-digit ministry code is stable and the correct key for cross-year joins.

## `field` as one-hot booleans

The raw field column contains strings like `'2/3'` or `'1/2/4'` indicating that a department accepts students from multiple scientific fields. Storing these as-is in CSV risks automatic date parsing by spreadsheet software (e.g. Excel reads `'1/2'` as 1 February). One-hot encoding into `field_1`…`field_4` avoids this, is type-safe, and makes field-based filtering trivial.

## Tiebreak columns dropped

The `ΚΡΙΤΗΡΙΑ ΙΣΟΒΑΘΜΙΑΣ` columns contain free-text tiebreak criteria strings (e.g. `'18,2 19,4 19,7 1 16,1'`). They carry no analytical value for threshold prediction and are discarded on load.

## Loader owns the format knowledge

All header-parsing logic lives in `national_load_baseis.py`. If the ministry changes the layout again, only that file needs updating.

## CSV vs Parquet for the master file

At the current scale (~500 rows/year, growing ~500/year), CSV is the right choice:

- Human-readable and inspectable without tooling.
- Openable directly in Excel for spot-checking.
- No extra dependency (pyarrow/fastparquet).

The `field` date-coercion risk — the main argument for parquet's type safety — is fully resolved by one-hot encoding.

**When to reconsider parquet**: if the dataset grows beyond ~10 years and downstream scripts start showing noticeable load times, or if the master is shared with other tools that already use pyarrow (e.g. a pandas pipeline that reads many files). At that point, switching is a one-line change in the loader and the query snippet above.

## `baseis.xlsx` kept as a hand-curated subset

It holds only the schools relevant to the analysis and is not auto-generated, so it can carry extra annotations (notes, flags) without being overwritten by the loader.

## Filename as authoritative year source in the baseis loader

`gel-YYYY.xlsx` is the contract: the year is read from the filename and passed explicitly into `load_baseis_raw`. `_extract_year` (title-cell regex) is retained only as a cross-check — a mismatch raises `AssertionError` immediately. Rationale: the title cell is ministry-authored free text whose format can change; the filename is under our control and already enforced by the `gel-*.xlsx` glob pattern. The cross-check catches the case where a file is saved under the wrong name.

## Consecutive distribution years are required; gaps are an error

`load_wide_df` rejects a `distributions_wide.xlsx` that has any gap in its year index (e.g. 2023 present, 2024 absent, 2025 present). Rationale: `.diff()` is purely positional — it computes `row[i] - row[i-1]` regardless of the year labels. A gap silently produces a diff that spans two calendar years but is labelled as a one-year shift, biasing both the metric and the regression. Forcing consecutive years keeps the arithmetic meaning of every diff unambiguous.

## Missing distribution bins are NaN, not zero

`get_wide_format` in `national_pivot_distributions.py` no longer passes `fill_value=0` to `pivot_table`. A bin/year combination absent from the source data becomes `NaN` rather than `0.0`. Rationale: a genuine zero percentage (no students scored in that bin) and a missing observation are semantically different. Imputing `0.0` made the weighted metric treat absent data as real evidence, silently biasing scores for subjects not administered in a given year.

## Automatic weight optimisation (and a neural network) evaluated and rejected

The `metric_weights.yml` weights are **hand-authored** and stay that way. A feature
branch (`feature/weight-optimisation`) explored learning them from data — a
per-school OLS weight optimiser, a global Ridge regression with interaction
terms, and a planned neural network — exporting the result back into the weight
store for `analyse.py` to consume. It was discarded. The reasons are structural,
not implementation detail, so they are recorded here to stop the idea being
re-attempted:

- **The data has almost no degrees of freedom in the distribution dimension.**
  The 48 distribution-diff features are *global* — identical for every school in
  a given year-over-year period. With only a handful of years, the entire
  training set spans just that handful of distinct points in 48-dimensional diff
  space; the only per-school variation is the prior-year entry mark. Fitting tens
  of weights (let alone a neural network) to so few distinct inputs is hopelessly
  under-determined and overfits. More model capacity makes this worse, not
  better.

- **The metric weights are not uniquely identifiable (scale-degeneracy).** In
  both `analyse.py` and the optimiser, the weight vector `W` enters only through
  a *scalar* metric, and each school then fits its own `shift ≈ a·metric + b`
  line. Scaling `W` by any positive constant rescales every school's `a`
  inversely and leaves all predictions — and therefore the loss — unchanged. The
  "optimal weights" are a ray, not a point: only the *shape* of `W` is meaningful,
  never its magnitude, so learned weights cannot be compared or trusted by value.

- **The hand-authored prior is the right tool and dominates.** The weights encode
  domain knowledge an optimiser cannot recover from a few points: admission
  thresholds for competitive (field-3) schools are set by the top of the grade
  distribution, so only high bins carry weight, increasing toward the top. This
  expert prior collapses 48 dimensions to one at zero fitting cost, leaving just
  two parameters per school to estimate — which is all the data can support.

Only a model that reduces to a 48-dim metric weight could ever feed `analyse.py`;
anything richer (interactions, `entry_prev`, non-linearity, a neural network)
changes the function class and cannot be projected back onto that representation.
Combined with the points above, the conclusion was to keep `analyse.py` on the
hand-authored metric alone and drop the ML branch entirely. If the question is
revisited, the binding constraint to solve first is data volume (more years, or a
different unit of observation), not model sophistication.
