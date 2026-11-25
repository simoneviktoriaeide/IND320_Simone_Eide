# Import necessary libraries
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from data_loader import load_data
from area_selector import select_area
from plot_theme import DARK_BLUE, WATER_BLUE, BAUXITE_RED, GREY


st.title("Reservoir Data Plot")

# Loads the reservoir data
df = load_data()

# Converts the date column to datetime
df["dato_Id"] = pd.to_datetime(df["dato_Id"])

# Sorts the data by date
df = df.sort_values("dato_Id")

# Creates area labels such as NO0, EL1 and VASS1
df["area"] = df["omrType"] + df["omrnr"].astype(str)

# Display the shared area selector
selected_area = select_area()

# Variables available for plotting
plot_columns = [
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

# Assigns consistent colours to the variables
variable_colors = {
    "fyllingsgrad": DARK_BLUE,
    "fylling_TWh": WATER_BLUE,
    "fyllingsgrad_forrige_uke": WATER_BLUE,
    "endring_fyllingsgrad": BAUXITE_RED
}

# Filters the data based on the selected area
area_data = df[df["area"] == selected_area].copy()

# Checks whether data is available
if area_data.empty:
    st.warning("No reservoir data available for the selected area.")
    st.stop()

# Selects which variable to plot
selected_variable = st.selectbox(
    "Select variable",
    ["All variables"] + plot_columns,
    format_func=lambda x: variable_labels.get(x, x)
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

# Plots one selected variable
if selected_variable != "All variables":

    # Converts ratios to percentages when relevant
    if selected_variable in [
        "fyllingsgrad",
        "fyllingsgrad_forrige_uke",
        "endring_fyllingsgrad"
    ]:
        y_data = filtered_data[selected_variable] * 100
    else:
        y_data = filtered_data[selected_variable]

    # Creates an interactive Plotly figure
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=filtered_data["dato_Id"],
            y=y_data,
            mode="lines+markers",
            name=variable_labels[selected_variable],
            line=dict(
                color=variable_colors[selected_variable],
                width=2.5
            )
        )
    )

    # Applies the shared Hydro-inspired theme
    fig.update_layout(
        template="hydro",
        title=f"{variable_labels[selected_variable]} - {selected_area}",
        xaxis_title="Date",
        yaxis_title=variable_labels[selected_variable],
        hovermode="x unified",
        height=500
    )

    # Displays the interactive figure
    st.plotly_chart(
        fig,
        use_container_width=True,
        theme=None
    )


# Plots all relevant variables on a common percentage scale
else:

    # Creates an interactive Plotly figure
    fig = go.Figure()

    # Gets the reservoir capacity for the selected area
    capacity = area_data["kapasitet_TWh"].iloc[0]

    # Converts reservoir levels to percent
    # and weekly change to percentage points
    fill_level = filtered_data["fyllingsgrad"] * 100

    previous_week = (
        filtered_data["fyllingsgrad_forrige_uke"] * 100
    )

    weekly_change = (
        filtered_data["endring_fyllingsgrad"] * 100
    )

    # Plots the fill level
    fig.add_trace(
        go.Scatter(
            x=filtered_data["dato_Id"],
            y=fill_level,
            mode="lines",
            name="Fill level (%)",
            line=dict(
                color=DARK_BLUE,
                width=2.5
            )
        )
    )

    # Plots the previous week's fill level
    fig.add_trace(
        go.Scatter(
            x=filtered_data["dato_Id"],
            y=previous_week,
            mode="lines",
            name="Previous week fill level (%)",
            line=dict(
                color=WATER_BLUE,
                width=2,
                dash="dash"
            )
        )
    )

    # Plots the weekly change
    fig.add_trace(
        go.Scatter(
            x=filtered_data["dato_Id"],
            y=weekly_change,
            mode="lines",
            name="Weekly change (percentage points)",
            line=dict(
                color=BAUXITE_RED,
                width=2
            )
        )
    )

    # Adds a zero line for the weekly change
    fig.add_hline(
        y=0,
        line_width=1,
        line_dash="dot",
        line_color=GREY
    )

    # Finds the lowest weekly change in the selected area
    lowest_change = (
        area_data["endring_fyllingsgrad"].min() * 100
    )

    # Gives some space below the lowest negative value
    lower_limit = min(-5, lowest_change - 2)

    # Applies the shared Hydro-inspired theme
    fig.update_layout(
        template="hydro",
        title=f"Reservoir development - {selected_area}",
        xaxis_title="Date",
        yaxis_title=(
            "% of total capacity / weekly change (percentage points)"
        ),
        hovermode="x unified",
        height=500,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0
        )
    )

    # Sets the y-axis range and intervals
    fig.update_yaxes(
        range=[lower_limit, 100],
        dtick=10
    )

    # Displays the interactive figure
    st.plotly_chart(
        fig,
        use_container_width=True,
        theme=None
    )

    st.caption(
        f"Reservoir capacity for {selected_area}: "
        f"{capacity:.2f} TWh. Fill level represents stored energy "
        "as a percentage of reservoir capacity. Weekly change is "
        "shown in percentage points."
    )