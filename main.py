
import streamlit as st
import folium
import branca.colormap as cm

from datetime import date
from calendar import monthrange

from streamlit_folium import st_folium
from map_utils import load_geojson
from map_weather import get_weather_values


# Configure the Streamlit application
st.set_page_config(
    page_title="Reservoir Insights Norway",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="auto"
)


# Available geographical area groups
AREA_GROUPS = {
    "EL": ["EL1", "EL2", "EL3", "EL4", "EL5"],
    "VASS": ["VASS1", "VASS2", "VASS3"],
    "NO": ["NO0"]
}

MONTH_NAMES = [
    "January", "February", "March", "April",
    "May", "June", "July", "August",
    "September", "October", "November", "December"
]


def get_area_type(area):
    """Find the geographical group for a reservoir area."""
    for group, areas in AREA_GROUPS.items():
        if area in areas:
            return group

    return "EL"


@st.cache_data(show_spinner=False)
def load_map_weather(area_type, start_date, end_date, property_name):
    """Cache aggregated weather values for the selected period."""
    return get_weather_values(
        area_type,
        start_date,
        end_date,
        property_name
    )


def show_home():

    # --------------------------------------------------
    # WELCOME AND DASHBOARD INTRODUCTION
    # --------------------------------------------------

    st.title("💧 Reservoir Insights Norway")
    st.caption("IND320 · Data to Decision")

    st.subheader("Welcome!")

    st.write(
        "Welcome to Reservoir Insights Norway, an interactive dashboard "
        "for exploring Norwegian reservoir statistics, electricity patterns, "
        "meteorological conditions, and exchange rates."
    )

    st.write(
        "The dashboard brings together different data sources to help "
        "you explore historical trends, compare geographical areas, "
        "identify anomalies, and investigate relationships between "
        "energy and weather."
    )

    st.info(
        "Start by exploring the interactive map below, or use the "
        "navigation menu to access the different analyses."
    )

    st.divider()

    # --------------------------------------------------
    # SHARED AREA SELECTION
    # --------------------------------------------------

    # Initialize the shared area selection
    if "reservoir_area" not in st.session_state:
        st.session_state["reservoir_area"] = "EL3"

    saved_area = st.session_state["reservoir_area"]
    current_type = get_area_type(saved_area)

    # --------------------------------------------------
    # INTERACTIVE MAP
    # --------------------------------------------------

    st.subheader("Explore Norway")

    st.write(
        "Use the interactive map to explore geographical differences "
        "in temperature and precipitation. Select an area to apply "
        "your selection across the dashboard."
    )

    # Synchronize the map type with selections from other pages
    if (
        "home_area_type" not in st.session_state
        or st.session_state.get("home_last_area") != saved_area
    ):
        st.session_state["home_area_type"] = current_type

    # Select geographical area type
    map_area_type = st.radio(
        "Select area type",
        options=list(AREA_GROUPS.keys()),
        horizontal=True,
        key="home_area_type"
    )

    # Update shared selection when changing area type
    if saved_area not in AREA_GROUPS[map_area_type]:
        st.session_state["reservoir_area"] = (
            AREA_GROUPS[map_area_type][0]
        )

    # Select how the map should be coloured
    colour_by = st.selectbox(
        "Colour map by",
        options=[
            "Area",
            "Temperature",
            "Precipitation"
        ],
        key="map_colour_by"
    )

    weather_values = {}
    colour_scale = None
    unit = None
    selected_month = None

    # Weather colouring is available for EL and VASS
    if colour_by != "Area" and map_area_type == "NO":

        st.info(
            "Weather colouring is currently available for "
            "EL and VASS areas. Select one of these area types."
        )

    elif colour_by != "Area":

        # Select month from available weather data
        selected_month = st.selectbox(
            "Select month",
            options=list(range(1, 13)),
            format_func=lambda month: MONTH_NAMES[month - 1],
            key="map_weather_month"
        )

        selected_year = 2024

        # Determine the first and last day of the selected month
        start_date = date(
            selected_year,
            selected_month,
            1
        )

        last_day = monthrange(
            selected_year,
            selected_month
        )[1]

        end_date = date(
            selected_year,
            selected_month,
            last_day
        )

        # Calculate aggregated weather values
        try:
            with st.spinner("Calculating weather values..."):
                weather_values = load_map_weather(
                    map_area_type,
                    start_date.isoformat(),
                    end_date.isoformat(),
                    colour_by
                )

        except (FileNotFoundError, ValueError) as error:
            st.warning(str(error))

        valid_values = [
            value
            for value in weather_values.values()
            if value is not None
        ]

        # Create the appropriate colour scale
        if valid_values:

            minimum = min(valid_values)
            maximum = max(valid_values)

            if colour_by == "Temperature":

                # Blue below zero, white at zero, red above zero
                colours = [
                    "#003B5C",
                    "#83C5D5",
                    "#FFFFFF",
                    "#E3A58F",
                    "#B55239"
                ]

                # Keep zero at the centre of the scale
                scale_limit = max(
                    abs(minimum),
                    abs(maximum),
                    10
                )

                minimum = -scale_limit
                maximum = scale_limit
                unit = "°C"

            else:

                # Light blue for less precipitation,
                # dark blue for more precipitation
                colours = [
                    "#FFFFFF",
                    "#D6EAF0",
                    "#83C5D5",
                    "#007FA3",
                    "#003B5C"
                ]

                if minimum == maximum:
                    minimum = max(0, minimum - 0.5)
                    maximum += 0.5

                unit = "mm"

            colour_scale = cm.LinearColormap(
                colors=colours,
                vmin=minimum,
                vmax=maximum
            )

    # Create the interactive map
    norway_map = folium.Map(
        location=[64.5, 12.0],
        zoom_start=5,
        tiles="OpenStreetMap"
    )

    # Load geographical boundaries
    map_areas = load_geojson(map_area_type)

    selected_area = st.session_state["reservoir_area"]

    # Define the appearance of each geographical area
    def area_style(feature):

        area_id = feature["properties"]["area_id"]

        fill_colour = "#007FA3"

        # Colour areas according to weather values
        if colour_scale is not None:
            value = weather_values.get(area_id)

            if value is not None:
                fill_colour = colour_scale(value)
            else:
                fill_colour = "#E8E9E7"

        # Highlight the selected geographical area
        is_selected = area_id == selected_area

        return {
            "fillColor": fill_colour,
            "color": "#B55239" if is_selected else "#003B5C",
            "weight": 5 if is_selected else 2,
            "fillOpacity": 0.55 if colour_scale else 0.25
        }

    # Highlight areas when hovering over them
    def area_highlight(feature):
        return {
            "color": "#007FA3",
            "weight": 5,
            "fillOpacity": 0.7
        }

    # Add weather values to map tooltips
    if colour_scale is not None:

        for feature in map_areas["features"]:

            area_id = feature["properties"]["area_id"]
            value = weather_values.get(area_id)

            if value is not None:
                feature["properties"]["weather_value"] = (
                    f"{value:.2f} {unit}"
                )
            else:
                feature["properties"]["weather_value"] = "No data"

        tooltip = folium.GeoJsonTooltip(
            fields=["area_id", "weather_value"],
            aliases=["Area:", f"{colour_by}:"]
        )

    else:

        tooltip = folium.GeoJsonTooltip(
            fields=["area_id"],
            aliases=["Area:"]
        )

    # Add geographical areas to the map
    folium.GeoJson(
        map_areas,
        name=f"{map_area_type} areas",
        tooltip=tooltip,
        style_function=area_style,
        highlight_function=area_highlight
    ).add_to(norway_map)

    # Display the map and capture user interactions
    map_data = st_folium(
        norway_map,
        width="stretch",
        height=500,
        key=f"home_map_{map_area_type}",
        returned_objects=["last_active_drawing"]
    )

    # Save clicked area in the shared session state
    if map_data and map_data.get("last_active_drawing"):

        clicked_feature = map_data["last_active_drawing"]

        clicked_area = clicked_feature.get(
            "properties", {}
        ).get("area_id")

        if clicked_area in AREA_GROUPS[map_area_type]:

            if clicked_area != st.session_state["reservoir_area"]:
                st.session_state["reservoir_area"] = clicked_area
                st.rerun()

    # Remember current area for synchronization
    st.session_state["home_last_area"] = (
        st.session_state["reservoir_area"]
    )

    # Display the selected area
    st.write(
        "Selected area:",
        st.session_state["reservoir_area"]
    )

    # --------------------------------------------------
    # COLOUR LEGEND
    # --------------------------------------------------

    if colour_scale is not None:

        month_label = MONTH_NAMES[selected_month - 1]

        st.markdown(
            f"**{colour_by} ({unit}) – {month_label} 2024**"
        )

        # Create evenly spaced legend values
        legend_values = [
            minimum + (maximum - minimum) * i / 4
            for i in range(5)
        ]

        # Use the same colour scale as the map
        gradient_colours = [
            colour_scale(
                minimum + (maximum - minimum) * i / 100
            )
            for i in range(101)
        ]

        gradient_css = ", ".join(gradient_colours)

        # Display the horizontal colour gradient
        st.markdown(
            f"""
            <div style="
                height: 20px;
                border-radius: 5px;
                border: 1px solid #E8E9E7;
                background: linear-gradient(
                    to right,
                    {gradient_css}
                );
            "></div>
            """,
            unsafe_allow_html=True
        )

        # Display labels beneath the colour gradient
        legend_columns = st.columns(5)

        for index, value in enumerate(legend_values):

            if index == 0:
                alignment = "left"
            elif index == 4:
                alignment = "right"
            else:
                alignment = "center"

            with legend_columns[index]:
                st.markdown(
                    f"<div style='text-align:{alignment}'>"
                    f"{value:.1f} {unit}"
                    f"</div>",
                    unsafe_allow_html=True
                )

        # Explain the weather aggregation
        if colour_by == "Temperature":

            st.caption(
                "Temperature represents the average temperature "
                "across sampled locations and hourly observations "
                "during the selected month."
            )

        elif colour_by == "Precipitation":

            st.caption(
                "Precipitation represents accumulated precipitation "
                "during the selected month, averaged across "
                "sampled locations."
            )

    st.divider()

    # --------------------------------------------------
    # DASHBOARD OVERVIEW
    # --------------------------------------------------

    st.subheader("Explore the Dashboard")

    st.write(
        "Use the navigation menu to explore the different "
        "datasets and analytical tools available in this dashboard."
    )

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

        with st.container(border=True):
            st.markdown("#### Weather Analysis")
            st.write(
                "Investigate precipitation patterns, temperature "
                "variations, and unusual weather observations."
            )

    with col2:

        with st.container(border=True):
            st.markdown("#### Reservoir Analysis")
            st.write(
                "Investigate seasonal reservoir trends and "
                "relationships with electricity import and export."
            )

        with st.container(border=True):
            st.markdown("#### Currency Analysis")
            st.write(
                "Explore exchange rates and currency trends "
                "through interactive visualizations."
            )


# --------------------------------------------------
# DASHBOARD NAVIGATION
# --------------------------------------------------

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
        ),
        st.Page(
            "pages/8_Prediction_Fill_Level.py",
            title="Prediction of Reservoir Fill Level"
        )
    ],

    "Currency Analysis": [
        st.Page(
            "pages/7_Exchange_Rates.py",
            title="Exchange Rates"
        )
    ]
}

navigation = st.navigation(
    pages,
    position="sidebar",
    expanded=True
)

with st.sidebar:
    st.divider()
    st.caption("IND320 · Data to Decision")

navigation.run()
