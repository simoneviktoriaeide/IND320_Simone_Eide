# Import necessary libraries
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from statsmodels.tsa.seasonal import STL
import numpy as np
from scipy.signal import spectrogram
from data_loader import load_data
from area_selector import select_area
from plot_theme import (
    DARK_BLUE,
    WATER_BLUE,
    LIGHT_BLUE,
    BAUXITE_RED,
    GREY,
    WHITE
)


st.title("Seasonal Reservoir Analysis")

# Load reservoir data from the NVE API
df = load_data()

# Convert dates to datetime
df["dato_Id"] = pd.to_datetime(df["dato_Id"])

# Sort reservoir data chronologically
df = df.sort_values("dato_Id")

# Create area labels such as NO0, EL1 and VASS1
df["area"] = df["omrType"] + df["omrnr"].astype(str)

# Display the shared area selector
selected_area = select_area()

# Select the chosen reservoir area
area_data = df[
    df["area"] == selected_area
].sort_values("dato_Id").copy()

# Check whether reservoir data is available
if area_data.empty:
    st.warning("No reservoir data available for the selected area.")
    st.stop()

# Create tabs for the two analysis methods
tab_stl, tab_spectrogram = st.tabs([
    "STL Decomposition",
    "Spectrogram"
])


# STL decomposition tab
with tab_stl:
    st.subheader("STL Decomposition")

    st.write(
        f"STL analysis of reservoir fill levels for {selected_area}."
    )

    # Allow the user to adjust STL parameters
    seasonal = st.slider(
        "Seasonal smoothing window",
        min_value=7,
        max_value=25,
        value=13,
        step=2
    )

    trend = st.slider(
        "Trend smoothing window",
        min_value=55,
        max_value=155,
        value=105,
        step=2
    )

    robust = st.checkbox(
        "Use robust fitting",
        value=True
    )

    # Use reservoir fill level as a percentage
    fill_level = (
        area_data.set_index("dato_Id")["fyllingsgrad"] * 100
    )

    # Perform STL decomposition
    stl = STL(
        fill_level,
        period=52,
        seasonal=seasonal,
        trend=trend,
        robust=robust
    )

    result = stl.fit()

    # Create four interactive subplots with a shared time axis
    fig = make_subplots(
        rows=4,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.06,
        subplot_titles=[
            "Observed fill level",
            "Trend",
            "Seasonal component",
            "Residuals"
        ]
    )

    # Plot the observed reservoir fill level
    fig.add_trace(
        go.Scatter(
            x=fill_level.index,
            y=result.observed,
            mode="lines",
            name="Observed",
            line=dict(
                color=DARK_BLUE,
                width=2
            )
        ),
        row=1,
        col=1
    )

    # Plot the long-term trend
    fig.add_trace(
        go.Scatter(
            x=fill_level.index,
            y=result.trend,
            mode="lines",
            name="Trend",
            line=dict(
                color=WATER_BLUE,
                width=2
            )
        ),
        row=2,
        col=1
    )

    # Plot the seasonal component
    fig.add_trace(
        go.Scatter(
            x=fill_level.index,
            y=result.seasonal,
            mode="lines",
            name="Seasonal",
            line=dict(
                color=DARK_BLUE,
                width=1.5
            )
        ),
        row=3,
        col=1
    )

    # Plot the residuals
    fig.add_trace(
        go.Scatter(
            x=fill_level.index,
            y=result.resid,
            mode="markers",
            name="Residuals",
            marker=dict(
                color=BAUXITE_RED,
                size=4,
                opacity=0.7
            )
        ),
        row=4,
        col=1
    )

    # Add zero lines to the seasonal and residual components
    fig.add_hline(
        y=0,
        line_dash="dot",
        line_color=GREY,
        row=3,
        col=1
    )

    fig.add_hline(
        y=0,
        line_dash="dot",
        line_color=GREY,
        row=4,
        col=1
    )

    # Label the axes
    fig.update_yaxes(
        title_text="Fill level (%)",
        row=1,
        col=1
    )

    fig.update_yaxes(
        title_text="Trend (%)",
        row=2,
        col=1
    )

    fig.update_yaxes(
        title_text="Seasonal (pp)",
        row=3,
        col=1
    )

    fig.update_yaxes(
        title_text="Residuals (pp)",
        row=4,
        col=1
    )

    fig.update_xaxes(
        title_text="Date",
        row=4,
        col=1
    )

    # Apply the shared Hydro-inspired theme
    fig.update_layout(
        template="hydro",
        title=(
            f"STL Decomposition of Reservoir Fill Level"
            f" - {selected_area}"
        ),
        height=850,
        showlegend=False,
        hovermode="x unified"
    )

    # Display the interactive STL decomposition
    st.plotly_chart(
        fig,
        use_container_width=True,
        theme=None
    )


