import requests
import pandas as pd
import streamlit as st
import plotly.express as px

from plot_theme import (
    DARK_BLUE,
    WATER_BLUE
)


# ---------------------------------------------------------
# NORGES BANK API
# ---------------------------------------------------------

@st.cache_data(ttl=3600)
def get_exchange_rates_df(currency, start_date, end_date):
    """
    Download daily exchange rates from Norges Bank.
    Based on the function from Project 4.
    """

    url = (
        "https://data.norges-bank.no/api/data/EXR/"
        f"B.{currency}.NOK.SP"
    )

    params = {
        "startPeriod": str(start_date),
        "endPeriod": str(end_date),
        "format": "sdmx-json",
        "locale": "no"
    }

    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()

    data = response.json()

    # Extract dates from the API response
    time_values = (
        data["data"]["structure"]
        ["dimensions"]["observation"][0]["values"]
    )

    # Extract exchange rate observations
    series = data["data"]["dataSets"][0]["series"]
    observations = list(series.values())[0]["observations"]

    # Match each observation with its date
    rows = []

    for i, item in enumerate(time_values):
        observation = observations.get(str(i))

        if observation is not None and observation[0] is not None:
            rows.append({
                "Date": pd.to_datetime(item["id"]),
                f"{currency}_NOK": float(observation[0])
            })

    return pd.DataFrame(
        rows,
        columns=["Date", f"{currency}_NOK"]
    )


@st.cache_data(ttl=3600)
def load_exchange_rates(start_date, end_date):

    # Download USD and EUR exchange rates
    usd_df = get_exchange_rates_df(
        "USD", start_date, end_date
    )

    eur_df = get_exchange_rates_df(
        "EUR", start_date, end_date
    )

    # Combine both currencies using their dates
    exchange_rates_df = pd.merge(
        usd_df,
        eur_df,
        on="Date",
        how="outer"
    )

    return exchange_rates_df.sort_values("Date")


# ---------------------------------------------------------
# PAGE HEADER
# ---------------------------------------------------------

st.title("Currency Exchange Rates")

st.write(
    "Explore historical exchange rates between the "
    "Norwegian krone (NOK), US dollar (USD), "
    "and euro (EUR), using data from Norges Bank."
)

st.caption("Source: Norges Bank API")

st.divider()


# ---------------------------------------------------------
# USER SELECTIONS
# ---------------------------------------------------------

st.subheader("Select Data")

col1, col2 = st.columns(2)

with col1:
    selected_currencies = st.multiselect(
        "Select currencies",
        options=["USD", "EUR"],
        default=["USD", "EUR"]
    )

with col2:
    selected_period = st.date_input(
        "Select date range",
        value=(
            pd.Timestamp("2024-01-01").date(),
            pd.Timestamp("2025-12-31").date()
        )
    )

if not selected_currencies:
    st.info("Please select at least one currency.")
    st.stop()

if len(selected_period) != 2:
    st.info("Please select a start and end date.")
    st.stop()

start_date, end_date = selected_period

if start_date > end_date:
    st.error("Start date must be before end date.")
    st.stop()


# ---------------------------------------------------------
# LOAD DATA
# ---------------------------------------------------------

try:
    exchange_rates_df = load_exchange_rates(
        start_date,
        end_date
    )

except requests.RequestException as error:
    st.error(f"Could not retrieve data from Norges Bank: {error}")
    st.stop()

except (KeyError, IndexError, ValueError) as error:
    st.error(f"Unexpected API response: {error}")
    st.stop()

if exchange_rates_df.empty:
    st.warning("No exchange rate data for the selected period.")
    st.stop()

selected_columns = [
    f"{currency}_NOK"
    for currency in selected_currencies
]

plot_data = exchange_rates_df[
    ["Date"] + selected_columns
].dropna(subset=selected_columns, how="all")

if plot_data.empty:
    st.warning("No observations for the selected currencies.")
    st.stop()


# ---------------------------------------------------------
# DATA OVERVIEW
# ---------------------------------------------------------

st.subheader("Exchange Rate Overview")

metric_columns = st.columns(len(selected_currencies))

for column, currency in zip(
    metric_columns,
    selected_currencies
):
    currency_column = f"{currency}_NOK"

    valid = plot_data[
        ["Date", currency_column]
    ].dropna().sort_values("Date")

    if valid.empty:
        continue

    latest = valid[currency_column].iloc[-1]
    previous = (
        valid[currency_column].iloc[-2]
        if len(valid) > 1 else None
    )

    with column:
        st.metric(
            label=f"{currency}/NOK",
            value=f"{latest:.4f} NOK",
            delta=(
                f"{latest - previous:+.4f}"
                if previous is not None else None
            )
        )

st.caption(
    "Metrics show the latest available rate in the "
    "selected period. The change is relative to the "
    "previous available observation."
)

st.divider()


# ---------------------------------------------------------
# INTERACTIVE PLOTLY CHART
# ---------------------------------------------------------

st.subheader("Exchange Rate Development")

# Convert wide data into long format for Plotly
long_data = plot_data.melt(
    id_vars="Date",
    value_vars=selected_columns,
    var_name="Currency",
    value_name="Exchange Rate"
).dropna()

# Use readable currency labels in the plot
long_data["Currency"] = long_data["Currency"].replace({
    "USD_NOK": "USD/NOK",
    "EUR_NOK": "EUR/NOK"
})

# Create an interactive exchange rate plot
# using the shared Hydro-inspired colour palette
fig = px.line(
    long_data,
    x="Date",
    y="Exchange Rate",
    color="Currency",
    color_discrete_map={
        "USD/NOK": DARK_BLUE,
        "EUR/NOK": WATER_BLUE
    },
    labels={
        "Date": "Date",
        "Exchange Rate": "NOK per unit of foreign currency",
        "Currency": "Currency"
    },
    template="hydro"
)

# Improve line visibility and hover information
fig.update_traces(
    line=dict(width=2),
    hovertemplate="%{y:.4f} NOK"
)

# Use different line styles to distinguish the currencies
fig.update_traces(
    line=dict(dash="solid"),
    selector=dict(name="USD/NOK")
)

fig.update_traces(
    line=dict(dash="dash"),
    selector=dict(name="EUR/NOK")
)

# Apply consistent layout settings
fig.update_layout(
    template="hydro",
    height=500,
    hovermode="x unified",
    legend_title_text="Currency",
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
        t=60,
        b=60
    )
)

# Display the plot without overriding the shared theme
st.plotly_chart(
    fig,
    use_container_width=True,
    theme=None
)

st.caption(
    "A higher exchange rate means that more Norwegian "
    "kroner are needed to purchase one unit of the "
    "selected foreign currency."
)


# ---------------------------------------------------------
# DATA TABLE
# ---------------------------------------------------------

st.divider()

st.subheader("Exchange Rate Data")

st.dataframe(
    plot_data.sort_values("Date", ascending=False),
    use_container_width=True,
    hide_index=True
)

st.caption(
    f"Number of dates with available observations: "
    f"{len(plot_data)}"
)


# ---------------------------------------------------------
# DATA SOURCE INFORMATION
# ---------------------------------------------------------

with st.expander("Data Source and Processing"):

    st.write(
        "Exchange rates are retrieved directly from the "
        "Norges Bank API."
    )

    st.write(
        "The API provides daily observations for USD/NOK "
        "and EUR/NOK. The datasets are combined by date."
    )

    st.write(
        "Missing observations may occur on weekends "
        "and holidays when exchange rates are not published."
    )

    st.write(
        "The dates are treated as daily observations, "
        "without timezone conversion."
    )