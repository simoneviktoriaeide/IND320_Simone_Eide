from pathlib import Path
import pandas as pd


# Folder containing previously downloaded weather data
WEATHER_FOLDER = (
    Path(__file__).resolve().parent
    / "data"
    / "weather_data"
    / "streamlit"
)

# Match map area names with weather data filenames
REGION_MAPPING = {
    "EL1": "NO1",
    "EL2": "NO2",
    "EL3": "NO3",
    "EL4": "NO4",
    "EL5": "NO5",
    "VASS1": "East",
    "VASS2": "West",
    "VASS3": "North"
}


def get_weather_values(area_type, start_date, end_date, property_name):
    """
    Calculate weather values for each geographical area
    during the selected period.
    """

    # Choose which geographical areas to calculate
    if area_type == "EL":
        area_ids = ["EL1", "EL2", "EL3", "EL4", "EL5"]

    elif area_type == "VASS":
        area_ids = ["VASS1", "VASS2", "VASS3"]

    else:
        raise ValueError(
            "Weather colouring currently supports EL and VASS."
        )

    # Choose the weather variable and aggregation method
    if property_name == "Temperature":
        column = "temperature_2m"

    elif property_name == "Precipitation":
        column = "precipitation"

    else:
        raise ValueError(f"Unknown weather property: {property_name}")

    weather_values = {}

    for area_id in area_ids:

        # Find the corresponding weather region
        region = REGION_MAPPING[area_id]

        # Find existing Parquet files for this region
        files = sorted(
            WEATHER_FOLDER.glob(
                f"{region}_2024-01-01_2024-12-31_batch_*.parquet"
            )
        )

        if not files:
            raise FileNotFoundError(
                f"No saved weather files found for {region}."
            )

        # Read only the columns needed for the calculation
        frames = [
            pd.read_parquet(file, columns=["time", column])
            for file in files
        ]

        weather_df = pd.concat(frames, ignore_index=True)

        # Filter observations to the selected period
        weather_df["time"] = pd.to_datetime(
            weather_df["time"], utc=True
        )

        start = pd.Timestamp(start_date).tz_localize("UTC")
        end = (
            pd.Timestamp(end_date).tz_localize("UTC")
            + pd.Timedelta(days=1)
        )

        selected_data = weather_df[
            (weather_df["time"] >= start)
            & (weather_df["time"] < end)
        ]

        if selected_data.empty:
            weather_values[area_id] = None
            continue

        if property_name == "Temperature":

            # Average temperature across locations and hours
            value = selected_data[column].mean()

        else:

            # Total precipitation per location, averaged
            # across the sampled locations
            hourly_mean = selected_data.groupby("time")[column].mean()
            value = hourly_mean.sum()

        weather_values[area_id] = round(float(value), 2)

    return weather_values