
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from data_loader import load_data
from area_selector import select_area
from weather_utils import download_streamlit_weather
from plotly.subplots import make_subplots
from map_utils import load_geojson
from plot_theme import DARK_BLUE, WATER_BLUE, LIGHT_BLUE, BAUXITE_RED, GREY, WHITE


# ---------------------------------------------------------
# PAGE HEADER
# ---------------------------------------------------------

st.title("Prediction of Reservoir Fill Level")

st.write(
    "Explore relationships between weather and reservoir filling, "
    "and prepare for forecasting reservoir levels."
)


# ---------------------------------------------------------
# AREA SELECTION
# ---------------------------------------------------------

# Match reservoir areas to the weather regions
AREA_TO_WEATHER_REGION = {
    "EL1": ["NO1"],
    "EL2": ["NO2"],
    "EL3": ["NO3"],
    "EL4": ["NO4"],
    "EL5": ["NO5"],
    "VASS1": ["East"],
    "VASS2": ["West"],
    "VASS3": ["North"],
    "NO0": ["East", "West", "North"],
}

# Use the shared area selector
selected_area = select_area()


# ---------------------------------------------------------
# ANALYSIS TABS
# ---------------------------------------------------------

correlation_tab, forecasting_tab = st.tabs([
    "Sliding Window Correlation",
    "Forecasting"
])


# ---------------------------------------------------------
# TAB 1: SLIDING WINDOW CORRELATION
# ---------------------------------------------------------

