# Import necessary libraries
from pathlib import Path
import time

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import openmeteo_requests
import requests_cache
from sklearn.neighbors import LocalOutlierFactor
from retry_requests import retry
from scipy.fft import dct, idct

from plot_theme import (
    DARK_BLUE,
    WATER_BLUE,
    LIGHT_BLUE,
    BAUXITE_RED,
    GREY
)


# Set up a cached session for Open-Meteo requests
cache_session = requests_cache.CachedSession(
    "data/weather_data/weather_cache",
    expire_after=-1
)

# Retry temporary request errors
retry_session = retry(
    cache_session,
    retries=3,
    backoff_factor=1
)

# Create the Open-Meteo API client
openmeteo = openmeteo_requests.Client(session=retry_session)


# Define a function to download weather data for Streamlit
def download_streamlit_weather(
    region,
    start_date="2024-01-01",
    end_date="2024-12-31",
    batch_size=3,
    status_callback=None
):

    # Load the sampled coordinates saved from the notebook
    coordinates_file = Path(
        "data/weather_data/streamlit_coordinates.csv"
    )
    coordinates_df = pd.read_csv(coordinates_file)

    # Select the 100 coordinates for the requested region
    region_coordinates = coordinates_df[
        coordinates_df["region"] == region
    ].reset_index(drop=True)

    if region_coordinates.empty:
        raise ValueError(f"No coordinates found for region: {region}")

    # Create a separate folder for Streamlit weather data
    output_folder = Path("data/weather_data/streamlit")
    output_folder.mkdir(parents=True, exist_ok=True)

    # Define the Open-Meteo historical weather API address
    weather_api_url = "https://archive-api.open-meteo.com/v1/archive"

    # Store the downloaded batches
    region_frames = []

    # Download coordinates in small batches
    for start_index in range(0, len(region_coordinates), batch_size):

        # Define a unique filename for each batch
        output_file = output_folder / (
            f"{region}_{start_date}_{end_date}_"
            f"batch_{start_index}_size_{batch_size}.parquet"
        )

        # Reuse previously downloaded data
        if output_file.exists():
            batch_df = pd.read_parquet(output_file)
            region_frames.append(batch_df)
            continue

        # Select coordinates for the current batch
        batch_coordinates = region_coordinates.iloc[
            start_index:start_index + batch_size
        ]

        # Define the API request parameters
        weather_params = {
            "latitude": batch_coordinates["latitude"].tolist(),
            "longitude": batch_coordinates["longitude"].tolist(),
            "start_date": start_date,
            "end_date": end_date,
            "hourly": ["temperature_2m", "precipitation"],
            "models": "era5"
        }

        # Retry when the API rate limit is reached
        max_attempts = 5

        for attempt in range(max_attempts):
            try:
                weather_responses = openmeteo.weather_api(
                    weather_api_url,
                    params=weather_params
                )
                break

            except Exception as error:
                error_message = str(error).lower()

                # Only wait automatically for rate-limit errors
                if "429" not in error_message and "rate limit" not in error_message:
                    raise

                if attempt == max_attempts - 1:
                    raise RuntimeError(
                        "API rate limit still reached after several retries."
                    ) from error

                # Inform Streamlit that the download is temporarily paused
                if status_callback is not None:
                    status_callback(
                        "Open-Meteo API rate limit reached. "
                        "Waiting 60 seconds before retrying..."
                    )

                time.sleep(60)

        # Store weather observations for each location
        location_frames = []

        for location_index, location_response in enumerate(weather_responses):

            # Access hourly weather data
            hourly_data = location_response.Hourly()

            # Extract temperature and precipitation
            location_temperature = hourly_data.Variables(0).ValuesAsNumpy()
            location_precipitation = hourly_data.Variables(1).ValuesAsNumpy()

            # Create timestamps for hourly observations
            hourly_times = pd.date_range(
                start=pd.to_datetime(hourly_data.Time(), unit="s", utc=True),
                end=pd.to_datetime(hourly_data.TimeEnd(), unit="s", utc=True),
                freq=pd.Timedelta(seconds=hourly_data.Interval()),
                inclusive="left"
            )

            # Create a DataFrame for the current location
            location_df = pd.DataFrame({
                "time": hourly_times,
                "latitude": batch_coordinates.iloc[location_index]["latitude"],
                "longitude": batch_coordinates.iloc[location_index]["longitude"],
                "temperature_2m": location_temperature,
                "precipitation": location_precipitation
            })

            location_frames.append(location_df)

        # Combine the locations in this batch
        batch_df = pd.concat(location_frames, ignore_index=True)

        # Save the batch so it can be reused
        batch_df.to_parquet(output_file, index=False)

        region_frames.append(batch_df)

        # Report download progress
        if status_callback is not None:
            completed = min(
                start_index + batch_size,
                len(region_coordinates)
            )
            status_callback(
                f"Downloaded {completed} of "
                f"{len(region_coordinates)} locations."
            )

    # Combine all downloaded batches
    region_weather_df = pd.concat(
        region_frames,
        ignore_index=True
    )

    return region_weather_df


