#%%[markdown]
'''
this is using the data from the wide format in order to test the following hypothesis. 

The 10% best marks should correspond to a marker that has a significant impact on the change of marks.

'''

# %%
import pandas as pd
import numpy as np
import pathlib
from scipy.stats import ttest_ind

# Define paths
ROOTDIR = pathlib.Path(__file__).parent
DATADIR = ROOTDIR / 'data'
OUTDIR = ROOTDIR / 'output'
WIDE_DF_XLSX =OUTDIR  / 'wide_df.xlsx'

# Load the wide format DataFrame
wide_df = pd.read_excel(WIDE_DF_XLSX, sheet_name=0)
# %%

wide_df.head()

# %%
new2023 = wide_df.iloc[1,1:]  -wide_df.iloc[0,1:] 
new2024 = wide_df.iloc[2,1:]  -wide_df.iloc[1,1:] 
# %%
