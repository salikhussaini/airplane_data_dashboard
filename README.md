# ✈️ Airplane Data Dashboard

A comprehensive Streamlit dashboard for visualizing and analyzing airplane flight data with advanced aggregations and rolling window analysis.

**🚀 Live Dashboard**: [View the Live Dashboard](https://airplane-data-dashboard.streamlit.app/)

## Features

### 📊 Summary View
- **Overview Dashboard**: Key metrics including data date range, aircraft counts, altitude statistics
- **Aircraft Analysis**: Top aircraft visualizations, geographic diversity metrics, detailed aircraft data table
- **Geographic Analysis**: 
  - Global choropleth map showing unique aircraft distribution by country
  - Top 15 countries by aircraft count
  - Country-level KPIs and geographic diversity metrics
- **Time Series Analysis**: Snapshot-by-snapshot breakdown with temporal trends
- **Comprehensive Metrics**:
  - Unique aircraft, altitudes, countries, locations, regions
  - Aircraft per country, per location, per region
  - Total records and in-air/on-ground splits

### 🔄 Rolling Windows Analysis
- **Configurable Window Sizes**: 1-day, 3-day, 7-day, 14-day, and 30-day rolling windows
- **Global Windows Tab**:
  - Current vs. Previous window comparison
  - Metrics: Records, Aircraft, Altitude, Velocity, Countries, On-Ground/In-Air counts
  - Delta calculations with percentage changes
  - Full rolling window data tables
- **Origin Country Windows Tab**:
  - Geographic distribution choropleth with aircraft changes
  - Country-level comparisons across periods
  - Top gainers/losers tracking
  - Aggregate statistics across all countries

## Project Structure

```
aircraft_dashboard/
├── main.py                    # Streamlit application
├── config.py                  # Configuration (GOLD_DATA_DIR setting)
├── requirements.txt           # Python dependencies
├── .streamlit/               # Streamlit configuration folder
│   └── config.toml           # Streamlit app configuration
├── gold_data/                # Data storage directory
│   ├── master/              # Master aggregated data files
│   │   └── gold_master_all_*.parquet
│   └── README.md            # Data documentation
└── README.md                # This file
```

## Setup Instructions

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Installation

1. **Clone or navigate to the project directory**:
   ```bash
   cd aircraft_dashboard
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate
   
   # macOS/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

### Configuration

1. **Create or verify `config.py`** in the project root:
   ```python
   from pathlib import Path
   
   # Directory where parquet data files are stored
   GOLD_DATA_DIR = Path(__file__).parent / "gold_data"
   ```

2. **Prepare data files**:
   - Place your parquet files in the `gold_data/` or `gold_data/master/` directory
   - Files should follow the naming pattern: `gold_master_all_*.parquet`
   - Files should contain columns for report_type, gold_type/rolling_type, and relevant metrics

## Running the Dashboard

### Local Development
Start the Streamlit app locally:
```bash
streamlit run main.py
```

The dashboard will open in your default browser at `http://localhost:8501`

### View Live Dashboard
Visit the deployed version at: [https://airplane-data-dashboard.streamlit.app/](https://airplane-data-dashboard.streamlit.app/)

## Data Format Requirements

### Master Data Structure
The dashboard expects a Parquet file with the following columns:

**For Summary Data (report_type="all")**:
- `report_type`: "all"
- `gold_type`: one of ["gold_by_country", "gold_by_aircraft", "gold_by_snapshot", "gold_summary"]
- `report_period`, `report_period_start`, `report_period_end`
- `metric`, `value` (for gold_summary)
- Additional columns based on gold_type

**For Rolling Window Data (report_type="rolling")**:
- `report_type`: "rolling"
- `rolling_type`: one of ["r12_1day", "r12_3day", "r12_7day", "r12_14day", "r12_30day"]
- `report_period`, `report_period_start`, `report_period_end`
- `previous_period_start`, `previous_period_end`
- Aggregated metrics: `total_records`, `avg_daily_unique_aircraft`, `avg_altitude`, `avg_daily_velocity`, etc.
- `country` (nullable for global vs. by-country data)

## Key Columns by Section

### Summary View
- **Summary Tab**: metric, value, min_date, max_date, total_records, unique_aircraft, avg_altitude, unique_countries, etc.
- **Aircraft Tab**: icao24, callsign, record_count, num_locations_visited, num_regions_visited, primary_location, primary_region
- **Country Tab**: origin_country, total_records, unique_aircraft, unique_locations, unique_regions, unique_country_codes
- **Snapshot Tab**: snapshot_id, snapshot_date, total_records, unique_aircraft, unique_locations, unique_regions, unique_countries, avg_altitude, avg_velocity

### Rolling Windows
- **Global**: total_records, avg_daily_unique_aircraft, avg_altitude, avg_daily_velocity, avg_daily_unique_countries, total_on_ground, total_in_air, max_altitude
- **By Country**: country, total_records, avg_aircraft, (other aggregated metrics), report_period_start, report_period_end, previous_period_start, previous_period_end

## Dependencies

- **streamlit**: Web framework for interactive dashboards
- **polars**: High-performance dataframe library for reading Parquet files
- **pandas**: Data manipulation and analysis
- **plotly**: Interactive visualization library

See [requirements.txt](requirements.txt) for version specifications.

## Features in Detail

### Geographic Visualizations
- **Choropleth Maps**: Shows data distribution across countries with quantile-based coloring
- **Color Scales**: 
  - PRGn diverging scale for aircraft distribution
  - RdBu_r diverging scale for change metrics (red=decrease, blue=increase)

### Comparison Metrics
- **Current vs. Previous**: Each rolling window compares current period with previous non-overlapping period
- **Delta Calculations**: Absolute differences and percentage changes
- **Trend Indicators**: Up/down indicators (using Streamlit's delta parameter)

### Caching
- Data loading is cached using Streamlit's `@st.cache_data` for performance
- Automatic cache invalidation on file updates

## Troubleshooting

### "No master data file found" error
- Ensure `config.py` exists with correct `GOLD_DATA_DIR` path
- Verify parquet files exist in `gold_data/` or `gold_data/master/` directory
- File names must match pattern: `gold_master_all_*.parquet`

### Slow performance
- Check data file size
- Consider pre-filtering large datasets before creating Parquet files
- Clear cache: `streamlit cache clear`

### Missing columns
- Verify your data includes all required columns
- Check data pipeline that generates the parquet files
- Refer to "Data Format Requirements" section above

## Future Enhancements

Potential features to add:
- Real-time data refresh with WebSocket integration
- Custom date range selector
- Export capabilities (CSV, PDF)
- User authentication and access control
- Data quality metrics and validation
- Predictive analytics and anomaly detection
- Mobile-responsive design improvements

## License

[Add your license information here]

## Contact

For issues, questions, or suggestions, please create an issue or contact the project maintainer.

---

**Last Updated**: August 2026  
**Dashboard Version**: 1.0
