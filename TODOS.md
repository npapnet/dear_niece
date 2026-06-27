**Agents should ignore this file - Unless explicitly instructed from the user**

- [ ] Create and md report in each profile. 

- [x] feat: add the year of prediction in the "schools.yml", so the analysis will take data up to that year and the previous one (probably the easier by subsetting). E.g. maria profile should make a prediction for 2025 (i.e. using distributions diff up to 2025-24 and bases diff up to 2024-2023), and Manou2026 for 2026 (distributions diff up to 2026-25 and bases diff up to 2025-24).
- [x] chore: when using national_load_bases.py the console should only show the name of year that is being processed, in the sense of a progress bar. 



# Metrics improvements 

- Alternative method to use the already established bin_diffs (make a note that this comes from the distribution_wide.xlsx)
- weights in the computation of high_end metric
- FEAT: analyse contains METRIC_WEIGHTS (=# --- Weighted high-end metric --- ) which converts the bins_diff into a single metric (in a sense this is a type of neural network that I could try to train for each individual school_code). In any case this is parameter that should be exposed outside of the code, so that it may be changed. 
     - FEAT: weights can be saved globally or with `schools.yml` also (or at least overriden)
     - maybe another approach (more intuitive and straightforward to compute -- array multiplication and sum) using a df with all the bins instead of a dictionary with only a few bins might be better (even though its mostly populated with zero values).
- to differentiate between measures, you need to add the weights in the analysis, suffix a hash which comes from the weights list. 

# Neural network training

In order to get better values for the weights of the high_end metric (or a better statistic/metric), a neural network could be trained to predict the next weights given the bin diffs per year, the school entry thresholds per year (normalised 20000->1) and compare them against the value of that year.

- prepare the data and the output
- choose architecture
- split the data into train/test
- train
- evaluate
- compare to other methods