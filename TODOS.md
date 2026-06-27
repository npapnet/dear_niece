**Agents should ignore this file - Unless explicitly instructed from the user**


# Recent improvements

This section is for completed tasks which have not yet been thoroughly documented or reflected in the documentation.


# Backlog


## Generic 

This for generic tasks. 


## Metrics improvements 

- [ ]Alternative method to use the already established bin_diffs (make a note that this comes from the distribution_wide.xlsx).  What I mean by that is that the distribution diff come from the distribution percentages which are already in the distributions_wide.Xlsx    . As a result I was wondering instead of passing the divisions from each year to pass the Actually the actual percentage is from this year and last year So that more data available 
- [ ] FEAT: analyse contains METRIC_WEIGHTS (=# --- Weighted high-end metric --- ) which converts the bins_diff into a single metric (in a sense this is a type of neural network that I could try to train for each individual school_code). In any case this is parameter that should be exposed outside of the code, so that it may be changed. 
     - [ ]FEAT: weights can be saved globally or with `schools.yml` also (or at least overriden)
     - [ ]maybe another approach (more intuitive and straightforward to compute -- array multiplication and sum) using a df with all the bins instead of a dictionary with only a few bins might be better (even though its mostly populated with zero values).
- [ ] to differentiate between measures, you need to add the weights in the analysis, suffix a hash which comes from the weights list. 

## Neural network training

In order to get better values for the weights of the high_end metric (or a better statistic/metric), a neural network could be trained to predict the next weights given the bin diffs per year, the school entry thresholds per year (normalised 20000->1) and compare them against the value of that year.

- prepare the data and the output
- choose architecture
- split the data into train/test
- train
- evaluate
- compare to other methods

## Future ideas
- [ ] UT Testing.
- [ ] Convert to package
- [ ] this repo currently caters only 3rd field school. Try to generalise it for all 4 fields (This only requires handling of addtional mark distribution data, since baseis-raw contain all fields).
  - [ ] national plot distribution only caters for the 3rd field.
  - [ ] national plot distribution only caters for the last year (maybe add an argument for processing a specific year as the last one and ignore subsequent, and set a number of years to include).
