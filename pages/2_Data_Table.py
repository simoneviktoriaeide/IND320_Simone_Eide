
# Import libraries
import streamlit as st
import pandas as pd
from data_loader import load_data


st.title("Reservoir Data Table")

# Loads the reservoir data from the NVE API
df = load_data()

# Converts the date column to datetime
df["dato_Id"] = pd.to_datetime(df["dato_Id"])

# Sorts the data by date
df = df.sort_values("dato_Id")

# Creates area labels such as NO0, EL1 and VASS1
df["area"] = df["omrType"] + df["omrnr"].astype(str)

# Selects the area type
selected_area_type = st.radio(
    "Select area type",
    ["EL", "NO", "VASS"],
    horizontal=True
)

# Filters data based on the selected area type
area_type_data = df[
    df["omrType"] == selected_area_type
].copy()

# Finds the first month in the selected dataset
first_month = area_type_data["dato_Id"].dt.to_period("M").min()

# Selects data from the first month
first_month_data = area_type_data[
    area_type_data["dato_Id"].dt.to_period("M") == first_month
].copy()

# Selects relevant reservoir variables
series_columns = [
    "fyllingsgrad",
    "fylling_TWh",
    "fyllingsgrad_forrige_uke",
    "endring_fyllingsgrad"
]

# English labels for the variables
variable_labels = {
    "fyllingsgrad": "Fill level (%)",
    "fylling_TWh": "Stored energy (TWh)",
    "fyllingsgrad_forrige_uke": "Previous week fill level (%)",
    "endring_fyllingsgrad": "Weekly change (percentage points)"
}

# Creates one row for each area
table_rows = []

for area in sorted(first_month_data["area"].unique()):

    # Selects data for the current area
    area_data = first_month_data[
        first_month_data["area"] == area
    ].sort_values("dato_Id")

    # Creates a row with time series for each variable
    row = {"Area": area}

    for column in series_columns:
        values = area_data[column].tolist()

        # Converts ratios to percentages when relevant
        if column != "fylling_TWh":
            values = [value * 100 for value in values]

        row[variable_labels[column]] = values

    table_rows.append(row)

# Creates a DataFrame for the Streamlit table
table_data = pd.DataFrame(table_rows)

st.write(
    f"Reservoir data for **{selected_area_type}** areas "
    f"during the first month in the dataset: **{first_month}**"
)

# Displays a line chart for each variable and area
st.dataframe(
    table_data,
    column_config={
        label: st.column_config.LineChartColumn(label)
        for label in variable_labels.values()
    },
    hide_index=True,
    use_container_width=True
)
