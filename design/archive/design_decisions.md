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
