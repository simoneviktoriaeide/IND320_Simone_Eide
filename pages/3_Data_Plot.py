
# Import neseccary libraries
import streamlit as st
import pandas as pd
from data_loader import load_data  # Imports the data loading function
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator # For more detailed y axis

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
# Labels for the variables
variable_labels = {
    "fyllingsgrad": "Fill level (%)",
    "fylling_TWh": "Stored energy (TWh)",
    "fyllingsgrad_forrige_uke": "Previous week fill level (%)",
    "endring_fyllingsgrad": "Weekly change (percentage points)"
}


# Plots one selected variable
if selected_variable != "All variables":
    fig, ax = plt.subplots()

    # Converts ratios to percentages when relevant
    if selected_variable in [
        "fyllingsgrad",
        "fyllingsgrad_forrige_uke",
        "endring_fyllingsgrad"
    ]:
        y_data = filtered_data[selected_variable] * 100
    else:
        y_data = filtered_data[selected_variable]

    ax.plot(
        filtered_data["dato_Id"],
        y_data
    )

    ax.set_title(
        f"{variable_labels[selected_variable]} - {selected_area}"
    )
    ax.set_xlabel("Date")
    ax.set_ylabel(variable_labels[selected_variable])

    plt.xticks(rotation=45)
    fig.tight_layout()

    st.pyplot(fig)


# Plots all relevant variables on a common percentage scale
else:
    fig, ax = plt.subplots()

    # Gets the reservoir capacity for the selected area
    capacity = area_data["kapasitet_TWh"].iloc[0]

    # Converts the variables to a common percentage-based scale
    fill_level = filtered_data["fyllingsgrad"] * 100

    previous_week = (
        filtered_data["fyllingsgrad_forrige_uke"] * 100
    )

    weekly_change = (
        filtered_data["endring_fyllingsgrad"] * 100
    )

    # Plots all variables together
    ax.plot(
        filtered_data["dato_Id"],
        fill_level,
        label="Fill level (%)"
    )

    ax.plot(
        filtered_data["dato_Id"],
        previous_week,
        label="Previous week fill level (%)"
    )

    ax.plot(
        filtered_data["dato_Id"],
        weekly_change,
        label="Weekly change (percentage points)"
    )

    # Adds a zero line for the weekly change
    ax.axhline(
        y=0,
        linewidth=0.8,
        linestyle=":"
    )

    # Finds the lowest weekly change in the selected area
    lowest_change = (
        area_data["endring_fyllingsgrad"].min() * 100
    )

    # Gives some space below the lowest negative value
    lower_limit = min(-5, lowest_change - 2)

    ax.set_ylim(lower_limit, 100)

    ax.yaxis.set_major_locator(MultipleLocator(10))

    ax.set_title(f"Reservoir development - {selected_area}")
    ax.set_xlabel("Date")
    ax.set_ylabel(
        "Reservoir level (% of capacity) / weekly change (percentage points)"
    )

    ax.legend()

    plt.xticks(rotation=45)
    fig.tight_layout()

    st.pyplot(fig)

    st.caption(
        f"Reservoir capacity for {selected_area}: "
        f"{capacity:.2f} TWh. Stored energy is shown as a "
        "percentage of capacity. Weekly change is shown in "
        "percentage points."
    )
