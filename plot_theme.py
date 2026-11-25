import plotly.graph_objects as go
import plotly.io as pio

# Hydro-inspired colour palette
DARK_BLUE = "#003B5C"
WATER_BLUE = "#007FA3"
LIGHT_BLUE = "#83C5D5"
BAUXITE_RED = "#B55239"
GREY = "#E8E9E7"
WHITE = "#FFFFFF"
TEXT_COLOR = "#252C30"

# Shared Plotly template
pio.templates["hydro"] = go.layout.Template(
    layout=go.Layout(
        colorway=[
            DARK_BLUE,
            WATER_BLUE,
            BAUXITE_RED,
            LIGHT_BLUE,
            "#607D75"
        ],
        paper_bgcolor=WHITE,
        plot_bgcolor=WHITE,
        font=dict(
            family="Arial",
            size=14,
            color=TEXT_COLOR
        ),
        title=dict(
            font=dict(
                size=22,
                color=DARK_BLUE
            )
        ),
        xaxis=dict(
            gridcolor=GREY,
            zerolinecolor=GREY
        ),
        yaxis=dict(
            gridcolor=GREY,
            zerolinecolor=GREY
        ),
        hovermode="closest"
    )
)

# Set the default Plotly template
pio.templates.default = "hydro"