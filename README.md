
# 💧 Reservoir Insights Norway

**IND320 – Data to Decision | Projects 1–3**  
**Simone Viktoria Eide**

[Explore the Streamlit Dashboard](https://reservoir-insights-norway-simoneeide.streamlit.app/) | [GitHub Repository](https://github.com/simoneviktoriaeide/IND320_Simone_Eide)

## About the Project

This repository contains my work in **IND320 – Data to Decision**.

Throughout the three projects, I have worked with Norwegian reservoir statistics, electricity import and export, and historical weather data. The projects cover everything from basic data exploration and visualisation to working with APIs, databases, geographical data and time-series analysis.

I have also developed **Reservoir Insights Norway**, an interactive Streamlit dashboard where users can explore the data and try different analyses.

## Project Overview

### Project 1 – Exploring Norwegian Reservoir Data

In Project 1, I focused on understanding, preparing and visualising historical reservoir data using Python.

This included:

- Exploring the dataset and checking for missing values and duplicates.
- Cleaning the data and converting dates.
- Working with the different area types: EL, NO and VASS.
- Visualising reservoir fill levels, capacity and stored energy.
- Comparing reservoir statistics between different areas.
- Exploring how reservoir levels change over time.

**Notebook:** [Project 1](notebooks/Project_1.ipynb)

### Project 2 – APIs, Databases and Electricity Flows

In Project 2, I continued working with reservoir statistics, but started retrieving the data directly from the NVE API.

I also explored different database technologies and electricity import and export data.

This included:

- Downloading reservoir data from the NVE API.
- Preparing and visualising the downloaded data.
- Working with Apache Spark and Cassandra.
- Exploring MongoDB Atlas.
- Using ENTSO-E data to investigate electricity import and export.
- Creating plots showing electricity flows over time.

**Notebook:** [Project 2](notebooks/Project_2.ipynb)

### Project 3 – Weather Data and Time-Series Analysis

In Project 3, I worked with geographical data, historical weather observations and different methods for analysing time series.

This included:

- Working with geographical boundaries for Norwegian electricity and precipitation regions.
- Generating 1,000 random locations per region.
- Visualising the sampled locations on maps.
- Downloading historical ERA5 weather data from Open-Meteo.
- Analysing temperature and precipitation data for NO3 in 2024.
- Using Discrete Cosine Transform (DCT) and Statistical Process Control (SPC) to identify unusual precipitation values.
- Comparing different DCT cutoff values.
- Using Local Outlier Factor (LOF) to detect temperature anomalies.
- Using STL decomposition to investigate seasonal patterns in reservoir levels.
- Creating spectrograms to explore how repeating patterns change over time.

**Notebook:** [Project 3](notebooks/Project_3.ipynb)

## Streamlit Dashboard

As part of the projects, I developed an interactive dashboard called **Reservoir Insights Norway**.

The dashboard brings together reservoir statistics, electricity data and weather analysis in one application.

### Dashboard Pages

| Page | Description |
|---|---|
| Home | Introduction to the dashboard |
| Data Table | Explore reservoir statistics in table form |
| Data Plot | Visualise and compare reservoir data |
| Electricity Import and Export | Explore Norwegian electricity flows |
| Seasonal Analysis | Analyse reservoir data using STL decomposition and spectrograms |
| Meteorological Data | Explore weather data and related analyses |

The dashboard includes a sidebar menu for navigating between pages, area selectors and interactive settings for different analyses.

For example, the Seasonal Analysis page allows users to adjust STL parameters and spectrogram settings to see how the results change.

**Live dashboard:** [Reservoir Insights Norway](https://reservoir-insights-norway-simoneeide.streamlit.app/)

## Repository Structure

```text
IND320_Simone_Eide/
│
├── notebooks/
│   ├── Project_1.ipynb
│   ├── Project_2.ipynb
│   ├── Project_3.ipynb
│   └── Project_4.ipynb
│
├── pages/
│   ├── 2_Data_Table.py
│   ├── 3_Data_Plot.py
│   ├── 4_Project_2.py
│   ├── 5_Seasonal_Analysis.py
│   └── 6_Meterological_data.py
│
├── data/
├── streamlit/
├── Screencasts/
│
├── main.py
├── area_selector.py
├── data_loader.py
├── weather_utils.py
├── requirements.txt
└── README.md
```

The `notebooks` folder contains the Jupyter Notebooks for each project.

The `pages` folder contains the different Streamlit pages.

The `main.py` file defines the dashboard's home page and navigation, while the other Python files contain shared functions for loading data, selecting areas and working with weather data.

## How to Run the Dashboard

### 1. Clone the Repository

```bash
git clone https://github.com/simoneviktoriaeide/IND320_Simone_Eide.git
cd IND320_Simone_Eide
```

### 2. Install the Required Libraries

Make sure Python is installed, then run:

```bash
pip install -r requirements.txt
```

### 3. Start Streamlit

```bash
streamlit run main.py
```

The dashboard will open in your browser.

An internet connection is needed for features that retrieve data from external APIs.

## Data Sources

The projects use data from the following sources:

- **NVE (Norwegian Water Resources and Energy Directorate):** Norwegian reservoir statistics and geographical region data.
- **ENTSO-E:** Electricity import and export data.
- **Open-Meteo / ERA5:** Historical temperature and precipitation data.

## Tools and Libraries

The main tools and libraries used throughout the projects include:

- Python
- Jupyter Notebook
- pandas and NumPy
- Matplotlib and Plotly
- Streamlit
- GeoPandas
- SciPy
- scikit-learn
- statsmodels
- Apache Spark
- Cassandra
- MongoDB

## Documentation

Each Jupyter Notebook contains the code, visualisations and explanations for its project.

The notebooks also include work logs and information about how AI tools were used during the projects.

---

*Created as part of IND320 – Data to Decision.*