# ---------------------------------------------------------
# SHARED WEATHER PLOT DESIGN
# ---------------------------------------------------------

# Apply consistent styling to all meteorological plots
def apply_weather_plot_theme(fig, title, yaxis_title):

    fig.update_layout(
        template="hydro",
        title=title,
        xaxis_title="Time",
        yaxis_title=yaxis_title,
        height=500,
        hovermode="closest",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0
        ),
        margin=dict(
            l=60,
            r=30,
            t=110,
            b=60
        )
    )

    return fig


# ---------------------------------------------------------
# PRECIPITATION DCT AND SPC
# ---------------------------------------------------------

# Detect precipitation outliers using DCT and robust SPC
def detect_precipitation_outliers(data, cutoff=30, n_std=3):

    # Extract precipitation values and time
    values = data["mean_precipitation"].to_numpy()
    time = data["time"].to_numpy()

    # Apply DCT and remove low-frequency components
    coefficients = dct(values, norm="ortho")
    filtered = coefficients.copy()
    filtered[:cutoff] = 0

    # Reconstruct high-frequency variations
    highpass = idct(filtered, norm="ortho")

    # Calculate robust SPC limits using median and MAD
    median = np.median(highpass)
    mad = np.median(np.abs(highpass - median))
    robust_std = 1.4826 * mad

    lower_limit = median - n_std * robust_std
    upper_limit = median + n_std * robust_std

    # Identify outliers
    outliers = (
        (highpass < lower_limit) |
        (highpass > upper_limit)
    )

    # Calculate summary statistics
    count = int(np.sum(outliers))
    percentage = 100 * count / len(values)

    # Convert SPC limits back to the original precipitation scale
    baseline = values - highpass
    upper_original = baseline + upper_limit
    lower_original = baseline + lower_limit

    # Create an interactive precipitation outlier plot
    fig = go.Figure()

    # Plot the original mean precipitation
    fig.add_trace(
        go.Scatter(
            x=time,
            y=values,
            mode="lines",
            name="Mean precipitation",
            line=dict(
                color=WATER_BLUE,
                width=1
            ),
            hovertemplate=(
                "%{y:.3f} mm"
                "<extra>Mean precipitation</extra>"
            )
        )
    )

    # Plot the upper SPC limit
    fig.add_trace(
        go.Scatter(
            x=time,
            y=upper_original,
            mode="lines",
            name="Upper SPC limit",
            line=dict(
                color=BAUXITE_RED,
                dash="dash",
                width=1.5
            ),
            hovertemplate=(
                "%{y:.3f} mm"
                "<extra>Upper SPC limit</extra>"
            )
        )
    )

    # Plot the lower SPC limit
    fig.add_trace(
        go.Scatter(
            x=time,
            y=lower_original,
            mode="lines",
            name="Lower SPC limit",
            line=dict(
                color=BAUXITE_RED,
                dash="dot",
                width=1.5
            ),
            hovertemplate=(
                "%{y:.3f} mm"
                "<extra>Lower SPC limit</extra>"
            )
        )
    )

    # Highlight detected outliers
    fig.add_trace(
        go.Scatter(
            x=time[outliers],
            y=values[outliers],
            mode="markers",
            name="Outliers",
            marker=dict(
                color=BAUXITE_RED,
                size=5,
                opacity=0.8
            ),
            hovertemplate=(
                "%{y:.3f} mm"
                "<extra>Outlier</extra>"
            )
        )
    )

    # Apply the shared Hydro-inspired theme
    fig = apply_weather_plot_theme(
        fig,
        title="Precipitation Outliers (2024) - DCT + SPC",
        yaxis_title="Mean precipitation (mm)"
    )

    # Return the figure and summary statistics
    summary = {
        "DCT cutoff": cutoff,
        "Standard deviations": n_std,
        "Number of outliers": count,
        "Percentage (%)": round(percentage, 2)
    }

    return fig, summary


# ---------------------------------------------------------
# TEMPERATURE DCT / SATV / SPC
# ---------------------------------------------------------

