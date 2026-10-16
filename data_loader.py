
import pandas as pd
import streamlit as st
import requests

@st.cache_data(ttl=3600)
def load_data():
    # Retrieve reservoir statistics from the NVE API
    url = "https://biapi.nve.no/magasinstatistikk/api/Magasinstatistikk/HentOffentligData"
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    # Convert the API response into a DataFrame
    df = pd.DataFrame(response.json())

    return df
