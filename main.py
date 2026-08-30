"""
Streamlit dashboard for airplane data visualization with gold aggregations and rolling windows.
Features: Global view mode selector (Summary/Rolling Windows), Window size and country filters
Shows counts as text with up/down indicators comparing to previous periods.
"""

import streamlit as st
import polars as pl
import pandas as pd
from pathlib import Path
from config import GOLD_DATA_DIR
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

# ============================================================================
# PAGE CONFIG
# ============================================================================

st.set_page_config(
    page_title="Airplane Data Dashboard",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
    <style>
    .main-header {
        text-align: center;
        color: #1f77b4;
        margin-bottom: 30px;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='main-header'>✈️ Airplane Data Dashboard</h1>", unsafe_allow_html=True)

# ============================================================================
# DATA LOADING
# ============================================================================

@st.cache_data
def load_master_data():
    """Load the master dataset containing all gold and rolling data."""
    try:
        # Look for master files recursively (handles both root and master/ subdirectory)
        master_files = list(GOLD_DATA_DIR.rglob("gold_master_all_*.parquet"))
        
        if not master_files:
            st.error("No master data file found. Please run: python 3_gold_and_rolling_aggregations.py")
            return None
        
        # Use the most recent master file (sort by modification time, descending)
        master_path = max(master_files, key=lambda p: p.stat().st_mtime)
        st.info(f"📂 Loading: {master_path.name}")
        return pl.read_parquet(master_path)
    except Exception as e:
        st.error(f"Error loading master data: {e}")
        return None

# Load master data
master_df = load_master_data()

if master_df is None:
    st.error("Failed to load data. Please run the aggregation script first.")
    st.stop()

# Extract data by report type and subtype
@st.cache_data
def get_gold_data(master_df):
    """Extract gold aggregations from master dataset."""
    gold_df = master_df.filter(pl.col("report_type") == "all")
    
    data = {}
    
    # Get each gold type
    if "gold_type" in gold_df.columns:
        for gold_type in ["gold_by_country", "gold_by_aircraft", "gold_by_airline", "gold_by_country_airline", "gold_by_snapshot", "gold_summary"]:
            filtered = gold_df.filter(pl.col("gold_type") == gold_type)
            if len(filtered) > 0:
                key = gold_type.replace("gold_", "")
                data[key] = filtered.drop(["report_type", "gold_type", "report_period", "report_period_start", "report_period_end"])
    
    return data

@st.cache_data
def get_rolling_data(master_df):
    """Extract rolling window data from master dataset."""
    rolling_df = master_df.filter(pl.col("report_type") == "rolling")
    
    rolling_data = {}
    
    if "rolling_type" in rolling_df.columns:
        for rolling_type in ["r12_1day", "r12_3day", "r12_7day", "r12_14day", "r12_30day"]:
            filtered = rolling_df.filter(pl.col("rolling_type") == rolling_type)
            if len(filtered) > 0:
                # Separate global, by-country, and by-airline
                global_only = filtered.filter((pl.col("country").is_null()) & (pl.col("airline_name").is_null()))
                by_country = filtered.filter((pl.col("country").is_not_null()) & (pl.col("airline_name").is_null()))
                by_airline = filtered.filter(pl.col("airline_name").is_not_null())
                
                if len(global_only) > 0:
                    rolling_data[f"rolling_global_{rolling_type.split('_')[1]}"] = global_only.drop(
                        ["report_type", "rolling_type", "report_period"]
                    )
                
                if len(by_country) > 0:
                    rolling_data[f"rolling_country_{rolling_type.split('_')[1]}"] = by_country.drop(
                        ["report_type", "rolling_type", "report_period"]
                    )
                
                if len(by_airline) > 0:
                    rolling_data[f"rolling_airline_{rolling_type.split('_')[1]}"] = by_airline.drop(
                        ["report_type", "rolling_type", "report_period"]
                    )
    
    return rolling_data

try:
    data = get_gold_data(master_df)
    rolling_data = get_rolling_data(master_df)
except Exception as e:
    st.error(f"Error processing data: {e}")
    st.stop()

# ============================================================================
# SIDEBAR CONTROLS
# ============================================================================

st.sidebar.markdown("### 📊 Dashboard Controls")

view_mode = st.sidebar.radio(
    "Select View Mode",
    options=["📊 Summary View", "🔄 Rolling Windows"],
    help="Choose between summary aggregations or rolling window analysis"
)

# ============================================================================
# SUMMARY VIEW
# ============================================================================

if view_mode == "📊 Summary View":
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📈 Summary", "✈️ Aircraft", "🌍 Origin Country", "✈️ Airlines", "🌍 Country-Airline", "📸 Snapshots"])
    
    with tab1:
        st.subheader("Dashboard Overview")
        if "summary" in data and len(data["summary"]) > 0:
            summary_df = data["summary"].to_pandas()
            
            # Convert metric-value pairs to a dictionary
            metrics_dict = dict(zip(summary_df["metric"], summary_df["value"]))
            
            # Display date range at top
            min_date = metrics_dict.get("min_date", "N/A")
            max_date = metrics_dict.get("max_date", "N/A")
            st.markdown(f"**📅 Data Range: {min_date} to {max_date}**")
            st.divider()
            
            # Display key metrics in columns
            col1, col2, col3, col4 = st.columns(4)
            
            metric_labels = [
                ("unique_aircraft", "Avg Aircraft"),
                ("avg_altitude", "Avg Altitude (ft)"),
                ("unique_countries", "Avg Countries"),
                ("total_records", "Total Records")
            ]
            
            cols = [col1, col2, col3, col4]
            for idx, (metric_key, label) in enumerate(metric_labels):
                with cols[idx]:
                    value = metrics_dict.get(metric_key, "N/A")
                    try:
                        val_float = float(value)
                        st.metric(label=label, value=f"{val_float:,.0f}")
                    except:
                        st.metric(label=label, value=value)
            
            # Display geographic metrics in separate row
            st.markdown("#### 🌍 Geographic Metrics")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                # Extract from summary data table if available
                loc_value = metrics_dict.get("unique_locations", "N/A")
                try:
                    loc_int = int(float(loc_value)) if loc_value != "N/A" else "N/A"
                    st.metric(label="Unique Locations", value=f"{loc_int:,.0f}" if isinstance(loc_int, int) else loc_int)
                except:
                    st.metric(label="Unique Locations", value=loc_value)
            with col2:
                reg_value = metrics_dict.get("unique_regions", "N/A")
                try:
                    reg_int = int(float(reg_value)) if reg_value != "N/A" else "N/A"
                    st.metric(label="Unique Regions", value=f"{reg_int:,.0f}" if isinstance(reg_int, int) else reg_int)
                except:
                    st.metric(label="Unique Regions", value=reg_value)
            with col3:
                cc_value = metrics_dict.get("unique_country_codes", "N/A")
                try:
                    cc_int = int(float(cc_value)) if cc_value != "N/A" else "N/A"
                    st.metric(label="Country Codes", value=f"{cc_int:,.0f}" if isinstance(cc_int, int) else cc_int)
                except:
                    st.metric(label="Country Codes", value=cc_value)
            with col4:
                on_air = metrics_dict.get("in_air_count", "0")
                try:
                    on_air_int = int(float(on_air))
                    st.metric(label="In-Air Records", value=f"{on_air_int:,.0f}")
                except:
                    st.metric(label="In-Air Records", value=on_air)
            
            # Display airport metrics
            st.markdown("#### ✈️ Airport Metrics")
            col1, col2, col3 = st.columns(3)
            with col1:
                airport_value = metrics_dict.get("unique_airports", "N/A")
                try:
                    airport_int = int(float(airport_value)) if airport_value != "N/A" else "N/A"
                    st.metric(label="Unique Airports", value=f"{airport_int:,.0f}" if isinstance(airport_int, int) else airport_int)
                except:
                    st.metric(label="Unique Airports", value=airport_value)
            with col2:
                ground_value = metrics_dict.get("aircraft_on_ground", "0")
                try:
                    ground_int = int(float(ground_value))
                    st.metric(label="Aircraft on Ground", value=f"{ground_int:,.0f}")
                except:
                    st.metric(label="Aircraft on Ground", value=ground_value)
            with col3:
                st.metric(label="Airport Coverage", value="Ground aircraft only")
            
            # Country-level KPIs
            st.markdown("#### 🌍 Country-Level Insights")
            if "by_country" in data and len(data["by_country"]) > 0:
                country_df = data["by_country"].to_pandas()
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Countries", len(country_df))
                with col2:
                    total_country_records = country_df["total_records"].sum() if "total_records" in country_df.columns else "N/A"
                    st.metric("Country Records", f"{total_country_records:,.0f}" if isinstance(total_country_records, (int, float)) else total_country_records)
                with col3:
                    unique_aircraft_countries = country_df["unique_aircraft"].sum() if "unique_aircraft" in country_df.columns else "N/A"
                    st.metric("Aircraft Across Countries", f"{unique_aircraft_countries:,.0f}" if isinstance(unique_aircraft_countries, (int, float)) else unique_aircraft_countries)
                
                # Geographic diversity KPIs
                if "unique_locations" in country_df.columns and "unique_regions" in country_df.columns:
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        avg_locs = country_df["unique_locations"].mean()
                        st.metric("Avg Locations per Country", f"{avg_locs:.1f}")
                    with col2:
                        avg_regs = country_df["unique_regions"].mean()
                        st.metric("Avg Regions per Country", f"{avg_regs:.1f}")
                    with col3:
                        max_locs = country_df["unique_locations"].max()
                        st.metric("Max Locations (Single Country)", f"{int(max_locs)}")
            
            # Aircraft-level KPIs
            st.markdown("#### ✈️ Aircraft-Level Insights")
            if "by_aircraft" in data and len(data["by_aircraft"]) > 0:
                aircraft_df = data["by_aircraft"].to_pandas()
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Aircraft", len(aircraft_df))
                with col2:
                    total_aircraft_records = aircraft_df["record_count"].sum() if "record_count" in aircraft_df.columns else "N/A"
                    st.metric("Total Records (Aircraft)", f"{total_aircraft_records:,.0f}" if isinstance(total_aircraft_records, (int, float)) else total_aircraft_records)
                with col3:
                    avg_records_per_aircraft = aircraft_df["record_count"].mean() if "record_count" in aircraft_df.columns else "N/A"
                    st.metric("Avg Records/Aircraft", f"{avg_records_per_aircraft:,.0f}" if isinstance(avg_records_per_aircraft, (int, float)) else avg_records_per_aircraft)
                
                if "num_locations_visited" in aircraft_df.columns and "num_regions_visited" in aircraft_df.columns:
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        avg_locs = aircraft_df["num_locations_visited"].mean()
                        st.metric("Avg Locations per Aircraft", f"{avg_locs:.1f}")
                    with col2:
                        avg_regs = aircraft_df["num_regions_visited"].mean()
                        st.metric("Avg Regions per Aircraft", f"{avg_regs:.1f}")
                    with col3:
                        max_locs = aircraft_df["num_locations_visited"].max()
                        st.metric("Max Locations (Single Aircraft)", f"{int(max_locs)}")
            
            # Snapshot-level KPIs
            st.markdown("#### 📸 Snapshot-Level Insights")
            if "by_snapshot" in data and len(data["by_snapshot"]) > 0:
                snapshot_df = data["by_snapshot"].to_pandas()
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Snapshots", len(snapshot_df))
                with col2:
                    total_snapshot_records = snapshot_df["total_records"].sum() if "total_records" in snapshot_df.columns else "N/A"
                    st.metric("Total Records (Snapshots)", f"{total_snapshot_records:,.0f}" if isinstance(total_snapshot_records, (int, float)) else total_snapshot_records)
                with col3:
                    avg_aircraft_per_snapshot = snapshot_df["unique_aircraft"].mean() if "unique_aircraft" in snapshot_df.columns else "N/A"
                    st.metric("Avg Aircraft per Snapshot", f"{avg_aircraft_per_snapshot:,.0f}" if isinstance(avg_aircraft_per_snapshot, (int, float)) else avg_aircraft_per_snapshot)
                
                if "unique_locations" in snapshot_df.columns:
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        avg_locs = snapshot_df["unique_locations"].mean()
                        st.metric("Avg Unique Locations", f"{avg_locs:.0f}")
                    with col2:
                        avg_regs = snapshot_df["unique_regions"].mean() if "unique_regions" in snapshot_df.columns else "N/A"
                        st.metric("Avg Unique Regions", f"{avg_regs:.0f}" if avg_regs != "N/A" else "N/A")
                    with col3:
                        avg_countries = snapshot_df["unique_countries"].mean() if "unique_countries" in snapshot_df.columns else "N/A"
                        st.metric("Avg Unique Countries", f"{avg_countries:.0f}" if avg_countries != "N/A" else "N/A")
            
            st.markdown("#### Full Summary Data")
            # Display as a clean key-value table
            display_df = pd.DataFrame({
                "Metric": [k.replace("_", " ").title() for k in metrics_dict.keys()],
                "Value": [v for v in metrics_dict.values()]
            })
            st.dataframe(display_df, use_container_width=True)
        else:
            st.info("No summary data available")
    
    with tab2:
        st.subheader("Aircraft Analysis - Visualizations")
        if "by_aircraft" in data and len(data["by_aircraft"]) > 0:
            aircraft_df = data["by_aircraft"].to_pandas()
            
            st.markdown("#### Top 15 Aircraft by Records")
            if "record_count" in aircraft_df.columns and "icao24" in aircraft_df.columns:
                top_aircraft = aircraft_df.nlargest(15, "record_count").sort_values("record_count")
                
                fig = px.bar(
                    top_aircraft,
                    x="record_count",
                    y="icao24",
                    orientation="h",
                    color="record_count",
                    color_continuous_scale="Blues",
                    title="Top 15 Aircraft by Record Count",
                    labels={"icao24": "Aircraft (ICAO24)", "record_count": "Records"},
                    height=400
                )
                fig.update_layout(
                    coloraxis_colorbar=dict(
                        thickness=20,
                        len=0.7,
                        tickformat=".0f"
                    )
                )
                st.plotly_chart(fig, use_container_width=True)
            
            # Top aircraft by geographic diversity
            st.markdown("#### Most Widely-Traveled Aircraft")
            if "num_locations_visited" in aircraft_df.columns:
                cols_to_show = ["icao24", "callsign", "num_locations_visited", "num_regions_visited", "primary_location", "primary_region"]
                if "airline_name" in aircraft_df.columns:
                    cols_to_show.insert(2, "airline_name")
                top_diverse = aircraft_df.nlargest(10, "num_locations_visited")[cols_to_show].sort_values("num_locations_visited", ascending=False)
                st.dataframe(top_diverse, use_container_width=True)
            
            # Aircraft with most airport visits
            st.markdown("#### Most Frequent Airport Visitors")
            if "num_airports_visited" in aircraft_df.columns:
                cols_to_show = ["icao24", "callsign", "num_airports_visited", "primary_airport", "airport_country", "airport_region"]
                if "airline_name" in aircraft_df.columns:
                    cols_to_show.insert(2, "airline_name")
                airport_visitors = aircraft_df[aircraft_df["num_airports_visited"] > 0].nlargest(10, "num_airports_visited")[cols_to_show].sort_values("num_airports_visited", ascending=False)
                if len(airport_visitors) > 0:
                    st.dataframe(airport_visitors, use_container_width=True)
                else:
                    st.info("No airport data available for aircraft")
            
            st.markdown("#### Aircraft Data Table")
            st.dataframe(aircraft_df, use_container_width=True)
        else:
            st.info("No aircraft data available")
    
    with tab3:
        st.subheader("Origin Country Analysis - Geographic Visualizations")
        if "by_country" in data and len(data["by_country"]) > 0:
            country_df = data["by_country"].to_pandas()
            
            # Force cache clear - v2
            st.cache_data.clear()
            
            # Map country names to ISO-3 country codes for choropleth
            country_iso_map = {
                "United States": "USA",
                "United Kingdom": "GBR",
                "Canada": "CAN",
                "Germany": "DEU",
                "Ireland": "IRL",
                "France": "FRA",
                "Netherlands": "NLD",
                "Spain": "ESP",
                "Italy": "ITA",
                "Switzerland": "CHE",
                "Sweden": "SWE",
                "Norway": "NOR",
                "Denmark": "DNK",
                "Belgium": "BEL",
                "Austria": "AUT",
                "Poland": "POL",
                "Portugal": "PRT",
                "Greece": "GRC",
                "Japan": "JPN",
                "China": "CHN",
                "India": "IND",
                "Australia": "AUS",
                "Brazil": "BRA",
                "Mexico": "MEX",
                "South Korea": "KOR",
                "Singapore": "SGP",
                "Hong Kong": "HKG",
                "UAE": "ARE",
                "Saudi Arabia": "SAU",
                "New Zealand": "NZL",
                "Thailand": "THA",
                "Malaysia": "MYS",
                "Philippines": "PHL",
                "Indonesia": "IDN",
                "Vietnam": "VNM",
                "Taiwan": "TWN",
                "Czechia": "CZE",
                "Czech Republic": "CZE",
                "Russia": "RUS",
                "Turkey": "TUR",
                "Israel": "ISR",
                "Pakistan": "PAK",
                "Bangladesh": "BGD",
                "Nigeria": "NGA",
                "South Africa": "ZAF",
            }
            
            # Add ISO codes to dataframe
            country_df["iso_alpha"] = country_df["origin_country"].map(country_iso_map)
            country_df_with_codes = country_df[country_df["iso_alpha"].notna()]
            
            # Create choropleth map with 10 quantile-based bins showing values
            if "unique_aircraft" in country_df_with_codes.columns and len(country_df_with_codes) > 0:
                st.markdown("#### Global Distribution - Choropleth Map")
                
                # Create 10 quantile-based bins with value ranges as labels
                country_df_with_codes["aircraft_bin"] = pd.qcut(
                    country_df_with_codes["unique_aircraft"],
                    q=10,
                    duplicates='drop'
                )
                
                # Convert intervals to readable string labels, then drop the Interval column
                country_df_with_codes["bin_label"] = country_df_with_codes["aircraft_bin"].astype(str)
                country_df_with_codes = country_df_with_codes.drop("aircraft_bin", axis=1)
                
                fig = px.choropleth(
                    country_df_with_codes,
                    locations="iso_alpha",
                    color="bin_label",
                    hover_name="origin_country",
                    hover_data={
                        "total_records": ":,.0f", 
                        "unique_aircraft": ":,.0f", 
                        "iso_alpha": False, 
                        "bin_label": True
                    },
                    color_discrete_sequence=px.colors.diverging.PRGn,
                    title="Unique Aircraft by Country (10 Categories)",
                    height=500
                )
                fig.update_layout(
                    geo=dict(
                        projection_type="natural earth",
                        showland=True,
                        landcolor="rgb(243, 243, 243)",
                        coastlinecolor="rgb(204, 204, 204)",
                    )
                )
                st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("#### Top 15 Countries by Aircraft Count")
            if "unique_aircraft" in country_df.columns and "origin_country" in country_df.columns:
                top_countries = country_df.nlargest(15, "unique_aircraft").sort_values("unique_aircraft")
                
                # Create bar chart with single-color gradient
                fig = px.bar(
                    top_countries,
                    x="unique_aircraft",
                    y="origin_country",
                    orientation="h",
                    title="Top 15 Countries by Unique Aircraft",
                    labels={"origin_country": "Origin Country", "unique_aircraft": "Aircraft"},
                    height=400
                )
                # Use continuous color mapping
                fig.update_layout(
                    coloraxis=dict(
                        showscale=True,
                        colorbar=dict(
                            thickness=20,
                            len=0.8,
                            tickmode="auto"
                        )
                    )
                )
                st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("#### All Countries Data Table")
            st.dataframe(country_df.drop("iso_alpha", axis=1, errors="ignore"), use_container_width=True)
        else:
            st.info("No origin country data available")
    
    with tab4:
        st.subheader("Airline Analysis - Visualizations")
        if "by_airline" in data and len(data["by_airline"]) > 0:
            airline_df = data["by_airline"].to_pandas()
            
            st.markdown("#### Top 15 Airlines by Aircraft Count")
            if "unique_aircraft" in airline_df.columns and "airline_name" in airline_df.columns:
                top_airlines = airline_df.nlargest(15, "unique_aircraft").sort_values("unique_aircraft")
                
                fig = px.bar(
                    top_airlines,
                    x="unique_aircraft",
                    y="airline_name",
                    orientation="h",
                    color="unique_aircraft",
                    color_continuous_scale="Greens",
                    title="Top 15 Airlines by Unique Aircraft",
                    labels={"airline_name": "Airline", "unique_aircraft": "Aircraft"},
                    height=400
                )
                fig.update_layout(
                    coloraxis_colorbar=dict(
                        thickness=20,
                        len=0.7,
                        tickformat=".0f"
                    )
                )
                st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("#### Top Airlines by Records")
            if "total_records" in airline_df.columns and "airline_name" in airline_df.columns:
                top_by_records = airline_df.nlargest(15, "total_records").sort_values("total_records")
                
                fig = px.bar(
                    top_by_records,
                    x="total_records",
                    y="airline_name",
                    orientation="h",
                    color="total_records",
                    color_continuous_scale="Blues",
                    title="Top 15 Airlines by Total Records",
                    labels={"airline_name": "Airline", "total_records": "Records"},
                    height=400
                )
                st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("#### Airline Geographic Coverage")
            if "unique_countries" in airline_df.columns:
                airline_coverage = airline_df.nlargest(10, "unique_countries")[
                    ["airline_name", "unique_aircraft", "unique_countries", "unique_locations", "unique_regions"]
                ].sort_values("unique_countries", ascending=False)
                st.dataframe(airline_coverage, use_container_width=True)

        else:
            st.info("No airline data available")
    
    with tab5:
        st.subheader("Country-Airline Analysis - Geographic Distribution")
        if "by_country_airline" in data and len(data["by_country_airline"]) > 0:
            country_airline_df = data["by_country_airline"].to_pandas()
            
            st.markdown("#### Top 20 Country-Airline Pairs by Records")
            if "total_records" in country_airline_df.columns:
                top_pairs = country_airline_df.nlargest(20, "total_records").sort_values("total_records")
                top_pairs['country_airline'] = top_pairs['origin_country'] + " - " + top_pairs['airline_name']
                
                fig = px.bar(
                    top_pairs,
                    x="total_records",
                    y="country_airline",
                    orientation="h",
                    color="total_records",
                    color_continuous_scale="Purples",
                    title="Top 20 Country-Airline Pairs by Records",
                    labels={"country_airline": "Country-Airline", "total_records": "Records"},
                    height=500
                )
                st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("#### Airline Presence by Country")
            if "origin_country" in country_airline_df.columns and "airline_name" in country_airline_df.columns:
                airlines_per_country = country_airline_df.groupby("origin_country").agg({
                    "airline_name": "count",
                    "total_records": "sum",
                    "unique_aircraft": "sum"
                }).rename(columns={
                    "airline_name": "num_airlines",
                    "total_records": "total_records",
                    "unique_aircraft": "total_aircraft"
                }).sort_values("num_airlines", ascending=False).head(15)
                st.dataframe(airlines_per_country, use_container_width=True)
            
            st.markdown("#### Country-Airline Data Table")
            st.dataframe(country_airline_df, use_container_width=True)
        else:
            st.info("No country-airline data available")
    
    with tab6:
        st.subheader("Time Series Analysis - Snapshot Breakdown")
        if "by_snapshot" in data and len(data["by_snapshot"]) > 0:
            snapshot_df = data["by_snapshot"].to_pandas()
            snapshot_df['snapshot_date'] = snapshot_df['snapshot_id'].str.slice(0, 10)
            agg = snapshot_df.groupby("snapshot_date").agg({
                "total_records": "sum",
                "unique_aircraft": "sum",
                "unique_locations": "sum",
                "unique_regions": "sum",
                "unique_countries": "sum",
                "unique_airports": "sum" if "unique_airports" in snapshot_df.columns else None,
                "avg_altitude": "mean",
                "avg_velocity": "mean"
            }).reset_index()
            st.markdown("#### Snapshot-by-Snapshot Breakdown")
            display_cols = ["snapshot_date", "total_records", "unique_aircraft", "unique_locations", 
                           "unique_regions", "unique_countries", "unique_airports", "avg_altitude", "avg_velocity"]
            display_cols = [c for c in display_cols if c in agg.columns]
            st.dataframe(agg[display_cols], use_container_width=True)
            
        else:
            st.info("No snapshot data available")


# ============================================================================
# ROLLING WINDOWS VIEW
# ============================================================================

else:
    st.subheader("🔄 Rolling Window Analysis")
    
    if not rolling_data:
        st.warning("No rolling window data available. Please run: python 3_gold_and_rolling_aggregations.py")
    else:
        # Extract available window sizes from rolling data keys
        window_sizes = set()
        for key in rolling_data.keys():
            if "rolling_global_" in key:
                # Extract size: "rolling_global_7day" -> "7"
                size_part = key.replace("rolling_global_", "")  # "7day", "30day", etc
                size = size_part.replace("day", "")  # Remove "day" suffix
                window_sizes.add(size)
        
        window_options = {f"{size}-day": size for size in sorted(window_sizes, key=lambda x: int(x))}
        
        selected_window = st.sidebar.selectbox("Select Window Size", options=list(window_options.keys()))
        window_size = window_options[selected_window]
        
        global_tab, country_tab, airline_tab = st.tabs(["🌐 Global Windows", "🌍 Origin Country Windows", "✈️ Airline Windows"])
        
        # ========== GLOBAL WINDOWS ==========
        with global_tab:
            st.markdown(f"#### {selected_window} Global Rolling Windows - Current vs Previous")
            
            global_key = f"rolling_global_{window_size}day"
            if global_key in rolling_data:
                rolling_df = rolling_data[global_key].to_pandas().sort_values("report_period_end", ascending=False)
                
                # Convert window_size to int for lookback calculation
                ws = int(window_size)
                
                if len(rolling_df) > ws:
                    current = rolling_df.iloc[0]
                    previous = rolling_df.iloc[ws]  # Look back by window size for non-overlapping window
                    
                    # Display comparison side-by-side with date ranges
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.markdown("**Current Window**")
                        current_start = current.get('report_period_start', 'N/A')
                        current_end = current.get('report_period_end', 'N/A')
                        st.subheader(f"📅 {current_start} to {current_end}")
                    
                    with col2:
                        st.markdown("**Comparison**")
                    
                    with col3:
                        st.markdown("**Previous Window**")
                        prev_start = current.get('previous_period_start', 'N/A')
                        prev_end = current.get('previous_period_end', 'N/A')
                        st.subheader(f"📅 {prev_start} to {prev_end}")
                    
                    st.divider()
                    
                    # Records comparison
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Records", f"{current['total_records']:,.0f}")
                    with col2:
                        delta_records = current['total_records'] - previous['total_records']
                        st.metric("Δ Records", f"{delta_records:,.0f}", delta=f"{(delta_records/previous['total_records']*100):.1f}%")
                    with col3:
                        st.metric("Records", f"{previous['total_records']:,.0f}")
                    
                    # Aircraft comparison
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Aircraft", f"{current['avg_daily_unique_aircraft']:,.0f}")
                    with col2:
                        delta_aircraft = current['avg_daily_unique_aircraft'] - previous['avg_daily_unique_aircraft']
                        st.metric("Δ Aircraft", f"{delta_aircraft:,.0f}", delta=f"{(delta_aircraft/previous['avg_daily_unique_aircraft']*100):.1f}%")
                    with col3:
                        st.metric("Aircraft", f"{previous['avg_daily_unique_aircraft']:,.0f}")
                    
                    # Altitude comparison
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Altitude (ft)", f"{current['avg_altitude']:,.0f}")
                    with col2:
                        delta_alt = current['avg_altitude'] - previous['avg_altitude']
                        st.metric("Δ Altitude", f"{delta_alt:,.0f}", delta=f"{(delta_alt/previous['avg_altitude']*100):.1f}%")
                    with col3:
                        st.metric("Altitude (ft)", f"{previous['avg_altitude']:,.0f}")
                    
                    # Velocity comparison
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Velocity (kt)", f"{current['avg_daily_velocity']:,.0f}")
                    with col2:
                        delta_vel = current['avg_daily_velocity'] - previous['avg_daily_velocity']
                        st.metric("Δ Velocity", f"{delta_vel:,.0f}", delta=f"{(delta_vel/previous['avg_daily_velocity']*100):.1f}%")
                    with col3:
                        st.metric("Velocity (kt)", f"{previous['avg_daily_velocity']:,.0f}")
                    
                    st.divider()
                    
                    # Countries comparison
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Countries", f"{current['avg_daily_unique_countries']:,.0f}")
                    with col2:
                        delta_countries = current['avg_daily_unique_countries'] - previous['avg_daily_unique_countries']
                        st.metric("Δ Countries", f"{delta_countries:,.0f}", delta=f"{(delta_countries/previous['avg_daily_unique_countries']*100):.1f}%")
                    with col3:
                        st.metric("Countries", f"{previous['avg_daily_unique_countries']:,.0f}")
                    
                    # On-Ground comparison
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("On-Ground", f"{current['total_on_ground']:,.0f}")
                    with col2:
                        delta_ground = current['total_on_ground'] - previous['total_on_ground']
                        st.metric("Δ On-Ground", f"{delta_ground:,.0f}", delta=f"{(delta_ground/previous['total_on_ground']*100):.1f}%" if previous['total_on_ground'] > 0 else "N/A")
                    with col3:
                        st.metric("On-Ground", f"{previous['total_on_ground']:,.0f}")
                    
                    # In-Air comparison
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("In-Air", f"{current['total_in_air']:,.0f}")
                    with col2:
                        delta_air = current['total_in_air'] - previous['total_in_air']
                        st.metric("Δ In-Air", f"{delta_air:,.0f}", delta=f"{(delta_air/previous['total_in_air']*100):.1f}%")
                    with col3:
                        st.metric("In-Air", f"{previous['total_in_air']:,.0f}")
                    
                    # Max Altitude comparison
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Max Altitude (ft)", f"{current['max_altitude']:,.0f}")
                    with col2:
                        delta_max_alt = current['max_altitude'] - previous['max_altitude']
                        st.metric("Δ Max Alt", f"{delta_max_alt:,.0f}", delta=f"{(delta_max_alt/previous['max_altitude']*100):.1f}%")
                    with col3:
                        st.metric("Max Altitude (ft)", f"{previous['max_altitude']:,.0f}")
                elif len(rolling_df) == 1:
                    current = rolling_df.iloc[0]
                    current_start = current.get('report_period_start', 'N/A')
                    current_end = current.get('report_period_end', 'N/A')
                    st.subheader(f"📅 {current_start} to {current_end}")
                    st.info("ℹ️ Only one window available. Previous window data not available for comparison.")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Records", f"{current['total_records']:,.0f}")
                    with col2:
                        st.metric("Aircraft", f"{current['avg_daily_unique_aircraft']:,.0f}")
                    with col3:
                        st.metric("Countries", f"{current['avg_daily_unique_countries']:,.0f}")
                    with col4:
                        st.metric("Altitude (ft)", f"{current['avg_altitude']:,.0f}")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Velocity (kt)", f"{current['avg_daily_velocity']:,.0f}")
                    with col2:
                        st.metric("On-Ground", f"{current['total_on_ground']:,.0f}")
                    with col3:
                        st.metric("In-Air", f"{current['total_in_air']:,.0f}")
                    with col4:
                        st.metric("Max Altitude (ft)", f"{current['max_altitude']:,.0f}")
                    st.dataframe(rolling_df, use_container_width=True)
                else:
                    st.info(f"Not enough data for comparison. Need at least {ws + 1} windows.")
            else:
                st.info(f"No global rolling window data available for {selected_window}")
        
        # ========== COUNTRY WINDOWS ==========
        with country_tab:
            st.markdown(f"#### Origin Country-Level {selected_window} Rolling Windows - Current vs Previous")
            
            country_key = f"rolling_country_{window_size}day"
            
            if country_key in rolling_data:
                country_rolling_df = rolling_data[country_key].to_pandas()
                
                # Show aggregate stats across all countries
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Countries", country_rolling_df["country"].nunique())
                with col2:
                    st.metric("Total Windows", len(country_rolling_df))
                with col3:
                    if "total_records" in country_rolling_df.columns:
                        st.metric("Avg Records/Window", f"{country_rolling_df['total_records'].mean():,.0f}")
                with col4:
                    if "avg_aircraft" in country_rolling_df.columns:
                        st.metric("Avg Aircraft", f"{country_rolling_df['avg_aircraft'].mean():,.0f}")
                
                st.divider()
                
                # Get unique windows sorted by date
                windows_sorted = sorted(country_rolling_df["report_period_end"].unique(), reverse=True)
                ws = int(window_size)
                
                if len(windows_sorted) >= 1:
                    current_window_date = windows_sorted[0]
                    current_window_df = country_rolling_df[country_rolling_df["report_period_end"] == current_window_date].sort_values("total_records", ascending=False)
                    
                    # Add choropleth for current window
                    st.markdown("#### 🌍 Geographic Distribution - Current Window")
                    
                    # Map country names to ISO codes
                    country_iso_map = {
                        "United States": "USA",
                        "United Kingdom": "GBR",
                        "Canada": "CAN",
                        "Germany": "DEU",
                        "Ireland": "IRL",
                        "France": "FRA",
                        "Netherlands": "NLD",
                        "Spain": "ESP",
                        "Italy": "ITA",
                        "Switzerland": "CHE",
                        "Sweden": "SWE",
                        "Norway": "NOR",
                        "Denmark": "DNK",
                        "Belgium": "BEL",
                        "Austria": "AUT",
                        "Poland": "POL",
                        "Portugal": "PRT",
                        "Greece": "GRC",
                        "Japan": "JPN",
                        "China": "CHN",
                        "India": "IND",
                        "Australia": "AUS",
                        "Brazil": "BRA",
                        "Mexico": "MEX",
                        "South Korea": "KOR",
                        "Singapore": "SGP",
                        "Hong Kong": "HKG",
                        "UAE": "ARE",
                        "Saudi Arabia": "SAU",
                        "New Zealand": "NZL",
                        "Thailand": "THA",
                        "Malaysia": "MYS",
                        "Philippines": "PHL",
                        "Indonesia": "IDN",
                        "Vietnam": "VNM",
                        "Taiwan": "TWN",
                        "Czechia": "CZE",
                        "Czech Republic": "CZE",
                        "Russia": "RUS",
                        "Turkey": "TUR",
                        "Israel": "ISR",
                        "Pakistan": "PAK",
                        "Bangladesh": "BGD",
                        "Nigeria": "NGA",
                        "South Africa": "ZAF",
                    }
                    
                    current_window_df_copy = current_window_df.copy()
                    for col, dtype in current_window_df_copy.dtypes.items():
                        if pd.api.types.is_numeric_dtype(dtype):
                            current_window_df_copy[col] = current_window_df_copy[col].fillna(0).round(1)

                    current_window_df_copy["iso_alpha"] = current_window_df_copy["country"].map(country_iso_map)
                    
                    # Get previous period data for comparison if available
                    ws = int(window_size)
                    if len(windows_sorted) > ws:
                        previous_window_date = windows_sorted[ws]
                        previous_window_df_for_diff = country_rolling_df[country_rolling_df["report_period_end"] == previous_window_date]
                        previous_by_country_diff = dict(zip(previous_window_df_for_diff["country"], previous_window_df_for_diff["avg_aircraft"]))
                        current_window_df_copy["prev_aircraft"] = current_window_df_copy["country"].map(previous_by_country_diff).fillna(0)
                        current_window_df_copy["aircraft_change"] = (current_window_df_copy["avg_aircraft"] - current_window_df_copy["prev_aircraft"]).round(1)
                    else:
                        current_window_df_copy["aircraft_change"] = 0.0
                    
                    current_window_with_codes = current_window_df_copy[current_window_df_copy["iso_alpha"].notna()]
                    
                    if len(current_window_with_codes) > 0:
                        # Create quantile bins for coloring based on aircraft change
                        current_window_with_codes["change_bin"] = pd.qcut(
                            current_window_with_codes["aircraft_change"],
                            q=10,
                            duplicates='drop',
                            labels=False
                        )
                        
                        fig = px.choropleth(
                            current_window_with_codes,
                            locations="iso_alpha",
                            color="aircraft_change",
                            hover_name="country",
                            hover_data={
                                "avg_aircraft": ":,.0f",
                                "aircraft_change": ":,.2f",
                                "iso_alpha": False
                            },
                            color_continuous_scale="RdBu_r",
                            title=f"Aircraft Count Change by Country - {selected_window} Window",
                            height=500
                        )
                        fig.update_traces(
                            hovertemplate="<b>%{hovertext}</b><br>Current Aircraft: %{customdata[0]}<br>Change: %{customdata[1]}<extra></extra>"
                        )
                        # Center color scale at 0 to show negative (red) and positive (blue) values
                        max_abs_change = current_window_with_codes["aircraft_change"].abs().max()
                        fig.update_layout(
                            geo=dict(
                                projection_type="natural earth",
                                showland=True,
                                landcolor="rgb(243, 243, 243)",
                                coastlinecolor="rgb(204, 204, 204)",
                            ),
                            coloraxis=dict(
                                cmin=-max_abs_change,
                                cmid=0,
                                cmax=max_abs_change,
                                colorbar=dict(
                                    title="Change",
                                    thickness=20,
                                    len=0.7
                                )
                            )
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    
                    st.divider()
                    
                    # Comparison section
                    if len(windows_sorted) > ws:
                        previous_window_date = windows_sorted[ws]  # Look back by window size
                        previous_window_df = country_rolling_df[country_rolling_df["report_period_end"] == previous_window_date]
                        
                        # Get date ranges
                        current_start = current_window_df['report_period_start'].iloc[0] if len(current_window_df) > 0 else 'N/A'
                        current_end = current_window_df['report_period_end'].iloc[0] if len(current_window_df) > 0 else 'N/A'
                        previous_start = current_window_df['previous_period_start'].iloc[0] if len(current_window_df) > 0 else 'N/A'
                        previous_end = current_window_df['previous_period_end'].iloc[0] if len(current_window_df) > 0 else 'N/A'
                        
                        st.markdown(f"#### 📊 Current vs Previous Period")
                        st.markdown(f"**Current:** {current_start} to {current_end} | **Previous:** {previous_start} to {previous_end}")
                        
                        # Create a comparison dataframe
                        current_by_country = dict(zip(current_window_df["country"], current_window_df["avg_aircraft"]))
                        previous_by_country = dict(zip(previous_window_df["country"], previous_window_df["avg_aircraft"]))
                        
                        # Merge and compare
                        all_countries = set(current_by_country.keys()) | set(previous_by_country.keys())
                        comparison_data = []
                        for country in sorted(all_countries):
                            curr_aircraft = current_by_country.get(country, 0)
                            prev_aircraft = previous_by_country.get(country, 0)
                            change = curr_aircraft - prev_aircraft
                            change_pct = (change / prev_aircraft * 100) if prev_aircraft > 0 else 0
                            comparison_data.append({
                                "Origin Country": country,
                                "Current Aircraft": curr_aircraft,
                                "Previous Aircraft": prev_aircraft,
                                "Change": change,
                                "% Change": change_pct
                            })
                        
                        comparison_df = pd.DataFrame(comparison_data).sort_values("Current Aircraft", ascending=False)
                        st.dataframe(comparison_df, use_container_width=True)
                        
                        # Top changes
                        st.markdown("#### Top 5 Gainers (Current vs Previous)")
                        st.dataframe(comparison_df.nlargest(5, "Change"), use_container_width=True)
                    else:
                        st.info(f"Only one window available. Need at least {ws + 1} unique windows for comparison.")
                
            else:
                st.info(f"No origin country-level data available for {selected_window}")
        
        # ========== AIRLINE WINDOWS ==========
        with airline_tab:
            st.markdown(f"#### {selected_window} Airline Rolling Windows - Top Airlines")
            
            airline_key = f"rolling_airline_{window_size}day"
            
            if airline_key in rolling_data:
                airline_rolling_df = rolling_data[airline_key].to_pandas()
                
                # Show aggregate stats across all airlines
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Airlines", airline_rolling_df["airline_name"].nunique())
                with col2:
                    st.metric("Total Windows", len(airline_rolling_df))
                with col3:
                    if "total_records" in airline_rolling_df.columns:
                        st.metric("Avg Records/Window", f"{airline_rolling_df['total_records'].mean():,.0f}")
                with col4:
                    if "avg_daily_unique_aircraft" in airline_rolling_df.columns:
                        st.metric("Avg Aircraft", f"{airline_rolling_df['avg_daily_unique_aircraft'].mean():,.0f}")
                
                st.divider()
                
                # Get latest window date
                windows_sorted = sorted(airline_rolling_df["report_period_end"].unique(), reverse=True)
                
                if len(windows_sorted) >= 1:
                    current_window_date = windows_sorted[0]
                    current_window_df = airline_rolling_df[airline_rolling_df["report_period_end"] == current_window_date].sort_values("total_records", ascending=False)
                    
                    # Display current window date range
                    st.markdown(f"#### 📅 Current Window: {current_window_date.date()}")
                    
                    # Top airlines by records
                    st.markdown("#### Top 10 Airlines by Records (Current Window)")
                    if "total_records" in current_window_df.columns and "airline_name" in current_window_df.columns:
                        top_airlines = current_window_df.nlargest(10, "total_records")[
                            ["airline_name", "total_records", "avg_daily_unique_aircraft", "avg_altitude", "avg_daily_velocity"]
                        ]
                        st.dataframe(top_airlines, use_container_width=True)
                    
                    # Top airlines by aircraft
                    st.markdown("#### Top 10 Airlines by Aircraft (Current Window)")
                    if "avg_daily_unique_aircraft" in current_window_df.columns and "airline_name" in current_window_df.columns:
                        top_by_aircraft = current_window_df.nlargest(10, "avg_daily_unique_aircraft")[
                            ["airline_name", "avg_daily_unique_aircraft", "total_records", "avg_altitude", "avg_daily_velocity"]
                        ]
                        st.dataframe(top_by_aircraft, use_container_width=True)
                    
                    # On-Ground vs In-Air for top airlines
                    st.markdown("#### Fleet Status - Top 10 Airlines (Current Window)")
                    if "total_on_ground" in current_window_df.columns and "total_in_air" in current_window_df.columns:
                        fleet_status = current_window_df.nlargest(10, "total_records")[
                            ["airline_name", "total_on_ground", "total_in_air", "total_records"]
                        ].copy()
                        fleet_status["ground_pct"] = (fleet_status["total_on_ground"] / fleet_status["total_records"] * 100).round(1)
                        fleet_status["air_pct"] = (fleet_status["total_in_air"] / fleet_status["total_records"] * 100).round(1)
                        st.dataframe(fleet_status, use_container_width=True)
                    
                    # Comparison with previous window (if available)
                    if len(windows_sorted) > int(window_size):
                        st.markdown(f"#### 📊 Comparison: Current vs Previous {selected_window} Window")
                        previous_window_date = windows_sorted[int(window_size)]
                        previous_window_df = airline_rolling_df[airline_rolling_df["report_period_end"] == previous_window_date].sort_values("total_records", ascending=False)
                        
                        # Get common airlines and compare
                        current_airlines = set(current_window_df["airline_name"])
                        previous_airlines = set(previous_window_df["airline_name"])
                        common_airlines = current_airlines & previous_airlines
                        
                        if common_airlines:
                            comparison_data = []
                            for airline in sorted(common_airlines):
                                curr = current_window_df[current_window_df["airline_name"] == airline].iloc[0]
                                prev = previous_window_df[previous_window_df["airline_name"] == airline].iloc[0]
                                
                                change = curr["total_records"] - prev["total_records"]
                                pct_change = (change / prev["total_records"] * 100) if prev["total_records"] > 0 else 0
                                
                                comparison_data.append({
                                    "Airline": airline,
                                    "Current Records": int(curr["total_records"]),
                                    "Previous Records": int(prev["total_records"]),
                                    "Change": int(change),
                                    "% Change": f"{pct_change:+.1f}%"
                                })
                            
                            comparison_df = pd.DataFrame(comparison_data).sort_values("Change", ascending=False)
                            st.dataframe(comparison_df, use_container_width=True)

            else:
                st.info(f"No airline-level rolling window data available for {selected_window}")

# ============================================================================
# FOOTER
# ============================================================================

st.markdown("---")
st.markdown(
    f"""
    <div style='text-align: center; color: gray; margin-top: 30px;'>
    <small>📊 Airplane Data Dashboard | Last Updated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</small>
    </div>
    """,
    unsafe_allow_html=True
)
