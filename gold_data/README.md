# Gold Data Directory

This directory contains the aggregated and processed airplane flight data used by the dashboard.

## Structure

```
gold_data/
├── master/
│   └── gold_master_all_*.parquet    # Master aggregated data files
└── README.md                         # This file
```

## File Format

The dashboard expects parquet files named with the pattern: `gold_master_all_*.parquet`

Each file should contain aggregated data with the following structure:

### Report Types
- **report_type="all"**: Summary aggregations (gold data)
- **report_type="rolling"**: Rolling window analysis data

### For Gold Data (report_type="all")
Gold types include:
- `gold_by_country`: Aggregations grouped by origin country
- `gold_by_aircraft`: Aggregations grouped by aircraft ICAO24 code
- `gold_by_snapshot`: Time-based snapshot aggregations
- `gold_summary`: Overall summary statistics

### For Rolling Window Data (report_type="rolling")
Rolling types include:
- `r12_1day`: 1-day rolling window
- `r12_3day`: 3-day rolling window
- `r12_7day`: 7-day rolling window
- `r12_14day`: 14-day rolling window
- `r12_30day`: 30-day rolling window

## Data Pipeline

To generate the required master parquet file:

1. Process raw airplane flight data (ADS-B, MLAT, etc.)
2. Create gold aggregations for:
   - Geographic analysis (by country)
   - Aircraft analysis (by ICAO24 code)
   - Time-based snapshots
   - Summary statistics
3. Generate rolling window aggregations at multiple time scales
4. Combine all aggregations into a single master parquet file
5. Save as `gold_master_all_<timestamp>.parquet` in this directory

## Required Columns

### Common Columns
- `report_type`: "all" or "rolling"
- `report_period`: Period identifier
- `report_period_start`: Start datetime
- `report_period_end`: End datetime

### For Gold Data
- `gold_type`: Type of aggregation
- `metric`: Metric name (for summary data)
- `value`: Metric value

### For Rolling Window Data
- `rolling_type`: Type of rolling window
- `country`: Origin country (nullable for global aggregations)
- `total_records`: Total number of records in the window
- `avg_daily_unique_aircraft`: Average unique aircraft per day
- `avg_altitude`: Average altitude in feet
- `avg_daily_velocity`: Average velocity in knots
- `avg_daily_unique_countries`: Average unique countries per day
- `total_on_ground`: Total records with ground status
- `total_in_air`: Total records with in-air status
- `max_altitude`: Maximum altitude observed
- `previous_period_start`: Start of previous comparison period
- `previous_period_end`: End of previous comparison period

## Notes

- Files are cached by Streamlit for performance
- Clear cache with: `streamlit cache clear`
- The dashboard searches recursively for files matching the naming pattern
- Larger files may take longer to load; consider partitioning by date ranges if needed

