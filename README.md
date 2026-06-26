# dear_niece

Predicting the admission mark threshold for Greek university departments (Biology focus) using historical student grade distributions.


## Data

### Student mark distributions

Per-class grade distributions (percentage of students in each score bin), for years 2022–2025.

- Source: `data/distributions.xlsx`, sheet `data-StudentsDistribution`
- 4 subjects: Biology (bio), Physics (phys), Chemistry (chem), Greek Language (lang)
- 12 score bins per subject per year: 0–4.9, 5–9.9, 10–10.9, 11–11.9, …, 19–20.0
- Data origin:
  - [2023 distributions](https://foititikanea.gr/statistika/2022/pinakes/8.php)
  - [2024 distributions](https://www.aeitei.gr/statistika-gel.php?year=2024)
  - [2025 distributions](https://www.aeitei.gr/statistika-gel.php?year=2025)

### University admission thresholds (βάσεις)

Minimum admission scores (on a 0–20,000 scale) per school and year.

- Source: `data/baseis-raw/gel-{YEAR}.xlsx` (raw ministry downloads), combined into `data/baseis-master.csv` by `load_baseis.py`
- Profile-specific subsets declared in `profiles/{name}/schools.yml`
- Data origin:
  - [2023 baseis](https://aeitei.gr/index.php?year=2023&pedio=3&likio_type=gh&order=2)
  - [2024 baseis](https://aeitei.gr/index.php?sist=&sys=&vasi=basi&year=2024&pedio=3&aeitei=&city=&likio_type=gh&cat=1&order=2)


## Pipeline

```mermaid
flowchart LR
    subgraph nat["National — once per year"]
        LB["national_load_baseis.py"]
        PD["national_pivot_distributions.py"]
        LB --> MASTER["baseis-master.csv"]
        PD --> WIDE["distributions_wide.xlsx"]
    end

    subgraph per["Per profile"]
        YML["profiles/name/\nschools.yml"] --> AN["analyse.py\n--profile name"]
        AN --> OUT["profiles/name/\nanalysis.xlsx"]
    end

    MASTER --> AN
    WIDE --> AN
```

| Script | Runs | Output |
|---|---|---|
| `national_load_baseis.py` | Once per year | `data/baseis-master.csv` |
| `national_pivot_distributions.py` | Once per year | `output/distributions_wide.xlsx` |
| `national_plot_distributions.py` | Optional | `output/distributions_plot.png` |
| `analyse.py --profile name` | Per profile per year | `profiles/name/analysis.xlsx` |

See [quickstart.md](quickstart.md) for the full workflow with download URLs.


## Methodology

### Done

Year-over-year difference in percentage per score bin — an arbitrary metric to detect whether student scores as a whole shifted up or down between years.

The high-end bins (score ≥ 18) drive admission threshold changes most strongly, so the metric weights them accordingly.

### In progress

For each subject and year:

1. Compute the cumulative grade distribution from the bins.
2. Find the score bin at the Xth percentile (e.g., the top 10% threshold).
3. Track how that percentile score shifts year over year.
4. Use the shift trend to estimate the 2025 admission threshold, assuming a strong correlation between the percentile score and the βάσεις.

### Todo

- Add 2025 βάσεις data to `data/baseis.xlsx` once published.
- Validate the percentile-shift model against the known 2022–2024 baseis.
- Explore regression of baseis ~ percentile_score across years and schools.


## Setup

```bash
uv sync
```
