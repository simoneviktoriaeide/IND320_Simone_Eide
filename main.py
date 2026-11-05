
import streamlit as st


# ---------------------------------------------------------
# APP CONFIGURATION
# ---------------------------------------------------------

st.set_page_config(
    page_title="Reservoir Insights Norway",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="auto"
)


# ---------------------------------------------------------
# HOME PAGE
# ---------------------------------------------------------

# Define the home page directly in main.py
def show_home():

    st.title("💧 Reservoir Insights Norway")

    st.write(
        "An interactive dashboard for exploring Norwegian "
        "reservoir statistics, seasonal patterns, and "
        "meteorological data."
    )

    st.caption("IND320 · Data to Decision")

    st.divider()

    st.subheader("Welcome")

    st.write(
        "Explore Norwegian reservoir data through interactive "
        "tables, visualizations, and statistical analyses."
    )

    st.write(
        "Use the navigation menu to access reservoir statistics, "
        "seasonal analysis, and meteorological observations."
    )

    st.subheader("Explore the Dashboard")

    # Use Streamlit's responsive layout
    col1, col2 = st.columns(
        2,
        gap="medium",
        border=False
    )

    with col1:
        with st.container(border=True):

            st.markdown("#### Reservoir Data")

            st.write(
                "Explore reservoir statistics, compare areas, "
                "and visualize historical patterns."
            )

    with col2:
        with st.container(border=True):

            st.markdown("#### Advanced Analysis")

            st.write(
                "Investigate seasonal trends, precipitation "
                "outliers, and temperature anomalies."
            )


# ---------------------------------------------------------
# PAGE NAVIGATION
# ---------------------------------------------------------

# Pages are displayed in the order defined below.
# Existing Python files do not need to be renamed.

pages = {

    "Overview": [
        st.Page(
            show_home,
            title="Home",
            default=True
        )
    ],

    "Explore Data": [
        st.Page(
            "pages/2_Data_Table.py",
            title="Data Table"
        ),

        st.Page(
            "pages/3_Data_Plot.py",
            title="Data Plot"
        )
    ],

    "Reservoir Analysis": [
        st.Page(
            "pages/4_Project_2.py",
            title="Electricity Import and Export"
        ),

        st.Page(
            "pages/5_Seasonal_Analysis.py",
            title="Seasonal Analysis"
        )
    ],

    "Weather Analysis": [
        st.Page(
            "pages/6_Meterological_data.py",
            title="Meteorological Data"
        )
    ]
}


# ---------------------------------------------------------
# CREATE NAVIGATION
# ---------------------------------------------------------

# Streamlit handles sidebar layout and mobile responsiveness
navigation = st.navigation(
    pages,
    position="sidebar",
    expanded=True
)


# ---------------------------------------------------------
# SIDEBAR FOOTER
# ---------------------------------------------------------

with st.sidebar:

    st.divider()

    st.caption("IND320 · Data to Decision")


# ---------------------------------------------------------
# RUN SELECTED PAGE
# ---------------------------------------------------------

navigation.run()
