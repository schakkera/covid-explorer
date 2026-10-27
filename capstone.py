# -*- coding: utf-8 -*-
"""
Created on Mon Oct 26 15:06:48 2026

@author: shank
"""

"""
COVID-19 Country Explorer
Data: Johns Hopkins CSSE COVID-19 global time series
Run with:  streamlit run capstone.py
"""
import pandas as pd
import plotly.express as px
import streamlit as st

# ---------- Data sources ----------
BASE = "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/"
URL = BASE + "csse_covid_19_time_series/time_series_covid19_{}_global.csv"
POP_URL = BASE + "UID_ISO_FIPS_LookUp_Table.csv"
NOT_COUNTRIES = ["Diamond Princess", "MS Zaandam", "Summer Olympics 2020", "Winter Olympics 2022"]


# ---------- Load and clean ----------
@st.cache_data  # download once, not on every click
def load(kind):
    df = pd.read_csv(URL.format(kind))
    df = df[~df["Country/Region"].isin(NOT_COUNTRIES)]      # drop cruise ships / Olympics
    df = df.drop(columns=["Province/State", "Lat", "Long"])
    df = df.groupby("Country/Region").sum()                  # add provinces into one country
    df = df.T                                                # rows = dates, columns = countries
    df.index = pd.to_datetime(df.index, format="%m/%d/%y")
    df.index.name = "Date"
    return df


@st.cache_data
def load_population():
    pop = pd.read_csv(POP_URL)
    pop = pop[pop["Province_State"].isna()]                  # keep whole-country rows only
    return pop.set_index("Country_Region")["Population"]


# ---------- Page ----------
st.set_page_config(page_title="COVID-19 Country Explorer", layout="wide")
st.title("COVID-19 Country Explorer")
st.caption("Source: Johns Hopkins University CSSE (22 Jan 2020 – 9 Mar 2023, when collection ended)")

# ---------- Sidebar controls ----------
st.sidebar.header("Options")
kind = st.sidebar.radio("Measure", ["confirmed", "deaths"])
view = st.sidebar.radio("Count type", ["Daily", "Cumulative"])
smooth = st.sidebar.checkbox("7-day average (daily only)", value=True)
per_capita = st.sidebar.checkbox("Per 100,000 people")

data = load(kind)
countries = st.sidebar.multiselect("Countries (type to add)", list(data.columns),
                                   default=["US", "United Kingdom", "India"])

first, last = data.index.min().date(), data.index.max().date()
start, end = st.sidebar.slider("Date range", first, last, (first, last))

tab1, tab2 = st.tabs(["Chart", "How to use & data notes"])

# ---------- Chart tab ----------
with tab1:
    if not countries:
        st.info("Pick at least one country in the sidebar.")
        st.stop()

    sel = data[countries].astype(float)

    if view == "Daily":
        sel = sel.diff().clip(lower=0)          # cumulative -> daily; negative revisions set to 0
        if smooth:
            sel = sel.rolling(7, min_periods=1).mean()

    if per_capita:
        pop = load_population()
        sel = sel / pop[countries] * 100_000

    sel = sel.loc[str(start):str(end)]          # apply the date range

    label = f"{view} {kind}" + (" per 100k" if per_capita else "")
    fig = px.line(sel, labels={"value": label, "variable": "Country"}, title=label.capitalize())
    fig.update_layout(hovermode="x unified")
    st.plotly_chart(fig)

# ---------- Help tab ----------
with tab2:
    st.markdown("""
### How to use
1. **Add countries** in the sidebar box (type a name). Remove one with its **x**.
2. Choose **confirmed** cases or **deaths**.
3. Choose **Daily** (new each day) or **Cumulative** (running total).
4. Optional: **7-day average** smooths uneven reporting; **per 100,000** compares
   countries of different sizes.
5. Use the **date range** slider to zoom. Hover over the chart to compare countries.

### Data cleaning
- **Provinces combined:** countries reported by province (China, Canada, UK, France...) are summed.
- **Non-countries removed:** Diamond Princess, MS Zaandam, and the two Olympic Games.
- **Daily counts** = today's cumulative total minus yesterday's.
- **Negative daily values** (countries revising totals down) are set to 0.
- **7-day average** smooths weekend gaps and weekly reporting in 2022–23.
- **Population** for per-100k rates comes from the CSSE lookup table.
- **Limitation:** case counts depend on testing, which varied by country and over time.
""")