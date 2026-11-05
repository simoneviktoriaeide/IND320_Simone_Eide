
import streamlit as st
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt
from area_selector import select_area
from weather_utils import (
    download_streamlit_weather,
    detect_precipitation_outliers,
    detect_temperature_anomalies
)


# Set the title of the meteorological data page
st.title("Meteorological Data")

# Introduce the weather analyses
st.write(
    "Explore temperature and precipitation patterns "
    "in Norway during 2024."
)


# Display the shared area selector
selected_area = select_area()


# Map reservoir areas to their corresponding weather regions
area_to_weather_region = {
    "EL1": ["NO1"],
    "EL2": ["NO2"],
    "EL3": ["NO3"],
    "EL4": ["NO4"],
    "EL5": ["NO5"],
    "VASS1": ["East"],
    "VASS2": ["West"],
    "VASS3": ["North"],
    "NO0": ["East", "West", "North"]
}


# Find the weather region(s) for the selected area
selected_weather_regions = area_to_weather_region[selected_area]

# Display the selected weather region(s)
st.write(
    "Weather region(s):",
    ", ".join(selected_weather_regions)
)


# Load the sampled coordinates saved from the notebook
coordinates_file = Path(
    "data/weather_data/streamlit_coordinates.csv"
)

streamlit_coordinates_df = pd.read_csv(coordinates_file)


# Select coordinates belonging to the chosen weather region(s)
selected_coordinates = streamlit_coordinates_df[
    streamlit_coordinates_df["region"].isin(selected_weather_regions)
]

# Display the number of selected geographical points
st.write(
    f"Selected weather locations: {len(selected_coordinates)}"
)


# Create storage for weather data during the Streamlit session
if "weather_data" not in st.session_state:
    st.session_state["weather_data"] = {}


# Identify the selected weather region combination
weather_key = tuple(selected_weather_regions)


# Display a button to load weather data
if st.button("Load Weather Data"):

    # Create placeholders for download status and progress
    status_message = st.empty()
    progress_bar = st.progress(0)

    # Store weather data from the selected regions
    weather_frames = []

    # Count all selected locations, including NO0 with 300 points
    total_locations = len(selected_coordinates)
    completed_locations = 0

    # Download or reuse data for each selected region
    for region in selected_weather_regions:

        # Count locations belonging to the current region
        region_locations = len(
            selected_coordinates[
                selected_coordinates["region"] == region
            ]
        )

        status_message.info(
            f"Loading weather data for {region}..."
        )

        # Update progress during the current region's download
        def update_progress(message):

            # Show API rate-limit messages without changing progress
            if not message.startswith("Downloaded "):
                status_message.info(message)
                return

            # Extract completed locations within the current region
            region_completed = int(message.split()[1])

            # Count completed locations across all selected regions
            overall_completed = (
                completed_locations + region_completed
            )

            # Update the overall progress bar
            progress_bar.progress(
                min(overall_completed / total_locations, 1.0)
            )

            # Display both total and regional progress
            status_message.info(
                f"{selected_area}: Downloaded "
                f"{overall_completed} of {total_locations} locations "
                f"({region}: {region_completed} of "
                f"{region_locations})"
            )

        # Load weather data for the current region
        region_df = download_streamlit_weather(
            region=region,
            start_date="2024-01-01",
            end_date="2024-12-31",
            batch_size=3,
            status_callback=update_progress
        )

        # Store the current region's weather data
        weather_frames.append(region_df)

        # Update the total number of completed locations
        completed_locations += region_locations

        # Update progress after completing the region
        progress_bar.progress(
            completed_locations / total_locations
        )

        status_message.info(
            f"{selected_area}: Loaded "
            f"{completed_locations} of {total_locations} locations "
            f"({region} completed)"
        )

    # Combine weather data from all selected regions
    weather_df = pd.concat(
        weather_frames,
        ignore_index=True
    )

    # Save data under the selected weather region combination
    st.session_state["weather_data"][weather_key] = weather_df

    # Confirm that all selected regions have been loaded
    status_message.success(
        f"{selected_area}: All {total_locations} locations loaded!"
    )

    st.success("All weather data loaded successfully!")