with correlation_tab:

    st.subheader("Weather and Reservoir Correlation")

    st.write(
        "Investigate how the correlation between weather and reservoir "
        "fill levels changes over time."
    )

    # Select weather and reservoir variables
    weather_property = st.selectbox(
        "Weather property",
        ["Precipitation", "Temperature"]
    )

    reservoir_property = st.selectbox(
        "Reservoir variable",
        ["Weekly change in fill level", "Fill level"]
    )

    # Select correlation settings
    col1, col2 = st.columns(2)

    with col1:
        window_length = st.slider(
            "Window length (weeks)",
            min_value=4,
            max_value=40,
            value=12
        )

    with col2:
        lag = st.slider(
            "Weather lag (weeks)",
            min_value=0,
            max_value=12,
            value=0
        )

    st.caption(
        "A lag of 2 weeks compares weather in a given week with "
        "reservoir values two weeks later."
    )

    # Load reservoir data from the NVE API
    try:
        reservoir_df = load_data().copy()

        # Create area labels such as EL1 and VASS1
        reservoir_df["area"] = (
            reservoir_df["omrType"].astype(str)
            + reservoir_df["omrnr"].astype(str)
        )

        # Convert dates to datetime
        reservoir_df["dato_Id"] = pd.to_datetime(
            reservoir_df["dato_Id"],
            errors="coerce"
        )

        # Keep observations for the selected area
        reservoir_df = reservoir_df.loc[
            reservoir_df["area"] == selected_area
        ].copy()

    except Exception as error:
        st.error(f"Could not load reservoir data: {error}")
        st.stop()

    if reservoir_df.empty:
        st.warning(
            "No reservoir observations found for the selected area."
        )
        st.stop()

    # Find the weather regions for the selected area
    weather_regions = AREA_TO_WEATHER_REGION.get(selected_area)

    if not weather_regions:
        st.error(
            "No matching weather region was found for this area."
        )
        st.stop()

    # Reuse weather data loaded on the meteorological page
    weather_key = tuple(weather_regions)

    cached_weather = st.session_state.get(
        "weather_data", {}
    )

    # Load weather data if it is not already available
    if weather_key not in cached_weather:

        st.info(
            "Weather data is not loaded for this area. "
            "Click below to load it, or load it first "
            "on the Meteorological Data page."
        )

        if st.button("Load Weather Data", type="primary"):

            try:
                with st.spinner("Loading weather data..."):

                    frames = [
                        download_streamlit_weather(
                            region=region,
                            start_date="2024-01-01",
                            end_date="2024-12-31"
                        )
                        for region in weather_regions
                    ]

                    st.session_state.setdefault(
                        "weather_data", {}
                    )[weather_key] = pd.concat(
                        frames,
                        ignore_index=True
                    )

                st.rerun()

            except Exception as error:
                st.error(
                    f"Could not load weather data: {error}"
                )

        st.stop()

    # Retrieve the stored weather observations
    weather_df = cached_weather[weather_key].copy()

    weather_df["time"] = pd.to_datetime(
        weather_df["time"],
        utc=True,
        errors="coerce"
    )

    # Select the relevant weather column
    weather_column = (
        "precipitation"
        if weather_property == "Precipitation"
        else "temperature_2m"
    )

    # Calculate mean weather values across locations per hour
    hourly_weather = (
        weather_df
        .groupby("time", as_index=False)[weather_column]
        .mean()
    )

    # Identify ISO year and week for each observation
    hourly_iso = hourly_weather["time"].dt.isocalendar()

    hourly_weather["iso_year"] = hourly_iso.year.astype(int)
    hourly_weather["iso_week"] = hourly_iso.week.astype(int)

    # Sum weekly precipitation or average weekly temperature
    aggregation = (
        "sum"
        if weather_property == "Precipitation"
        else "mean"
    )

    weekly_weather = (
        hourly_weather
        .groupby(["iso_year", "iso_week"], as_index=False)
        [weather_column]
        .agg(aggregation)
        .rename(columns={
            weather_column: "weather_value"
        })
    )

    # Use NVE ISO week information when available
    if {"iso_aar", "iso_uke"}.issubset(
        reservoir_df.columns
    ):

        reservoir_df["iso_year"] = pd.to_numeric(
            reservoir_df["iso_aar"],
            errors="coerce"
        )

        reservoir_df["iso_week"] = pd.to_numeric(
            reservoir_df["iso_uke"],
            errors="coerce"
        )

    else:

        iso_reservoir = (
            reservoir_df["dato_Id"]
            .dt.isocalendar()
        )

        reservoir_df["iso_year"] = iso_reservoir.year
        reservoir_df["iso_week"] = iso_reservoir.week

    # Select the reservoir variable
    reservoir_column = (
        "endring_fyllingsgrad"
        if reservoir_property == "Weekly change in fill level"
        else "fyllingsgrad"
    )

    # Keep reservoir observations for 2024
    reservoir_df = reservoir_df.loc[
        reservoir_df["iso_year"] == 2024
    ].copy()

    # Convert reservoir ratios to percentages
    reservoir_df[reservoir_column] = pd.to_numeric(
        reservoir_df[reservoir_column],
        errors="coerce"
    ) * 100

    # Keep one observation per reporting week
    weekly_reservoir = (
        reservoir_df
        .sort_values("dato_Id")
        .drop_duplicates(
            ["iso_year", "iso_week"],
            keep="last"
        )
        [
            ["iso_year", "iso_week", reservoir_column]
        ]
        .rename(columns={
            reservoir_column: "reservoir_value"
        })
    )

    # Convert ISO year and week to the Monday of each week
    for frame in (weekly_weather, weekly_reservoir):

        frame["week_start"] = pd.to_datetime(
            frame["iso_year"].astype("Int64").astype(str)
            + "-W"
            + frame["iso_week"].astype("Int64").astype(str).str.zfill(2)
            + "-1",
            format="%G-W%V-%u",
            errors="coerce"
        )

    weekly_weather = weekly_weather.sort_values(
        "week_start"
    )

    # Shift weather dates forward to represent the selected lag
    weekly_weather["week_start"] += pd.to_timedelta(
        lag,
        unit="W"
    )

    # Match weekly weather and reservoir observations
    combined = (
        weekly_reservoir[
            ["week_start", "reservoir_value"]
        ]
        .merge(
            weekly_weather[
                ["week_start", "weather_value"]
            ],
            on="week_start",
            how="inner"
        )
        .dropna()
        .sort_values("week_start")
    )

    # Preserve missing weeks rather than treating them as consecutive
    combined = (
        combined
        .set_index("week_start")
        .asfreq("W-MON")
        .reset_index()
    )

    # Calculate Pearson correlation in a moving window
    combined["correlation"] = (
        combined["weather_value"]
        .rolling(
            window=window_length,
            min_periods=window_length
        )
        .corr(combined["reservoir_value"])
    )

    # Keep weeks with valid correlation values
    valid = combined.dropna(
        subset=["correlation"]
    )

    if valid.empty:

        st.warning(
            "Not enough aligned weeks for this window and lag. "
            "Try a shorter window or smaller lag."
        )

    else:

        # Create an interactive Plotly correlation graph
        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=valid["week_start"],
                y=valid["correlation"],
                mode="lines+markers",
                name="Rolling correlation",
                line=dict(
                    color=DARK_BLUE,
                    width=2
                )
            )
        )

        # Add a horizontal reference line at zero
        fig.add_hline(
            y=0,
            line_dash="dash",
            line_color=GREY
        )

        fig.update_layout(
            template="hydro",
            title=(
                f"{weather_property} vs. "
                f"{reservoir_property} — {selected_area}"
            ),
            xaxis_title="Week",
            yaxis_title="Pearson correlation",
            yaxis=dict(
                range=[-1.05, 1.05]
            ),
            hovermode="x unified",
            height=450
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
            theme=None
        )

        # Display correlation statistics
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "Latest correlation",
                f"{valid['correlation'].iloc[-1]:.2f}"
            )

        with col2:
            st.metric(
                "Highest correlation",
                f"{valid['correlation'].max():.2f}"
            )

        with col3:
            st.metric(
                "Lowest correlation",
                f"{valid['correlation'].min():.2f}"
            )

        # Show the aligned data for inspection
        with st.expander("View aligned weekly data"):

            st.dataframe(
                combined,
                use_container_width=True
            )

    st.caption(
        "Weather coverage is currently limited to 2024. "
        "Correlation does not establish causation, and "
        "overlapping windows are not independent."
    )



