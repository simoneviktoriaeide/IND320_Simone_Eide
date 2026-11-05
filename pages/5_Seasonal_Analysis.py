# Import necessary libraries
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from statsmodels.tsa.seasonal import STL
import numpy as np
from scipy.signal import spectrogram
from data_loader import load_data
from area_selector import select_area


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

    # Select the chosen reservoir area
    area_data = df[
        df["area"] == selected_area
    ].sort_values("dato_Id").copy()

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

    # Plot the decomposition
    fig = result.plot()
    fig.set_size_inches(12, 9)
    fig.suptitle(
        f"STL Decomposition of Reservoir Fill Level - {selected_area}",
        fontsize=14
    )
    fig.tight_layout()

    st.pyplot(fig)
    plt.close(fig)


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

    # Select the chosen reservoir area and sort by date
    area_data = df[
        df["area"] == selected_area
    ].sort_values("dato_Id").copy()

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

    # Create the spectrogram plot
    fig, ax = plt.subplots(figsize=(12, 6))

    mesh = ax.pcolormesh(
        times / 52 + area_data["dato_Id"].dt.year.iloc[0],
        frequencies_per_year,
        power_db,
        shading="auto",
        cmap="viridis"
    )

    # Add a colorbar to show the strength of each frequency
    fig.colorbar(mesh, ax=ax, label="Power (dB)")

    # Label the axes and add a title
    ax.set_title(
        f"Spectrogram of Reservoir Fill Level - {selected_area}"
    )
    ax.set_xlabel("Year")
    ax.set_ylabel("Frequency (cycles per year)")
    # Limit the displayed frequency range
    ax.set_ylim(0, max_frequency)

    # Highlight the expected annual seasonal frequency
    ax.axhline(
        1,
        color="red",
        linestyle="--",
        label="Annual cycle"
    )
    ax.legend()

    fig.tight_layout()

    # Display the spectrogram in Streamlit
    st.pyplot(fig)
    plt.close(fig)