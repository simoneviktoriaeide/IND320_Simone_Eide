import geopandas as gpd
from pathlib import Path


# Folder containing the GeoJSON files
GEOJSON_FOLDER = Path(__file__).resolve().parent / "data" / "Shapefile"


def load_geojson(area_type):
    """
    Load geographical boundaries for NO, EL or VASS areas.
    """

    if area_type == "EL":

        # Load electricity bidding areas
        areas = gpd.read_file(
            GEOJSON_FOLDER / "price_areas.geojson"
        )

        # Match area names with reservoir statistics
        areas["area_id"] = areas["budomr"].str.replace(
            "NO ", "EL", regex=False
        )

    elif area_type == "VASS":

        # Load NVE regions
        areas = gpd.read_file(
            GEOJSON_FOLDER / "nve_regions.geojson"
        )

        # Use the same regional grouping as Project 3
        region_mapping = {
            "RV": "VASS2",
            "RS": "VASS1",
            "RØ": "VASS1",
            "RM": "VASS3",
            "RN": "VASS3"
        }

        # Assign and merge regions
        areas["area_id"] = areas["REGION"].map(region_mapping)

        areas = areas.dissolve(
            by="area_id",
            as_index=False
        )

    elif area_type == "NO":

        # Combine all electricity areas into Norway
        areas = gpd.read_file(
            GEOJSON_FOLDER / "price_areas.geojson"
        )

        areas["area_id"] = "NO0"

        areas = areas.dissolve(
            by="area_id",
            as_index=False
        )

    else:
        raise ValueError(f"Unknown area type: {area_type}")

    # Ensure coordinates are suitable for web maps
    areas = areas.to_crs(epsg=4326)

    return areas.__geo_interface__