# Calculate seasonally adjusted temperature variations
# using DCT high-pass filtering
def detect_temperature_satv(
    temperature_data,
    cutoff=30,
    n_std=3
):

    # Prepare a chronological series of hourly mean temperatures
    data = temperature_data.sort_values("time").dropna(
        subset=["time", "mean_temperature"]
    ).copy()

    values = data["mean_temperature"].to_numpy(dtype=float)

    if len(values) < 3:
        raise ValueError(
            "Not enough temperature observations for DCT filtering."
        )

    # Remove the slowly varying components of the temperature signal
    coefficients = dct(values, norm="ortho")
    filtered_coefficients = coefficients.copy()
    filtered_coefficients[:min(cutoff, len(values))] = 0

    satv = idct(filtered_coefficients, norm="ortho")

    # Calculate robust SPC thresholds for the filtered temperature variations
    median = np.median(satv)
    mad = np.median(np.abs(satv - median))
    robust_std = 1.4826 * mad

    lower_limit = median - n_std * robust_std
    upper_limit = median + n_std * robust_std

    # Identify outliers
    outliers = (
        (satv < lower_limit) |
        (satv > upper_limit)
    )

    # Create an interactive SATV plot
    fig = go.Figure()

    # Plot SATV itself, rather than the original temperature series
    fig.add_trace(
        go.Scatter(
            x=data["time"],
            y=satv,
            mode="lines",
            name="SATV (DCT high-pass filtered temperature)",
            line=dict(
                color=DARK_BLUE,
                width=1
            ),
            hovertemplate=(
                "%{y:.2f} °C"
                "<extra>SATV</extra>"
            )
        )
    )

    # Add a horizontal zero reference line
    fig.add_hline(
        y=0,
        line_color=GREY,
        line_width=1
    )

    # Plot the upper SPC limit
    fig.add_trace(
        go.Scatter(
            x=data["time"],
            y=np.full(len(data), upper_limit),
            mode="lines",
            name="Upper SPC limit",
            line=dict(
                color=BAUXITE_RED,
                dash="dash",
                width=1.5
            ),
            hovertemplate=(
                "%{y:.2f} °C"
                "<extra>Upper SPC limit</extra>"
            )
        )
    )

    # Plot the lower SPC limit
    fig.add_trace(
        go.Scatter(
            x=data["time"],
            y=np.full(len(data), lower_limit),
            mode="lines",
            name="Lower SPC limit",
            line=dict(
                color=BAUXITE_RED,
                dash="dot",
                width=1.5
            ),
            hovertemplate=(
                "%{y:.2f} °C"
                "<extra>Lower SPC limit</extra>"
            )
        )
    )

    # Highlight detected temperature outliers
    fig.add_trace(
        go.Scatter(
            x=data.loc[outliers, "time"],
            y=satv[outliers],
            mode="markers",
            name="Outliers",
            marker=dict(
                color=BAUXITE_RED,
                size=5,
                opacity=0.8
            ),
            hovertemplate=(
                "%{y:.2f} °C"
                "<extra>Outlier</extra>"
            )
        )
    )

    # Apply the shared Hydro-inspired theme
    fig = apply_weather_plot_theme(
        fig,
        title="Seasonally Adjusted Temperature Variations (2024) - DCT",
        yaxis_title="Temperature variation (°C)"
    )

    # Calculate summary statistics
    count = int(np.sum(outliers))

    summary = {
        "DCT cutoff": cutoff,
        "Standard deviations": n_std,
        "Number of outliers": count,
        "Percentage (%)": round(100 * count / len(values), 2)
    }

    return fig, summary


# ---------------------------------------------------------
# TEMPERATURE LOF
# ---------------------------------------------------------