# Spectrogram tab
with tab_spectrogram:
    st.subheader("Spectrogram")

    st.write(
        f"Spectrogram analysis of reservoir fill levels for {selected_area}."
    )

    # Allow the user to adjust the spectrogram parameters
    window_length = st.slider(
        "Window length (weeks)",
        min_value=52,
        max_value=208,
        value=104,
        step=4
    )

    overlap = st.slider(
        "Overlap (weeks)",
        min_value=0,
        max_value=window_length - 1,
        value=min(52, window_length - 1)
    )

    # Allow the user to adjust the displayed frequency range
    max_frequency = st.slider(
        "Maximum frequency (cycles per year)",
        min_value=2,
        max_value=26,
        value=5,
        step=1
    )

    # Convert reservoir fill levels to percentages
    fill_level = area_data["fyllingsgrad"].to_numpy() * 100

    # Calculate the spectrogram using weekly observations
    # fs=1 means one observation per week
    frequencies, times, power = spectrogram(
        fill_level,
        fs=1,
        window="hann",
        nperseg=window_length,
        noverlap=overlap,
        detrend="linear"
    )

    # Convert frequencies to cycles per year
    frequencies_per_year = frequencies * 52

    # Convert power to decibels for easier visualization
    power_db = 10 * np.log10(power + 1e-12)

    # Convert time offsets in weeks to calendar dates
    spectrogram_dates = (
        area_data["dato_Id"].iloc[0]
        + pd.to_timedelta(times, unit="W")
    )

    # Define a Hydro-inspired sequential colour scale
    hydro_colorscale = [
        [0.0, WHITE],
        [0.3, "#D6EAF0"],
        [0.5, LIGHT_BLUE],
        [0.75, WATER_BLUE],
        [1.0, DARK_BLUE]
    ]

    # Create the interactive spectrogram
    fig = go.Figure(
        data=go.Heatmap(
            x=spectrogram_dates,
            y=frequencies_per_year,
            z=power_db,
            colorscale=hydro_colorscale,
            colorbar=dict(
                title="Power (dB)"
            ),
            hovertemplate=(
                "Date: %{x|%Y-%m-%d}<br>"
                "Frequency: %{y:.2f} cycles/year<br>"
                "Power: %{z:.2f} dB"
                "<extra></extra>"
            )
        )
    )

    # Highlight the expected annual seasonal frequency
    fig.add_hline(
        y=1,
        line_color=BAUXITE_RED,
        line_dash="dash",
        line_width=2,
        annotation_text="Annual cycle",
        annotation_position="top right"
    )

    # Apply the shared Hydro-inspired theme
    fig.update_layout(
        template="hydro",
        title=(
            f"Spectrogram of Reservoir Fill Level"
            f" - {selected_area}"
        ),
        xaxis_title="Date",
        yaxis_title="Frequency (cycles per year)",
        height=550
    )

    # Limit the displayed frequency range
    fig.update_yaxes(
        range=[0, max_frequency]
    )

    # Display the interactive spectrogram
    st.plotly_chart(
        fig,
        use_container_width=True,
        theme=None
    )