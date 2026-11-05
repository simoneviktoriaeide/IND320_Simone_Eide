
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


# ---------------------------------------------------------
# PAGE DESIGN
# ---------------------------------------------------------

# Apply custom styling to the meteorological data page
st.markdown("""
<style>

/* Main content width and spacing */
.block-container {
    max-width: 1250px;
    padding-top: 2rem;
    padding-bottom: 3rem;
}

/* Page section headings */
h2, h3 {
    letter-spacing: -0.025em;
}

/* Dark blue primary buttons */
div.stButton > button[kind="primary"] {
    background-color: #294B70;
    color: #FFFFFF;
    border: 1px solid #294B70;
    border-radius: 10px;
    font-weight: 600;
    min-height: 48px;
    transition: background-color 0.2s ease;
}

div.stButton > button[kind="primary"]:hover {
    background-color: #365F89;
    color: #FFFFFF;
    border-color: #365F89;
}

div.stButton > button[kind="primary"]:focus {
    color: #FFFFFF;
    border-color: #365F89;
}

/* Full-width analysis tabs */
div[data-baseweb="tab-list"] {
    display: flex;
    width: 100%;
    gap: 0;
    border-bottom: 1px solid rgba(128, 128, 128, 0.2);
}

/* Make both tabs equally wide */
button[data-baseweb="tab"] {
    flex: 1 1 0;
    min-width: 0;
    justify-content: center;
    text-align: center;
    font-size: clamp(14px, 1.5vw, 18px);
    font-weight: 600;
    padding: 18px 12px;
    white-space: normal;
    transition: color 0.2s ease;
}

/* Active tab styling */
button[data-baseweb="tab"][aria-selected="true"] {
    color: #294B70;
}

/* Active tab underline */
div[data-baseweb="tab-highlight"] {
    background-color: #294B70;
    height: 3px;
}

/* Radio button group spacing */
div[role="radiogroup"] {
    gap: 10px;
}

/* Area selection options */
div[role="radiogroup"] label {
    padding: 10px 14px;
    border: 1px solid rgba(128, 128, 128, 0.18);
    border-radius: 10px;
    transition:
        background-color 0.2s ease,
        border-color 0.2s ease;
}

/* Hover effect for area selection */
div[role="radiogroup"] label:hover {
    background-color: rgba(41, 75, 112, 0.07);
    border-color: rgba(41, 75, 112, 0.35);
}

/* Improve metric appearance */
div[data-testid="stMetric"] {
    padding: 16px;
    border: 1px solid rgba(128, 128, 128, 0.18);
    border-radius: 12px;
    background-color: rgba(128, 128, 128, 0.035);
}

/* Make metric values stand out */
div[data-testid="stMetricValue"] {
    font-weight: 650;
}

/* Responsive adjustments */
@media (max-width: 600px) {

    .block-container {
        padding-top: 1rem;
        padding-left: 1rem;
        padding-right: 1rem;
    }

    button[data-baseweb="tab"] {
        font-size: 13px;
        padding: 14px 5px;
    }

    div[role="radiogroup"] {
        gap: 6px;
    }

    div[role="radiogroup"] label {
        padding: 8px 10px;
    }

    div[data-testid="stMetric"] {
        padding: 12px;
    }
}

</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------
# PAGE HEADER
# ---------------------------------------------------------

st.title("Meteorological Data")

st.write(
    "Explore historical weather patterns across Norway "
    "using ERA5 reanalysis data from 2024. "
    "Investigate unusual precipitation events and "
    "temperature anomalies through interactive analyses."
)

st.divider()


# ---------------------------------------------------------
# AREA SELECTION
# ---------------------------------------------------------

st.subheader("Select Area")

st.write(
    "Choose a reservoir area to explore its corresponding "
    "meteorological data."
)

# Display the shared area selector inside a bordered container
with st.container(border=True):

    selected_area = select_area()


# Map reservoir areas to corresponding weather regions
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

# Identify the weather regions associated with the selected area
selected_weather_regions = area_to_weather_region[selected_area]


# ---------------------------------------------------------
# DATASET OVERVIEW
# ---------------------------------------------------------

# Load sampled geographical coordinates
coordinates_file = Path(
    "data/weather_data/streamlit_coordinates.csv"
)

streamlit_coordinates_df = pd.read_csv(coordinates_file)

# Filter coordinates for the selected weather regions
selected_coordinates = streamlit_coordinates_df[
    streamlit_coordinates_df["region"].isin(selected_weather_regions)
]

st.subheader("Selected Dataset")

# Display important dataset information
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "Reservoir Area",
        selected_area
    )

with col2:
    st.metric(
        "Weather Locations",
        len(selected_coordinates)
    )

with col3:
    st.metric(
        "Data Period",
        "2024"
    )

st.caption(
    "Weather regions: "
    + ", ".join(selected_weather_regions)
    + "  |  Source: Open-Meteo ERA5"
)


# ---------------------------------------------------------
# WEATHER DATA LOADING
# ---------------------------------------------------------

# Store weather data during the Streamlit session
if "weather_data" not in st.session_state:
    st.session_state["weather_data"] = {}

# Use selected weather regions as a session storage key
weather_key = tuple(selected_weather_regions)

# Check whether the selected dataset is already loaded
data_loaded = weather_key in st.session_state["weather_data"]

st.divider()

st.subheader("Weather Data")

# Display a status message depending on the dataset state
if data_loaded:

    st.success(
        "Weather data is ready. Explore the analyses below."
    )

else:

    st.info(
        "Load the weather data to explore precipitation "
        "outliers and temperature anomalies."
    )


# Allow users to load or reload weather data
if st.button(
    "Load Weather Data" if not data_loaded else "Reload Weather Data",
    type="primary",
    use_container_width=True
):

    # Create placeholders for download status and progress
    status_message = st.empty()
    progress_bar = st.progress(0)

    # Store downloaded data from each selected region
    weather_frames = []

    total_locations = len(selected_coordinates)
    completed_locations = 0

    # Download or reuse cached weather data for each region
    for region in selected_weather_regions:

        # Count locations within the current region
        region_locations = len(
            selected_coordinates[
                selected_coordinates["region"] == region
            ]
        )

        status_message.info(
            f"Loading weather data for {region}..."
        )

        # Update download progress
        def update_progress(message):

            # Display API messages without changing progress
            if not message.startswith("Downloaded "):
                status_message.info(message)
                return

            # Extract completed locations in the current region
            region_completed = int(message.split()[1])

            # Calculate total completed locations
            overall_completed = (
                completed_locations + region_completed
            )

            # Update the overall progress bar
            progress_bar.progress(
                min(overall_completed / total_locations, 1.0)
            )

            # Display detailed progress information
            status_message.info(
                f"{selected_area}: Downloaded "
                f"{overall_completed} of {total_locations} locations "
                f"({region}: {region_completed} of "
                f"{region_locations})"
            )

        # Download historical ERA5 weather data
        region_df = download_streamlit_weather(
            region=region,
            start_date="2024-01-01",
            end_date="2024-12-31",
            batch_size=3,
            status_callback=update_progress
        )

        # Store data from the current region
        weather_frames.append(region_df)

        # Update completed location count
        completed_locations += region_locations

        progress_bar.progress(
            completed_locations / total_locations
        )

        status_message.info(
            f"{selected_area}: Loaded "
            f"{completed_locations} of {total_locations} locations "
            f"({region} completed)"
        )

    # Combine all selected regions into one dataset
    weather_df = pd.concat(
        weather_frames,
        ignore_index=True
    )

    # Save the dataset for reuse during the session
    st.session_state["weather_data"][weather_key] = weather_df

    # Confirm successful data loading
    status_message.success(
        f"{selected_area}: All {total_locations} locations loaded!"
    )

    st.success(
        "Weather data loaded successfully!"
    )


# ---------------------------------------------------------
# ANALYSES AND DATA QUALITY
# ---------------------------------------------------------

# Display analyses only when weather data is available
if weather_key in st.session_state["weather_data"]:

    # Retrieve stored weather data
    weather_df = st.session_state["weather_data"][weather_key]

    # Display dataset statistics
    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            "Hourly Observations",
            f"{len(weather_df):,}"
        )

    with col2:
        st.metric(
            "Unique Timestamps",
            f"{weather_df['time'].nunique():,}"
        )

    # Keep technical information in an expandable section
    with st.expander("Data Quality & Details"):

        st.write(
            "The following checks verify the completeness "
            "of the downloaded weather dataset."
        )

        # Count unique geographical locations
        number_of_locations = (
            weather_df[["latitude", "longitude"]]
            .drop_duplicates()
            .shape[0]
        )

        # Count unique hourly timestamps
        number_of_hours = weather_df["time"].nunique()

        # Calculate expected observations for 2024
        expected_observations = (
            len(selected_coordinates) * 8784
        )

        # Count actual observations
        actual_observations = len(weather_df)

        # Count missing weather values
        missing_temperature = (
            weather_df["temperature_2m"].isna().sum()
        )

        missing_precipitation = (
            weather_df["precipitation"].isna().sum()
        )

        # Compare expected and actual values
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

        # Assign validation status
        validation_results["Status"] = (
            validation_results["Expected"]
            == validation_results["Actual"]
        ).map({True: "PASS", False: "CHECK"})

        # Display validation table
        st.dataframe(
            validation_results,
            hide_index=True,
            use_container_width=True
        )

        # Display a small data preview
        st.write("Data Preview")

        st.dataframe(
            weather_df.head(10),
            use_container_width=True
        )

    st.divider()


    # -----------------------------------------------------
    # WEATHER ANALYSIS TABS
    # -----------------------------------------------------

    st.subheader("Weather Analysis")

    st.write(
        "Select an analysis below to investigate unusual "
        "precipitation events or temperature anomalies."
    )

    # Create two equally sized analysis tabs
    tab_spc, tab_lof = st.tabs([
        "🌧️ Precipitation · DCT/SPC",
        "🌡️ Temperature · LOF"
    ])


    # -----------------------------------------------------
    # TAB 1: PRECIPITATION DCT/SPC
    # -----------------------------------------------------

    with tab_spc:

        st.subheader("Precipitation Outlier Detection")

        st.write(
            "Identify unusual precipitation events using "
            "Discrete Cosine Transform (DCT) filtering "
            "and robust Statistical Process Control (SPC)."
        )

        # Calculate average hourly precipitation
        hourly_precipitation = (
            weather_df
            .groupby("time")["precipitation"]
            .mean()
            .reset_index()
            .rename(
                columns={"precipitation": "mean_precipitation"}
            )
        )

        # Display adjustable analysis settings
        with st.expander(
            "Analysis Settings",
            expanded=True
        ):

            cutoff = st.slider(
                "DCT cutoff",
                min_value=5,
                max_value=100,
                value=30,
                step=5
            )

            n_std = st.slider(
                "SPC standard deviations",
                min_value=1.0,
                max_value=5.0,
                value=3.0,
                step=0.5
            )

        # Perform precipitation outlier detection
        fig, summary = detect_precipitation_outliers(
            hourly_precipitation,
            cutoff=cutoff,
            n_std=n_std
        )

        # Display precipitation analysis plot
        st.pyplot(fig)
        plt.close(fig)

        # Display key analysis results
        st.markdown("#### Analysis Results")

        result_col1, result_col2 = st.columns(2)

        with result_col1:
            st.metric(
                "Detected Outliers",
                summary["Number of outliers"]
            )

        with result_col2:
            st.metric(
                "Outlier Percentage",
                f"{summary['Percentage (%)']:.2f}%"
            )

        st.caption(
            "Outliers are identified using high-pass "
            "filtered precipitation and robust "
            "statistical thresholds."
        )


    # -----------------------------------------------------
    # TAB 2: TEMPERATURE LOF
    # -----------------------------------------------------

    with tab_lof:

        st.subheader("Temperature Anomaly Detection")

        st.write(
            "Identify unusual temperature patterns "
            "using Local Outlier Factor (LOF) after "
            "removing the local temperature trend."
        )

        # Calculate average hourly temperature
        hourly_temperature = (
            weather_df
            .groupby("time")["temperature_2m"]
            .mean()
            .reset_index(name="mean_temperature")
        )

        # Display adjustable analysis settings
        with st.expander(
            "Analysis Settings",
            expanded=True
        ):

            contamination = st.slider(
                "LOF contamination",
                min_value=0.005,
                max_value=0.05,
                value=0.01,
                step=0.005,
                format="%.3f"
            )

            n_neighbors = st.slider(
                "LOF neighbors",
                min_value=5,
                max_value=100,
                value=20,
                step=5
            )

            window_days = st.slider(
                "Temperature trend window (days)",
                min_value=1,
                max_value=30,
                value=7,
                step=1
            )

        # Perform temperature anomaly detection
        fig_lof, summary_lof = detect_temperature_anomalies(
            hourly_temperature,
            contamination=contamination,
            n_neighbors=n_neighbors,
            window_days=window_days
        )

        # Display temperature anomaly plot
        st.pyplot(fig_lof)
        plt.close(fig_lof)

        # Display key analysis results
        st.markdown("#### Analysis Results")

        result_col1, result_col2 = st.columns(2)

        with result_col1:
            st.metric(
                "Detected Anomalies",
                summary_lof["Number of anomalies"]
            )

        with result_col2:
            st.metric(
                "Anomaly Percentage",
                f"{summary_lof['Percentage (%)']:.2f}%"
            )

        st.caption(
            "Anomalies are identified using "
            "trend-adjusted temperature deviations "
            "and Local Outlier Factor."
        )
