#%%
import numpy as np
import pathlib 
import pandas as pd

#%%
ROOTDIR = pathlib.Path(__file__).parent
DATADIR = ROOTDIR / 'data'
STUDENT_DATA = DATADIR / 'Bro-Maria.xlsx'

CLASS_NAMES_DICT = {'Βιολογία':'bio',
                    'Φυσική':'phys', 
                    'Χημεία':'chem',
                    'γλώσσα':'lang',
                    }

# %%
df = pd.read_excel(STUDENT_DATA, sheet_name='data-StudentsDistribution')
df.drop(columns=['Column1', 'excludde'], inplace=True)
df.rename(columns={'Επίδοση': 'marks_bin', 'Πλήθος':'count', 'Ποσοστό':'percentage', 'Μαθημα ':'class', 'Ετος':'year'}, inplace=True)
df.head()

# replace class names with their abbreviations
df['class'] = df['class'].replace(CLASS_NAMES_DICT)


# %%
# I wnat to create a new column based on marks_bin, by splitting along the '-' and taking the first part conveted as integer

df['marks_bin_start'] = df['marks_bin'].str.split('-').str[0].astype(int)
# I want to get a subset of the data frame based on a value of the 
df.head()
# %%
# for a given class and year I want to get the values of the percentage with the marks_bin_start
def get_percentage_by_class_year(df, class_name, year):
    subset = df[(df['class'] == class_name) & (df['year'] == year)]
    return subset[['marks_bin_start', 'percentage']]

# Example usage
class_name = 'lang'
year = 2023
percentage_data = get_percentage_by_class_year(df, class_name, year)
print(percentage_data)
# sort the data by marks_bin_start and calculate the cumulative percentage

percentage_data = percentage_data.sort_values(by='marks_bin_start')
percentage_data['cumulative_percentage'] = percentage_data['percentage'].cumsum()
# %%
percentage_data

# %%

def massage_data_for_class_year(df,class_name, year):
    """
    This function takes a DataFrame, a class name, and a year,
    and returns a DataFrame with marks_bin_start and cumulative percentage
    for the specified class and year.
    """
    subset = get_percentage_by_class_year(df, class_name, year)
    subset = subset[['marks_bin_start', 'percentage']]
    subset = subset.sort_values(by='marks_bin_start')
    subset['cumulative_percentage'] = subset['percentage'].cumsum()
    # shift the cumulative percentage by one and replace first value with 0 
    subset['cumulative_percentage'] = subset['cumulative_percentage'].shift(1).fillna(0)
    return subset
# %%
massaged_data = massage_data_for_class_year(df, class_name, year)
# %%
massaged_data
# %%
