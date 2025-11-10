# Importing libraries
import pandas as pd
import numpy as np

# Reading the data
print('Reading the A/B test data:')
try:
    data = pd.read_csv("data/raw/AB_Test_Results.csv")
    print('✅Data read successfully!!')
except Exception as e:
    raise ValueError(f"❌ Data could not be read: {e}")

# Formatting columns names
data.columns = [col.lower() for col in data.columns]

# Getting contaminated users, that is,
# Users that ar both on the control group and the variant group

variant_check = data.groupby('user_id')['variant_name'].nunique().reset_index()
contaminated_users = variant_check[variant_check['variant_name'] > 1]['user_id'].to_list()

# Removing the contaminated users
data_clean = data[~data['user_id'].isin(contaminated_users)].copy()

print("Number of contaminated users:", len(contaminated_users))
print("Number of events for the analysis:", len(data_clean))

# Aggregating the data so we have one line per user

data_agg = data_clean.groupby(['user_id', 'variant_name']).agg(
    total_revenue=('revenue', 'sum')
).reset_index()

# Generating the convertion information
data_agg['converted'] = np.where(data_agg['total_revenue'] > 0,
                                 1,
                                 0)
print(data_agg)
print('Number of unique users for the analysis:', len(data_agg))

# Saving the clean data
try:
    data_agg.to_csv('data/processed/data_processed.csv')
    print('✅Data was saved successfully!!')
except Exception as e:
    raise ValueError(f"❌ Data could not be saved: {e}")