import pandas as pd
import os

def merge_all_data():
    print("Loading all datasets...")

    # Load simulated crowd data
    crowd_df = pd.read_csv("data/simulated_crowd_data.csv")
    crowd_df['date'] = pd.to_datetime(crowd_df['date'])
    print(f"Crowd data: {len(crowd_df)} records")

    # Load tourist sites
    sites_df = pd.read_csv("data/tourist_sites.csv")
    print(f"Tourist sites: {len(sites_df)} records")

    # Load holidays
    holidays_df = pd.read_csv("data/holidays_events.csv")
    holidays_df['date'] = pd.to_datetime(holidays_df['date'])
    print(f"Holidays: {len(holidays_df)} records")

    # Load weather
    weather_df = pd.read_csv("data/weather_data.csv")
    print(f"Weather data: {len(weather_df)} records")

    print("\nMerging datasets...")

    # Merge crowd data with site info
    merged = crowd_df.merge(
        sites_df[['site_id', 'district', 'province',
                  'latitude', 'longitude',
                  'is_eco_friendly', 'is_unesco',
                  'entrance_fee_lkr']],
        on='site_id',
        how='left'
    )

    # Add festival period flag from holidays
    high_impact_dates = set(
        holidays_df[holidays_df['expected_impact_level'].isin(['High', 'Very High'])]
        ['date'].dt.strftime('%Y-%m-%d')
    )
    merged['is_festival_period'] = merged['date'].dt.strftime('%Y-%m-%d').isin(
        high_impact_dates
    ).astype(int)

    # Add district info
    merged['district_encoded'] = pd.factorize(merged['district'])[0]
    merged['category_encoded'] = pd.factorize(merged['category'])[0]
    merged['season_encoded'] = pd.factorize(merged['season'])[0]

    # Final columns
    final_columns = [
        'date', 'site_id', 'site_name', 'district', 'province',
        'category', 'latitude', 'longitude',
        'day_of_week', 'month', 'season', 'is_weekend',
        'is_public_holiday', 'is_festival_period',
        'avg_temperature_c', 'avg_rainfall_mm',
        'daily_flights_at_cmb', 'is_eco_friendly', 'is_unesco',
        'entrance_fee_lkr', 'capacity_per_day',
        'estimated_daily_visitors', 'crowd_score_normalized',
        'risk_level', 'district_encoded',
        'category_encoded', 'season_encoded'
    ]

    final_df = merged[final_columns]

    os.makedirs("data", exist_ok=True)
    final_df.to_csv("data/master_dataset.csv", index=False)

    print(f"\nMaster dataset created successfully")
    print(f"Total records: {len(final_df)}")
    print(f"Total columns: {len(final_df.columns)}")
    print(f"\nColumns:")
    for col in final_df.columns:
        print(f"  - {col}")
    print(f"\nRisk level distribution:")
    print(final_df['risk_level'].value_counts())
    print(f"\nSample data:")
    print(final_df.head())

    return final_df

if __name__ == "__main__":
    merge_all_data()