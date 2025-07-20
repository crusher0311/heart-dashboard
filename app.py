import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import base64

st.set_page_config(page_title="HEART Metric Dashboard", layout="wide")

# Embed the HEART logo
def add_logo():
    logo_path = "heart_logo.png"
    with open(logo_path, "rb") as image_file:
        encoded = base64.b64encode(image_file.read()).decode()
    st.markdown(
        f"""
        <div style="display: flex; align-items: center;">
            <img src="data:image/png;base64,{encoded}" width="150" style="margin-right: 10px;">
            <h1 style="display: inline;">HEART Metric Dashboard</h1>
        </div>
        """,
        unsafe_allow_html=True,
    )

@st.cache_data
def load_data():
    df_raw = pd.read_excel("Heart Metric Dashboard (3).xlsx", sheet_name="Data", header=1)
    df = pd.melt(df_raw, id_vars=["Week", "Metric"], var_name="Advisor", value_name="Value")
    df["Week"] = df["Week"].astype(str).str.extract(r"(\d+)").astype(int)

    # Assign location based on advisor name
    location_map = {
        "Armando": "Northbrook", "Jaime": "Northbrook", "Craig": "Northbrook",
        "Frank": "Wilmette", "Dimitri": "Wilmette", "Ben": "Wilmette",
        "Ernie": "Evanston", "Sam": "Evanston", "Jaysun": "Evanston"
    }
    df["Location"] = df["Advisor"].map(location_map)

    # Rename metrics for display
    display_map = {
        "CC": "Car Count"
    }
    df["DisplayMetric"] = df["Metric"].replace(display_map)

    return df

def z_score_outliers(group):
    mean = group["Value"].mean()
    std = group["Value"].std()
    group["Z-Score"] = (group["Value"] - mean) / std
    group["Outlier"] = group["Z-Score"].abs() > 2
    group["Smoothed"] = group["Value"].rolling(window=2, min_periods=1).mean()
    return group

add_logo()
df = load_data()

# Sidebar filters with session state
advisors = df["Advisor"].unique().tolist()
metrics = df["DisplayMetric"].unique().tolist()
locations = df["Location"].dropna().unique().tolist()
weeks = sorted(df["Week"].unique())

default_locations = ["Evanston"]
default_advisors = ["Ernie", "Sam", "Jaysun"]
default_metrics = ["GP$/HR", "Hrs Sold/RO", "Car Count"]

if "selected_locations" not in st.session_state:
    st.session_state.selected_locations = default_locations
if "selected_advisors" not in st.session_state:
    st.session_state.selected_advisors = default_advisors
if "selected_metrics" not in st.session_state:
    st.session_state.selected_metrics = default_metrics
if "week_range" not in st.session_state:
    st.session_state.week_range = (min(weeks), max(weeks))
if "show_outliers" not in st.session_state:
    st.session_state.show_outliers = False
if "show_rolling_avg" not in st.session_state:
    st.session_state.show_rolling_avg = False
if "show_trendline" not in st.session_state:
    st.session_state.show_trendline = False

selected_locations = st.sidebar.multiselect(
    "Select Location(s)", locations, default=st.session_state.selected_locations, key="selected_locations"
)
selected_advisors = st.sidebar.multiselect(
    "Select Advisor(s)", advisors, default=st.session_state.selected_advisors, key="selected_advisors"
)
selected_metrics = st.sidebar.multiselect(
    "Select Metric(s)", metrics, default=st.session_state.selected_metrics, key="selected_metrics"
)
week_range = st.sidebar.slider(
    "Select Week Range", min_value=min(weeks), max_value=max(weeks),
    value=st.session_state.week_range, key="week_range"
)
show_outliers = st.sidebar.checkbox("Show Outliers", value=st.session_state.show_outliers, key="show_outliers")
show_rolling_avg = st.sidebar.checkbox("Show Rolling Average", value=st.session_state.show_rolling_avg, key="show_rolling_avg")
show_trendline = st.sidebar.checkbox("Show Trendline", value=st.session_state.show_trendline, key="show_trendline")

df_filtered = df[
    (df["Location"].isin(selected_locations)) &
    (df["Advisor"].isin(selected_advisors)) &
    (df["DisplayMetric"].isin(selected_metrics)) &
    (df["Week"].between(week_range[0], week_range[1]))
]

df_processed = df_filtered.groupby(["DisplayMetric", "Advisor"], group_keys=False).apply(z_score_outliers)

for metric in selected_metrics:
    st.subheader(f"{metric}")
    metric_df = df_processed[df_processed["DisplayMetric"] == metric]

    fig = px.line(
        metric_df,
        x="Week",
        y="Value",
        color="Advisor",
        markers=True,
        line_dash="Outlier" if show_outliers else None,
        symbol="Outlier" if show_outliers else None
    )

    if show_rolling_avg:
        for advisor in metric_df["Advisor"].unique():
            advisor_df = metric_df[metric_df["Advisor"] == advisor]
            fig.add_scatter(x=advisor_df["Week"], y=advisor_df["Smoothed"],
                            mode="lines", name=f"{advisor} (Smoothed)")

    if show_trendline:
        for advisor in metric_df["Advisor"].unique():
            advisor_df = metric_df[metric_df["Advisor"] == advisor]
            if len(advisor_df) > 1:
                trend = px.scatter(advisor_df, x="Week", y="Smoothed", trendline="ols")
                for trace in trend.data:
                    if trace.mode == "lines":
                        trace.name = f"{advisor} (Trend)"
                        fig.add_trace(trace)

    st.plotly_chart(fig, use_container_width=True)
