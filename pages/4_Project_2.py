import calendar
from urllib.parse import quote_plus

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
from pymongo import MongoClient


st.title("Cross-Border Electricity Flow")
st.write(
    "Explore electricity imports and exports between Norway and neighbouring "
    "countries using daily ENTSO-E data stored in MongoDB."
)


# Connect to MongoDB using credentials stored in Streamlit Secrets.
@st.cache_resource
def get_collection():
    username = quote_plus(st.secrets["mongodb"]["username"])
    password = quote_plus(st.secrets["mongodb"]["password"])
    uri = f"mongodb+srv://{username}:{password}@ind320.0zlleiy.mongodb.net/"

    client = MongoClient(uri, serverSelectionTimeoutMS=10000)
    client.admin.command("ping")
    return client["ind320_project2"]["entsoe_daily_flows"]


# Cache the downloaded daily records to avoid querying MongoDB on every click.
@st.cache_data(ttl=3600)
def load_data():
    collection = get_collection()
    records = list(collection.find({}, {"_id": 0}))
    data = pd.DataFrame(records)
    if data.empty:
        return data
    data["date"] = pd.to_datetime(data["date"])
    data["total_mwh"] = pd.to_numeric(data["total_mwh"], errors="coerce")
    return data


try:
    df = load_data()

    if df.empty:
        st.warning("No electricity flow data was found in MongoDB.")
        st.stop()

    # Create one label for each connection, regardless of flow direction.
    connections = sorted(
        {
            " ↔ ".join(sorted((out_area, in_area)))
            for out_area, in_area in zip(df["out_area"], df["in_area"])
        }
    )
    years = sorted(df["date"].dt.year.unique().tolist())

    # Display the controls and visualizations in two columns.
    left_col, right_col = st.columns(2, gap="large")

    with left_col:
        st.subheader("Annual import and export")

        # The assignment specifies radio buttons for selecting a connection.
        selected_connection = st.radio("Select connection", connections)
        selected_year = st.selectbox(
            "Select year",
            years,
            index=years.index(2025) if 2025 in years else len(years) - 1,
        )

    # Keep only the chosen year and both directions of the chosen connection.
    area_1, area_2 = selected_connection.split(" ↔ ")
    year_df = df[df["date"].dt.year == selected_year]
    connection_df = year_df[
        (
            (year_df["out_area"] == area_1)
            & (year_df["in_area"] == area_2)
        )
        | (
            (year_df["out_area"] == area_2)
            & (year_df["in_area"] == area_1)
        )
    ]

    # Calculate the annual energy total for each direction (MWh).
    direction_totals = connection_df.groupby("direction")["total_mwh"].sum()
    direction_totals = direction_totals.reindex(["Import", "Export"], fill_value=0)

    with left_col:
        if direction_totals.sum() > 0:
            fig, ax = plt.subplots(figsize=(5, 4))
            ax.pie(
                direction_totals,
                labels=direction_totals.index,
                autopct="%1.1f%%",
                startangle=90,
                colors=["#B65C91", "#258A93"],
            )
            ax.set_title(f"Import vs Export: {selected_connection} ({selected_year})")
            st.pyplot(fig)
            plt.close(fig)
            st.caption("Annual total electricity flow, measured in MWh.")
            st.dataframe(
                direction_totals.rename("Total energy (MWh)").to_frame(),
                use_container_width=True,
            )
        else:
            st.info(
            "No data available for the selected period. "
            "Electricity flow data is only available from October 2024 onwards. "
            "Please select a month within the available date range."
            )

    with right_col:
        st.subheader("Daily electricity flow")

        # The assignment specifies pills with multiple month selections.
        month_options = list(range(1, 13))
        selected_months = st.pills(
            "Select months",
            options=month_options,
            default=[1],
            selection_mode="multi",
            format_func=lambda month: calendar.month_abbr[month],
        )

        if not selected_months:
            st.info("Select at least one month to display the line chart.")
        else:
            # Filter the selected connection to the chosen months.
            month_df = connection_df[
                connection_df["date"].dt.month.isin(selected_months)
            ]

            if month_df.empty:
                st.info("No data is available for the selected months.")
            else:
                # Place import and export in separate columns for plotting.
                daily_plot = month_df.pivot_table(
                    index="date",
                    columns="direction",
                    values="total_mwh",
                    aggfunc="sum",
                ).sort_index()

                fig, ax = plt.subplots(figsize=(7, 4))

                daily_plot = daily_plot.reindex(
                    columns=["Import", "Export"]
                )

                daily_plot.plot(
                    ax=ax,
                    color=["#B65C91", "#258A93"],
                    linewidth=2,
                )
                ax.set_title(f"Daily flow: {selected_connection} ({selected_year})")
                ax.set_xlabel("Date")
                ax.set_ylabel("Energy (MWh)")
                ax.legend(title="Direction")
                fig.autofmt_xdate()
                fig.tight_layout()
                st.pyplot(fig)
                plt.close(fig)

    # Document where the displayed data comes from.
    with st.expander("Data source and processing"):
        st.write(
            "The electricity transfer data comes from the ENTSO-E Transparency "
            "Platform API and covers cross-border flows between Norwegian "
            "electricity areas and neighbouring countries."
        )
        st.write(
            "The original API records were processed with Apache Spark, "
            "stored in Apache Cassandra, read back through Spark, and then "
            "aggregated to daily import/export totals before being uploaded "
            "to MongoDB Atlas. This Streamlit page reads those daily totals "
            "directly from MongoDB."
        )
        st.write(
            "The pie chart compares total imported and exported energy for "
            "the selected connection and year. The line chart shows daily "
            "energy totals for the selected months. All values are in MWh."
        )
        st.caption(
            "The dataset covers approximately two years; the first and last "
            "calendar years may therefore contain only partial data."
        )

except Exception as e:
    st.error(f"An error occurred: {type(e).__name__}: {e}")