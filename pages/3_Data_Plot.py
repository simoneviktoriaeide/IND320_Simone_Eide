
import streamlit as st
import pandas as pd
from data_loader import load_data  # Imports the data loading function
import matplotlib.pyplot as plt


st.title("Reservoir Data Plot")

# Loads the reservoir data
df = load_data()

# Converts the date column to datetime
df["dato_Id"] = pd.to_datetime(df["dato_Id"])

df = df.sort_values("dato_Id")

# Creates area labels such as NO0, EL1 and VASS1
df["area"] = df["omrType"] + df["omrnr"].astype(str)

# Creates a list of available areas
areas = sorted(df["area"].unique().tolist())

# Selects which area to display, with Norway as default
selected_area = st.selectbox(
    "Select area",
    areas,
    index=areas.index("NO0")
)

# Filters the data based on the selected area
area_data = df[df["area"] == selected_area].copy()

# Variables available for plotting
plot_columns = [
    "fyllingsgrad",
    "fylling_TWh",
    "fyllingsgrad_forrige_uke",
    "endring_fyllingsgrad"
]

# Selects which variable to plot
selected_variable = st.selectbox(
    "Select variable",
    ["All variables"] + plot_columns
)

# Creates a sorted list of months in the dataset
months = sorted(
    area_data["dato_Id"].dt.to_period("M").astype(str).unique()
)

# Selects the time period to display
selected_months = st.select_slider(
    "Select month range",
    options=months,
    value=(months[0], months[0])
)

# Filters the data based on the selected month range
start_month, end_month = selected_months

filtered_data = area_data[
    (area_data["dato_Id"].dt.to_period("M") >= pd.Period(start_month)) &
    (area_data["dato_Id"].dt.to_period("M") <= pd.Period(end_month))
]


# Plots the selected variable
if selected_variable != "All variables":
    fig, ax = plt.subplots()

    ax.plot(
        filtered_data["dato_Id"],
        filtered_data[selected_variable]
    )

    ax.set_title(f"{selected_variable} - {selected_area}")
    ax.set_xlabel("Date")
    ax.set_ylabel(selected_variable)

    plt.xticks(rotation=45)
    fig.tight_layout()

    st.pyplot(fig)

else:
    fig, ax = plt.subplots()

    for column in plot_columns:
        ax.plot(
            filtered_data["dato_Id"],
            filtered_data[column],
            label=column
        )

    ax.set_title(f"All variables - {selected_area}")
    ax.set_xlabel("Date")
    ax.set_ylabel("Value")
    ax.legend()

    plt.xticks(rotation=45)
    fig.tight_layout()

    st.pyplot(fig)