# Detect temperature anomalies using trend-adjusted LOF
def detect_temperature_anomalies(
    temperature_data,
    contamination=0.01,
    n_neighbors=20,
    window_days=7
):

    # Sort observations chronologically
    data = temperature_data.sort_values("time").copy()

    # Calculate a centered moving average
    window_hours = window_days * 24

    data["temperature_trend"] = (
        data["mean_temperature"]
        .rolling(
            window=window_hours,
            center=True,
            min_periods=1
        )
        .mean()
    )

    # Calculate deviations from the local trend
    data["temperature_deviation"] = (
        data["mean_temperature"] - data["temperature_trend"]
    )

    # Apply LOF to temperature deviations
    values = data[["temperature_deviation"]].to_numpy()

    lof = LocalOutlierFactor(
        n_neighbors=n_neighbors,
        contamination=contamination
    )

    labels = lof.fit_predict(values)
    outliers = labels == -1

    # Calculate summary statistics
    count = int(np.sum(outliers))
    percentage = 100 * count / len(data)

    # Create an interactive temperature anomaly plot
    fig = go.Figure()

    # Plot the original mean temperature
    fig.add_trace(
        go.Scatter(
            x=data["time"],
            y=data["mean_temperature"],
            mode="lines",
            name="Mean temperature",
            line=dict(
                color=DARK_BLUE,
                width=1
            ),
            hovertemplate=(
                "%{y:.2f} °C"
                "<extra>Mean temperature</extra>"
            )
        )
    )

    # Highlight detected temperature anomalies
    fig.add_trace(
        go.Scatter(
            x=data.loc[outliers, "time"],
            y=data.loc[outliers, "mean_temperature"],
            mode="markers",
            name="LOF anomalies",
            marker=dict(
                color=BAUXITE_RED,
                size=6,
                opacity=0.8
            ),
            hovertemplate=(
                "%{y:.2f} °C"
                "<extra>LOF anomaly</extra>"
            )
        )
    )

    # Apply the shared Hydro-inspired theme
    fig = apply_weather_plot_theme(
        fig,
        title="Temperature Anomalies (2024) - Trend-adjusted LOF",
        yaxis_title="Mean temperature (°C)"
    )

    # Return plot and anomaly summary
    summary = {
        "Contamination": contamination,
        "Neighbors": n_neighbors,
        "Window (days)": window_days,
        "Number of anomalies": count,
        "Percentage (%)": round(percentage, 2)
    }

    return fig, summary


# ---------------------------------------------------------
# PRECIPITATION LOF
# ---------------------------------------------------------

# Detect precipitation anomalies using LOF on non-zero rainfall
def detect_precipitation_anomalies(
    precipitation_data,
    contamination=0.01,
    n_neighbors=20
):

    # Sort observations chronologically
    data = precipitation_data.sort_values("time").copy()

    # Remove missing values
    data = data.dropna(
        subset=["mean_precipitation"]
    )

    # Only analyze hours with measurable precipitation
    rainy_data = data[
        data["mean_precipitation"] > 0
    ].copy()

    # Check that enough rainy observations are available
    if len(rainy_data) < 3:
        raise ValueError(
            "Not enough rainy observations for precipitation LOF."
        )

    # Apply a log transformation to reduce precipitation skewness
    rainy_data["log_precipitation"] = np.log1p(
        rainy_data["mean_precipitation"]
    )

    # Adjust the number of neighbors to the available observations
    actual_neighbors = min(
        n_neighbors,
        len(rainy_data) - 1
    )

    # Apply LOF to precipitation intensity
    values = rainy_data[["log_precipitation"]].to_numpy()

    lof = LocalOutlierFactor(
        n_neighbors=actual_neighbors,
        contamination=contamination
    )

    labels = lof.fit_predict(values)
    outliers = labels == -1

    # Calculate summary statistics for rainy observations
    count = int(np.sum(outliers))
    percentage = 100 * count / len(rainy_data)

    # Create an interactive precipitation anomaly plot
    fig = go.Figure()

    # Plot the complete precipitation time series
    fig.add_trace(
        go.Scatter(
            x=data["time"],
            y=data["mean_precipitation"],
            mode="lines",
            name="Mean precipitation",
            line=dict(
                color=WATER_BLUE,
                width=1
            ),
            hovertemplate=(
                "%{y:.3f} mm"
                "<extra>Mean precipitation</extra>"
            )
        )
    )

    # Highlight anomalous rainy observations
    fig.add_trace(
        go.Scatter(
            x=rainy_data.loc[outliers, "time"],
            y=rainy_data.loc[outliers, "mean_precipitation"],
            mode="markers",
            name="LOF anomalies",
            marker=dict(
                color=BAUXITE_RED,
                size=6,
                opacity=0.8
            ),
            hovertemplate=(
                "%{y:.3f} mm"
                "<extra>LOF anomaly</extra>"
            )
        )
    )

    # Apply the shared Hydro-inspired theme
    fig = apply_weather_plot_theme(
        fig,
        title="Precipitation Anomalies (2024) - Rainfall intensity LOF",
        yaxis_title="Mean precipitation (mm)"
    )

    # Return plot and anomaly summary
    summary = {
        "Contamination": contamination,
        "Neighbors": actual_neighbors,
        "Number of anomalies": count,
        "Percentage (%)": round(percentage, 2)
    }

    return fig, summary