# Display data only for the currently selected weather region(s)
if weather_key in st.session_state["weather_data"]:

    # Retrieve the previously loaded weather data
    weather_df = st.session_state["weather_data"][weather_key]

    # Display the number of weather observations
    st.write(
        f"Total weather observations: {len(weather_df):,}"
    )

    # Display a preview of temperature and precipitation data
    st.subheader("Weather Data Preview")

    st.dataframe(weather_df.head(20))

    
    # Validate the weather data before running the analyses
    st.subheader("Weather Data Validation")

    # Count the number of unique geographical locations
    number_of_locations = (
        weather_df[["latitude", "longitude"]]
        .drop_duplicates()
        .shape[0]
    )

    # Count the number of unique hourly timestamps
    number_of_hours = weather_df["time"].nunique()

    # Calculate the expected number of observations
    expected_observations = (
        len(selected_coordinates) * 8784
    )

    # Count the actual number of observations
    actual_observations = len(weather_df)

    # Count missing temperature and precipitation values
    missing_temperature = weather_df["temperature_2m"].isna().sum()
    missing_precipitation = weather_df["precipitation"].isna().sum()

    # Display validation results
    validation_results = pd.DataFrame({
        "Check": [
            "Unique locations",
            "Unique hours",
            "Total observations",
            "Missing temperature values",
            "Missing precipitation values"
        ],
        "Expected": [
            len(selected_coordinates),
            8784,
            expected_observations,
            0,
            0
        ],
        "Actual": [
            number_of_locations,
            number_of_hours,
            actual_observations,
            missing_temperature,
            missing_precipitation
        ]
    })

    # Check whether the actual values match expectations
    validation_results["Status"] = (
        validation_results["Expected"]
        == validation_results["Actual"]
    ).map({True: "PASS", False: "CHECK"})

    st.dataframe(validation_results, hide_index=True)

    
    # Calculate average hourly precipitation across selected locations
    hourly_precipitation = (
        weather_df
        .groupby("time")["precipitation"]
        .mean()
        .reset_index()
        .rename(columns={"precipitation": "mean_precipitation"})
    )

    # Display precipitation outlier analysis
    st.subheader("Precipitation Outlier Detection - DCT + SPC")

    st.write(
        "Detect unusual precipitation patterns using "
        "Discrete Cosine Transform (DCT) and "
        "robust Statistical Process Control (SPC)."
    )

    # Allow users to adjust the DCT cutoff
    cutoff = st.slider(
        "DCT cutoff",
        min_value=5,
        max_value=100,
        value=30,
        step=5
    )

    # Allow users to adjust the SPC detection threshold
    n_std = st.slider(
        "SPC standard deviations",
        min_value=1.0,
        max_value=5.0,
        value=3.0,
        step=0.5
    )

    # Run the DCT and SPC analysis
    fig, summary = detect_precipitation_outliers(
        hourly_precipitation,
        cutoff=cutoff,
        n_std=n_std
    )

    # Display the resulting figure
    st.pyplot(fig)

    # Close the figure to release memory
    plt.close(fig)

    # Display the analysis summary
    st.write("Analysis Summary")
    st.dataframe(
        pd.DataFrame([summary]),
        hide_index=True
    )
    
    # Calculate average hourly temperature across selected locations
    hourly_temperature = (
        weather_df
        .groupby("time")["temperature_2m"]
        .mean()
        .reset_index(name="mean_temperature")
    )

    # Display temperature anomaly analysis
    st.subheader("Temperature Anomaly Detection - LOF")

    st.write(
        "Detect unusual temperature patterns using "
        "Local Outlier Factor (LOF) after removing "
        "the local temperature trend."
    )

    # Allow users to adjust the expected proportion of anomalies
    contamination = st.slider(
        "LOF contamination",
        min_value=0.005,
        max_value=0.05,
        value=0.01,
        step=0.005,
        format="%.3f"
    )

    # Allow users to adjust the number of neighbors
    n_neighbors = st.slider(
        "LOF neighbors",
        min_value=5,
        max_value=100,
        value=20,
        step=5
    )

    # Allow users to adjust the moving average window
    window_days = st.slider(
        "Temperature trend window (days)",
        min_value=1,
        max_value=30,
        value=7,
        step=1
    )

    # Run the trend-adjusted LOF analysis
    fig_lof, summary_lof = detect_temperature_anomalies(
        hourly_temperature,
        contamination=contamination,
        n_neighbors=n_neighbors,
        window_days=window_days
    )

    # Display the temperature anomaly plot
    st.pyplot(fig_lof)

    # Close the figure to release memory
    plt.close(fig_lof)

    # Display the LOF analysis summary
    st.write("LOF Analysis Summary")

    st.dataframe(
        pd.DataFrame([summary_lof]),
        hide_index=True
    )