# ---------------------------------------------------------
# TAB 2: FORECASTING
# ---------------------------------------------------------

with forecasting_tab:

    from statsmodels.tsa.statespace.sarimax import SARIMAX

    st.subheader("Forecasting Reservoir Fill Level")

    st.write(
        "Use a SARIMAX model to forecast reservoir fill levels. "
        "Adjust the training period, model parameters and forecast horizon."
    )

    # -----------------------------------------------------
    # FORECAST SETTINGS
    # -----------------------------------------------------

    forecast_horizon = st.slider(
        "Forecast horizon (weeks)",
        min_value=1,
        max_value=12,
        value=6
    )

    training_years = st.slider(
        "Training period (years)",
        min_value=1,
        max_value=10,
        value=5
    )

    st.markdown("#### SARIMAX parameters")

    col1, col2, col3 = st.columns(3)

    with col1:
        p = st.number_input(
            "AR order (p)",
            min_value=0,
            max_value=3,
            value=1
        )

    with col2:
        d = st.number_input(
            "Differencing (d)",
            min_value=0,
            max_value=2,
            value=1
        )

    with col3:
        q = st.number_input(
            "MA order (q)",
            min_value=0,
            max_value=3,
            value=1
        )

    use_seasonality = st.checkbox(
        "Include yearly seasonality (52 weeks)",
        value=False
    )

    if use_seasonality:

        col1, col2, col3 = st.columns(3)

        with col1:
            P = st.number_input(
                "Seasonal AR (P)",
                min_value=0,
                max_value=2,
                value=1
            )

        with col2:
            D = st.number_input(
                "Seasonal differencing (D)",
                min_value=0,
                max_value=1,
                value=0
            )

        with col3:
            Q = st.number_input(
                "Seasonal MA (Q)",
                min_value=0,
                max_value=2,
                value=0
            )

        seasonal_order = (
            int(P), int(D), int(Q), 52
        )

    else:
        seasonal_order = (0, 0, 0, 0)

    # -----------------------------------------------------
    # EXOGENOUS VARIABLES
    # -----------------------------------------------------

    st.markdown("#### Weather variables")

    use_temperature = st.checkbox(
        "Use temperature",
        value=False
    )

    use_precipitation = st.checkbox(
        "Use precipitation",
        value=False
    )

    use_weather = use_temperature or use_precipitation

    if use_weather:
        st.info(
            "Future weather observations are not known. "
            "The model will use historical weekly weather averages "
            "as an illustrative scenario for the forecast period."
        )

    # -----------------------------------------------------
    # PREPARE RESERVOIR DATA
    # -----------------------------------------------------

    try:

        forecast_df = load_data().copy()

        # Create area identifiers
        forecast_df["area"] = (
            forecast_df["omrType"].astype(str)
            + forecast_df["omrnr"].astype(str)
        )

        forecast_df = forecast_df.loc[
            forecast_df["area"] == selected_area
        ].copy()

        forecast_df["dato_Id"] = pd.to_datetime(
            forecast_df["dato_Id"],
            errors="coerce"
        )

        forecast_df["fyllingsgrad"] = pd.to_numeric(
            forecast_df["fyllingsgrad"],
            errors="coerce"
        )

        # Convert fill level from a ratio to a percentage
        forecast_df["fill_level"] = (
            forecast_df["fyllingsgrad"] * 100
        )

        forecast_df = (
            forecast_df
            .dropna(subset=["dato_Id", "fill_level"])
            .sort_values("dato_Id")
        )

        # Use the reporting week as the time index
        iso_dates = forecast_df["dato_Id"].dt.isocalendar()

        forecast_df["week_start"] = pd.to_datetime(
            iso_dates.year.astype(str)
            + "-W"
            + iso_dates.week.astype(str).str.zfill(2)
            + "-1",
            format="%G-W%V-%u",
            errors="coerce"
        )

        # Keep the latest observation for each week
        weekly_fill = (
            forecast_df
            .drop_duplicates("week_start", keep="last")
            .set_index("week_start")["fill_level"]
            .sort_index()
        )

        # Create a regular weekly time series
        weekly_fill = weekly_fill.asfreq("W-MON")

        # Use the selected number of training years
        if not weekly_fill.empty:

            training_end = weekly_fill.index.max()

            training_start = (
                training_end
                - pd.DateOffset(years=training_years)
            )

            weekly_fill = weekly_fill.loc[
                weekly_fill.index >= training_start
            ]

    except Exception as error:

        st.error(
            f"Could not prepare reservoir data: {error}"
        )

        weekly_fill = pd.Series(dtype=float)

    # -----------------------------------------------------
    # OPTIONAL WEATHER DATA
    # -----------------------------------------------------

    weather_features = []
    weekly_exog = None
    future_exog = None
    weather_error = None

    if use_temperature:
        weather_features.append("temperature_2m")

    if use_precipitation:
        weather_features.append("precipitation")

    if use_weather and not weekly_fill.empty:

        try:

            regions = AREA_TO_WEATHER_REGION[selected_area]

            weather_frames = []

            # Download weather observations for training
            for region in regions:

                region_weather = download_streamlit_weather(
                    region=region,
                    start_date=weekly_fill.index.min().strftime(
                        "%Y-%m-%d"
                    ),
                    end_date=weekly_fill.index.max().strftime(
                        "%Y-%m-%d"
                    )
                )

                weather_frames.append(region_weather)

            historical_weather = pd.concat(
                weather_frames,
                ignore_index=True
            )

            historical_weather["time"] = pd.to_datetime(
                historical_weather["time"],
                utc=True,
                errors="coerce"
            )

            # Aggregate weather across sampled locations
            hourly_values = (
                historical_weather
                .groupby("time")[weather_features]
                .mean()
                .sort_index()
            )

            # Convert hourly weather to weekly weather
            hourly_values.index = (
                hourly_values.index
                .tz_convert("Europe/Oslo")
                .tz_localize(None)
            )

            weekly_weather = pd.DataFrame()

            if use_temperature:

                weekly_weather["temperature_2m"] = (
                    hourly_values["temperature_2m"]
                    .resample("W-MON", label="left", closed="left")
                    .mean()
                )

            if use_precipitation:

                weekly_weather["precipitation"] = (
                    hourly_values["precipitation"]
                    .resample("W-MON", label="left", closed="left")
                    .sum(min_count=1)
                )

            weekly_exog = weekly_weather.reindex(
                weekly_fill.index
            )

            # Build an illustrative future weather scenario
            future_dates = pd.date_range(
                start=weekly_fill.index.max()
                + pd.Timedelta(weeks=1),
                periods=forecast_horizon,
                freq="W-MON"
            )

            # Historical average for each ISO week
            historical_weeks = (
                weekly_weather.index.isocalendar().week
            )

            weather_climatology = (
                weekly_weather
                .groupby(historical_weeks)
                .mean()
            )

            future_values = []

            for future_date in future_dates:

                week_number = future_date.isocalendar().week

                if week_number in weather_climatology.index:

                    values = weather_climatology.loc[
                        week_number
                    ]

                else:

                    values = weekly_weather.mean()

                future_values.append(values.to_dict())

            future_exog = pd.DataFrame(
                future_values,
                index=future_dates
            )[weather_features]

        except Exception as error:

            weather_error = str(error)

    # -----------------------------------------------------
    # RUN SARIMAX MODEL
    # -----------------------------------------------------

    if weekly_fill.empty:

        st.warning(
            "No reservoir data available for the selected area."
        )

    elif weekly_fill.notna().sum() < 30:

        st.warning(
            "Not enough historical observations to fit "
            "the forecasting model."
        )

    elif weather_error is not None:

        st.error(
            f"Could not prepare weather variables: {weather_error}"
        )

    else:

        # Fill short gaps in the reservoir time series
        model_series = weekly_fill.interpolate(
            method="time",
            limit=3
        )

        # Remove any remaining missing values at the edges
        model_series = model_series.dropna()

        # Keep exogenous variables aligned with reservoir dates
        if use_weather:

            model_exog = weekly_exog.reindex(
                model_series.index
            )

            # Fill short gaps in historical weather data
            model_exog = model_exog.interpolate(
                method="time",
                limit=3
            )

            valid_rows = model_exog.notna().all(axis=1)

            model_series = model_series.loc[
                valid_rows
            ]

            model_exog = model_exog.loc[
                valid_rows
            ]

        else:

            model_exog = None

        st.write(
            f"Training observations: {len(model_series)} weeks"
        )

        if len(model_series) < 30:

            st.warning(
                "Not enough aligned observations to fit SARIMAX. "
                "Try disabling weather variables or selecting "
                "a longer training period."
            )

        else:

            if st.button(
                "Generate Forecast",
                type="primary"
            ):

                try:

                    with st.spinner(
                        "Training SARIMAX model..."
                    ):

                        # Define and fit the SARIMAX model
                        model = SARIMAX(
                            endog=model_series,
                            exog=model_exog,
                            order=(
                                int(p), int(d), int(q)
                            ),
                            seasonal_order=seasonal_order,
                            enforce_stationarity=False,
                            enforce_invertibility=False
                        )

                        fitted_model = model.fit(
                            disp=False,
                            maxiter=100
                        )

                        # Forecast future reservoir fill levels
                        forecast_result = (
                            fitted_model.get_forecast(
                                steps=forecast_horizon,
                                exog=(
                                    future_exog
                                    if use_weather
                                    else None
                                )
                            )
                        )

                        predicted_values = (
                            forecast_result.predicted_mean
                        )

                        confidence_intervals = (
                            forecast_result.conf_int(
                                alpha=0.05
                            )
                        )

                        # Build forecast dates from the last
                        # observation actually used by the model
                        forecast_dates = pd.date_range(
                            start=(
                                model_series.index.max()
                                + pd.Timedelta(weeks=1)
                            ),
                            periods=forecast_horizon,
                            freq="W-MON"
                        )

                        # Display predicted fill level in percent
                        # without modifying the fitted model
                        predicted_values = pd.Series(
                            predicted_values.to_numpy(),
                            index=forecast_dates
                        )

                        lower_bound = pd.Series(
                            confidence_intervals.iloc[:, 0].to_numpy(),
                            index=forecast_dates
                        )

                        upper_bound = pd.Series(
                            confidence_intervals.iloc[:, 1].to_numpy(),
                            index=forecast_dates
                        )

                    # ---------------------------------------------
                    # PLOT FORECAST
                    # ---------------------------------------------

                    fig_forecast = go.Figure()

                    fig_forecast.add_trace(
                        go.Scatter(
                            x=model_series.index,
                            y=model_series.values,
                            mode="lines",
                            name="Historical fill level",
                            line=dict(
                                color=DARK_BLUE,
                                width=2
                            )
                        )
                    )

                    fig_forecast.add_trace(
                        go.Scatter(
                            x=forecast_dates,
                            y=predicted_values,
                            mode="lines+markers",
                            name="SARIMAX forecast",
                            line=dict(
                                color=WATER_BLUE,
                                width=3
                            )
                        )
                    )

                    # Upper confidence boundary
                    fig_forecast.add_trace(
                        go.Scatter(
                            x=forecast_dates,
                            y=upper_bound,
                            mode="lines",
                            line=dict(width=0),
                            showlegend=False,
                            hoverinfo="skip"
                        )
                    )

                    # Lower confidence boundary and shaded area
                    fig_forecast.add_trace(
                        go.Scatter(
                            x=forecast_dates,
                            y=lower_bound,
                            mode="lines",
                            line=dict(width=0),
                            fill="tonexty",
                            fillcolor="rgba(131,197,213,0.35)",
                            name="95% confidence interval",
                            hoverinfo="skip"
                        )
                    )

                    fig_forecast.update_layout(
                        template="hydro",
                        title=(
                            "Reservoir Fill Level Forecast "
                            f"— {selected_area}"
                        ),
                        xaxis_title="Week",
                        yaxis_title="Fill level (%)",
                        hovermode="x unified",
                        height=500
                    )

                    st.plotly_chart(
                        fig_forecast,
                        use_container_width=True,
                        theme=None
                    )
                    




                    # ---------------------------------------------
                    # ANIMATED FORECAST MAP
                    # ---------------------------------------------

                    st.markdown("#### Animated Forecast Map")

                    st.write(
                        "Explore how the predicted reservoir fill "
                        "level changes throughout the forecast period."
                    )

                    try:

                        # Identify the selected area type
                        area_type = selected_area.rstrip("0123456789")

                        # Reuse GeoJSON from the main map
                        forecast_geojson = load_geojson(area_type)

                        # Create a map and forecast graph
                        animated_fig = make_subplots(
                            rows=1,
                            cols=2,
                            specs=[[
                                {"type": "choropleth"},
                                {"type": "xy"}
                            ]],
                            column_widths=[0.45, 0.55],
                            subplot_titles=[
                                "Predicted fill level",
                                "Forecast development"
                            ]
                        )

                        # Create the initial map
                        animated_fig.add_trace(
                            go.Choropleth(
                                geojson=forecast_geojson,
                                locations=[selected_area],
                                featureidkey="properties.area_id",
                                z=[float(predicted_values.iloc[0])],
                                colorscale=[
                                     [0, WHITE],
                                     [0.25, "#D6EAF0"],
                                     [0.5, LIGHT_BLUE],
                                     [0.75, WATER_BLUE],
                                     [1, DARK_BLUE]
                                 ],
                                zmin=0,
                                zmax=100,
                                marker_line_color=DARK_BLUE,
                                marker_line_width=2,
                                marker_opacity=0.75,
                                colorbar=dict(
                                    title="Fill (%)",
                                    x=0.43,
                                    len=0.65
                                ),
                                hovertemplate=(
                                    "%{location}<br>"
                                    "Predicted fill: %{z:.1f}%"
                                    "<extra></extra>"
                                )
                            ),
                            row=1,
                            col=1
                        )

                        # Show the complete forecast curve
                        animated_fig.add_trace(
                            go.Scatter(
                                x=forecast_dates,
                                y=predicted_values.values,
                                mode="lines+markers",
                                name="Forecast",
                                line=dict(
                                    color=WATER_BLUE,
                                    width=3
                                )
                            ),
                            row=1,
                            col=2
                        )

                        # Highlight the currently selected week
                        animated_fig.add_trace(
                            go.Scatter(
                                x=[forecast_dates[0]],
                                y=[predicted_values.iloc[0]],
                                mode="markers",
                                name="Selected week",
                                marker=dict(
                                    size=14,
                                    color=BAUXITE_RED
                                )
                            ),
                            row=1,
                            col=2
                        )

                        # Create one animation frame per forecast week
                        frames = []

                        for i, date in enumerate(forecast_dates):

                            fill_value = float(
                                predicted_values.iloc[i]
                            )

                            frames.append(
                                go.Frame(
                                    name=str(i),
                                    data=[
                                        go.Choropleth(
                                            z=[fill_value]
                                        ),
                                        go.Scatter(
                                            x=[date],
                                            y=[fill_value]
                                        )
                                    ],
                                    traces=[0, 2],
                                    layout=go.Layout(
                                        title_text=(
                                            f"{selected_area} — "
                                            f"{date:%d %b %Y} — "
                                            f"{fill_value:.1f}%"
                                        )
                                    )
                                )
                            )

                        animated_fig.frames = frames

                        # Create a slider for forecast dates
                        slider_steps = []

                        for i, date in enumerate(forecast_dates):

                            slider_steps.append(
                                dict(
                                    method="animate",
                                    label=date.strftime("%d %b"),
                                    args=[
                                        [str(i)],
                                        dict(
                                            mode="immediate",
                                            frame=dict(
                                                duration=0,
                                                redraw=True
                                            ),
                                            transition=dict(
                                                duration=0
                                            )
                                        )
                                    ]
                                )
                            )

                        # Configure the geographic map
                        animated_fig.update_geos(
                            scope="europe",
                            projection_type="mercator",
                            center=dict(lat=65, lon=15),
                            lataxis_range=[57, 72],
                            lonaxis_range=[4, 32],
                            showland=True,
                            landcolor=GREY,
                            showcountries=True
                        )

                        # Configure the forecast graph
                        animated_fig.update_xaxes(
                            title_text="Forecast week",
                            row=1,
                            col=2
                        )

                        animated_fig.update_yaxes(
                            title_text="Fill level (%)",
                            range=[
                                min(
                                    0,
                                    float(predicted_values.min())
                                ),
                                max(
                                    100,
                                    float(predicted_values.max())
                                )
                            ],
                            row=1,
                            col=2
                        )

                        # Add animation controls
                        animated_fig.update_layout(
                            template="hydro",
                            title=(
                                f"{selected_area} — "
                                f"{forecast_dates[0]:%d %b %Y} — "
                                f"{predicted_values.iloc[0]:.1f}%"
                            ),
                            height=600,
                            showlegend=False,
                            margin=dict(
                                l=20,
                                r=20,
                                t=90,
                                b=120
                            ),
                            sliders=[
                                dict(
                                    active=0,
                                    currentvalue=dict(
                                        prefix="Forecast date: "
                                    ),
                                    steps=slider_steps,
                                    pad=dict(t=50)
                                )
                            ],
                            updatemenus=[
                                dict(
                                    type="buttons",
                                    direction="left",
                                    x=0,
                                    y=-0.05,
                                    buttons=[
                                        dict(
                                            label="Play",
                                            method="animate",
                                            args=[
                                                None,
                                                dict(
                                                    frame=dict(
                                                        duration=800,
                                                        redraw=True
                                                    ),
                                                    transition=dict(
                                                        duration=0
                                                    ),
                                                    fromcurrent=True
                                                )
                                            ]
                                        ),
                                        dict(
                                            label="Pause",
                                            method="animate",
                                            args=[
                                                [None],
                                                dict(
                                                    mode="immediate",
                                                    frame=dict(
                                                        duration=0,
                                                        redraw=False
                                                    ),
                                                    transition=dict(
                                                        duration=0
                                                    )
                                                )
                                            ]
                                        )
                                    ]
                                )
                            ]
                        )

                        st.plotly_chart(
                            animated_fig,
                            use_container_width=True,
                            theme=None
                        )

                        st.caption(
                            "The map and forecast marker are "
                            "synchronized through the selected "
                            "forecast week. Darker blue indicates "
                            "a higher predicted reservoir fill level."
                        )

                    except Exception as map_error:

                        st.warning(
                            f"Could not display forecast map: "
                            f"{map_error}"
                        )







                    # ---------------------------------------------
                    # FORECAST RESULTS
                    # ---------------------------------------------

                    st.markdown("#### Forecast results")

                    forecast_table = pd.DataFrame({
                        "Week": forecast_dates,
                        "Predicted fill level (%)": (
                            predicted_values.values
                        ),
                        "Lower 95% bound": lower_bound.values,
                        "Upper 95% bound": upper_bound.values
                    })

                    st.dataframe(
                        forecast_table.round(2),
                        use_container_width=True
                    )

                    st.metric(
                        "Final predicted fill level",
                        f"{predicted_values.iloc[-1]:.1f}%"
                    )

                    st.caption(
                        "Confidence intervals describe model "
                        "uncertainty under the fitted assumptions. "
                        "Forecasts may fall outside the physical "
                        "0–100% range because SARIMAX is unconstrained."
                    )

                    st.caption(
                        "Future weather inputs are illustrative "
                        "historical averages, not actual weather forecasts."
                        if use_weather
                        else "This forecast uses historical reservoir "
                        "fill levels without weather variables."
                    )

                except Exception as error:

                    st.error(
                        f"SARIMAX forecasting failed: {error}"
                    )
