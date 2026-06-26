# Overview

## The problem

Greek university admissions are governed by a threshold score called *βάση* (plural: *βάσεις*).
Each year, after the national exams (*Πανελλαδικές*), the ministry publishes one entry threshold
per department: the lowest score admitted in the general track. A student who scores above the
threshold for their desired department is admitted.

These thresholds are not fixed. They shift every year — sometimes by hundreds of points — in
response to how the student population performed nationally. This creates a forecasting problem:
a student deciding which schools to target in May needs an estimate of where the thresholds will
land in August, before the results are announced.

## The key insight

The Ministry of Education publishes two datasets on different schedules:

| Dataset | What it contains | When it appears |
|---|---|---|
| **Student grade distributions** | For each subject, the percentage of students in each score bracket | Published in **May–June**, shortly after the exams |
| **Admission thresholds (βάσεις)** | The lowest score admitted to each department | Published in **August**, after placement |

Distributions arrive roughly two months before thresholds. If there is a measurable relationship
between how the distributions shifted and how the thresholds shifted in past years, that
relationship can be used to predict the upcoming thresholds from the freshly-published distributions.

## What this repository does

1. **Maintains a historical database** of βάσεις — one row per year per department, sourced from
   the ministry's annual Excel files.
2. **Tracks the national grade distributions** across four subjects: Biology, Physics, Chemistry,
   and Greek Language.
3. **Computes a scalar metric** (the *high-end metric*) that summarises the strength of the
   high-scoring tail of the distributions each year.
4. **Fits a per-school linear regression** that maps year-over-year shifts in the metric to
   year-over-year shifts in the βάση for that school.
5. **Generates predictions** for the upcoming year using the latest distribution shift.

The pipeline is designed for multiple users: shared national data is processed once, and each
person maintains a *profile* listing the schools they care about.

## Data sources

| File | Origin | Update cadence |
|---|---|---|
| `data/baseis-raw/gel-{YEAR}.xlsx` | Direct ministry download | Once per year, August |
| `data/distributions.xlsx` (sheet `data-StudentsDistribution`) | Manually collected from published exam statistics | Once per year, May–June |
