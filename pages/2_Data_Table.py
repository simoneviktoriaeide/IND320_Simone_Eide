import streamlit as st
import pandas as pd
from data_loader import load_data  # Imports the data loading function

# Loads the reservoir data
df = load_data()

# Converts the date column to datetime
df["dato_Id"] = pd.to_datetime(df["dato_Id"])

# Selects data for Norway as a whole
no_data = df[df["omrType"] == "NO"].copy()
no_data = no_data.sort_values("dato_Id")

# Finds the first month in the dataset
first_month = no_data["dato_Id"].dt.to_period("M").min()

# Selects data from the first month
first_month_data = no_data[
    no_data["dato_Id"].dt.to_period("M") == first_month
]

# Selects relevant reservoir variables
series_columns = [
    "fyllingsgrad",
    "fylling_TWh",
    "fyllingsgrad_forrige_uke",
    "endring_fyllingsgrad"
]

# Creates one row for each selected variable
table_data = pd.DataFrame({
    "Variable": series_columns,
    "First month": [
        first_month_data[column].tolist()
        for column in series_columns
    ]
})

# Page content
st.title("Reservoir Data Table")

st.write(
    f"National reservoir data (NO) for the first month "
    f"in the dataset: **{first_month}**"
)

st.dataframe(
    table_data,
    column_config={
        "First month": st.column_config.LineChartColumn(
            "First month"
        )
    },
    hide_index=True
)


import pandas as pd
import streamlit as st

data_df = pd.DataFrame(
    {
        "sales": [
            [0, 4, 26, 80, 100, 40],
            [80, 20, 80, 35, 40, 100],
            [10, 20, 80, 80, 70, 0],
            [10, 100, 20, 100, 30, 100],
        ],
    }
)
