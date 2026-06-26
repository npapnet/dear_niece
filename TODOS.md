**Agents should ignore this file - Unless explicitly instructed from the user**

- weights in the computation of high_end metric
- Alternative method to use the already established bin_diffs (make a note that this comes from the distribution_wide.xlsx)
- feat: add the year of prediction in the "schools.yml", so the analysis will take data up to that year and the previous one (probably the easier by subsetting).
- chore: when using national_load_bases.py the console should only show the name of year that is being processed, in the sense of a progress bar. 

- FEAT: analyse contains METRIC_WEIGHTS (=# --- Weighted high-end metric --- ) which converts the bins_diff into a single metric (in a sense this is a type of neural network that I could try to train for each individual school_code). In any case this is parameter that should be exposed outside of the code, so that it may be changed. 
