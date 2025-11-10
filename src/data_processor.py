# Importing libraries
import pandas as pd
import numpy as np

# Reading the data
data = pd.read_csv("data/raw/AB_Test_Result.csv")
data.info()
print(data.head())