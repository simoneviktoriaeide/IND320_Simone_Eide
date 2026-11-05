import streamlit as st


def select_area():
    """Display a shared reservoir area selector across Streamlit pages."""

    # Define the available reservoir areas
    area_groups = {
        "EL": ["EL1", "EL2", "EL3", "EL4", "EL5"],
        "NO": ["NO0"],
        "VASS": ["VASS1", "VASS2", "VASS3"]
    }

    # Initialize the persistent area selection
    if "reservoir_area" not in st.session_state:
        st.session_state["reservoir_area"] = "EL3"

    # Read the saved area
    saved_area = st.session_state["reservoir_area"]

    # Find the corresponding area type
    saved_type = next(
        group for group, areas in area_groups.items()
        if saved_area in areas
    )

    # Display the area type selector
    selected_type = st.radio(
        "Select area type",
        options=list(area_groups.keys()),
        index=list(area_groups.keys()).index(saved_type),
        horizontal=True,
        key="area_type_selector"
    )

    # Update the saved area when changing area type
    if saved_area not in area_groups[selected_type]:
        st.session_state["reservoir_area"] = area_groups[selected_type][0]

    # Display the specific area selector
    selected_area = st.selectbox(
        "Select area",
        options=area_groups[selected_type],
        index=area_groups[selected_type].index(
            st.session_state["reservoir_area"]
        ),
        key="area_selector"
    )

    # Save the selected area
    st.session_state["reservoir_area"] = selected_area


    return selected_area