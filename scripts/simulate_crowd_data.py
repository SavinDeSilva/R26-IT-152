import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

SITES = [
    {"site_id": 1, "site_name": "Sigiriya Rock Fortress", "annual_visitors": 600000, "capacity_per_day": 2500, "category": "Heritage"},
    {"site_id": 2, "site_name": "Galle Fort", "annual_visitors": 500000, "capacity_per_day": 4000, "category": "Heritage"},
    {"site_id": 3, "site_name": "Temple of the Tooth Kandy", "annual_visitors": 700000, "capacity_per_day": 6000, "category": "Religious"},
    {"site_id": 4, "site_name": "Yala National Park", "annual_visitors": 350000, "capacity_per_day": 1200, "category": "Nature"},
    {"site_id": 5, "site_name": "Mirissa Beach", "annual_visitors": 250000, "capacity_per_day": 5000, "category": "Beach"},
    {"site_id": 6, "site_name": "Anuradhapura Sacred City", "annual_visitors": 400000, "capacity_per_day": 4000, "category": "Heritage"},
    {"site_id": 7, "site_name": "Ella Rock", "annual_visitors": 200000, "capacity_per_day": 2000, "category": "Nature"},
    {"site_id": 8, "site_name": "Nuwara Eliya", "annual_visitors": 300000, "capacity_per_day": 6000, "category": "Nature"},
    {"site_id": 9, "site_name": "Dambulla Cave Temple", "annual_visitors": 400000, "capacity_per_day": 4000, "category": "Religious"},
    {"site_id": 10, "site_name": "Horton Plains National Park", "annual_visitors": 180000, "capacity_per_day": 1000, "category": "Nature"},
    {"site_id": 11, "site_name": "Polonnaruwa Ancient City", "annual_visitors": 300000, "capacity_per_day": 3000, "category": "Heritage"},
    {"site_id": 12, "site_name": "Arugam Bay", "annual_visitors": 150000, "capacity_per_day": 4000, "category": "Beach"},
    {"site_id": 13, "site_name": "Pinnawala Elephant Orphanage", "annual_visitors": 400000, "capacity_per_day": 3000, "category": "Nature"},
    {"site_id": 14, "site_name": "Minneriya National Park", "annual_visitors": 160000, "capacity_per_day": 800, "category": "Nature"},
    {"site_id": 15, "site_name": "Adams Peak Sri Pada", "annual_visitors": 250000, "capacity_per_day": 3000, "category": "Religious"},
    {"site_id": 16, "site_name": "Udawalawe National Park", "annual_visitors": 200000, "capacity_per_day": 900, "category": "Nature"},
    {"site_id": 17, "site_name": "Trincomalee", "annual_visitors": 180000, "capacity_per_day": 5000, "category": "Beach"},
    {"site_id": 18, "site_name": "Bentota Beach", "annual_visitors": 220000, "capacity_per_day": 6000, "category": "Beach"},
    {"site_id": 19, "site_name": "Ritigala Forest Monastery", "annual_visitors": 40000, "capacity_per_day": 500, "category": "Heritage"},
    {"site_id": 20, "site_name": "Wilpattu National Park", "annual_visitors": 120000, "capacity_per_day": 600, "category": "Nature"},
    {"site_id": 21, "site_name": "Colombo National Museum", "annual_visitors": 200000, "capacity_per_day": 3000, "category": "Heritage"},
    {"site_id": 22, "site_name": "Gangaramaya Temple", "annual_visitors": 300000, "capacity_per_day": 5000, "category": "Religious"},
    {"site_id": 23, "site_name": "Hikkaduwa Beach", "annual_visitors": 280000, "capacity_per_day": 6000, "category": "Beach"},
    {"site_id": 24, "site_name": "Ambuluwawa Tower", "annual_visitors": 100000, "capacity_per_day": 2000, "category": "Nature"},
    {"site_id": 25, "site_name": "Knuckles Mountain Range", "annual_visitors": 90000, "capacity_per_day": 1000, "category": "Nature"},
    {"site_id": 26, "site_name": "Bundala National Park", "annual_visitors": 80000, "capacity_per_day": 600, "category": "Nature"},
    {"site_id": 27, "site_name": "Kalpitiya Beach", "annual_visitors": 100000, "capacity_per_day": 3000, "category": "Beach"},
    {"site_id": 28, "site_name": "Nalanda Gedige", "annual_visitors": 50000, "capacity_per_day": 500, "category": "Heritage"},
    {"site_id": 29, "site_name": "Mulgirigala Rock Temple", "annual_visitors": 70000, "capacity_per_day": 1000, "category": "Religious"},
    {"site_id": 30, "site_name": "Pidurangala Rock", "annual_visitors": 130000, "capacity_per_day": 2000, "category": "Nature"},
]

HIGH_IMPACT_DATES = [
    "2024-01-14","2024-02-04","2024-04-13","2024-04-14",
    "2024-05-01","2024-05-23","2024-05-24","2024-07-20",
    "2024-07-27","2024-10-31","2024-12-25","2024-12-31",
    "2025-01-14","2025-02-04","2025-04-13","2025-04-14",
    "2025-05-01","2025-05-12","2025-05-13","2025-06-10",
    "2025-07-10","2025-07-11","2025-10-20","2025-12-25",
    "2025-12-31","2026-04-13","2026-04-14","2026-05-22",
    "2026-05-23","2026-07-20","2026-10-20","2026-12-25",
]

def get_season(month):
    if month in [12, 1, 2, 3]:
        return ("peak", 1.6)
    elif month in [4, 5, 6]:
        return ("shoulder", 1.0)
    elif month in [7, 8, 9]:
        return ("low", 0.8)
    else:
        return ("shoulder", 1.1)

def get_monthly_weather(month):
    weather = {
        1: (27, 45), 2: (28, 30), 3: (29, 55),
        4: (29, 120), 5: (28, 180), 6: (27, 160),
        7: (27, 130), 8: (27, 110), 9: (27, 130),
        10: (27, 200), 11: (27, 300), 12: (27, 150)
    }
    return weather.get(month, (27, 100))

def generate_crowd_data():
    print("Generating simulated crowd data...")
    records = []
    np.random.seed(42)

    start_date = datetime(2024, 1, 1)
    end_date = datetime(2025, 12, 31)
    current_date = start_date

    while current_date <= end_date:
        date_str = current_date.strftime("%Y-%m-%d")
        day_of_week = current_date.weekday()
        is_weekend = 1 if day_of_week >= 5 else 0
        is_holiday = 1 if date_str in HIGH_IMPACT_DATES else 0
        month = current_date.month
        season, season_mult = get_season(month)
        temp, rainfall = get_monthly_weather(month)

        season_mult_flight = season_mult
        daily_flights = int(np.random.normal(65 * season_mult_flight, 8))
        daily_flights = max(20, min(100, daily_flights))

        for site in SITES:
            base_daily = site["annual_visitors"] / 365
            weekend_mult = 1.4 if is_weekend else 1.0
            holiday_mult = 1.8 if is_holiday else 1.0
            noise = np.random.normal(1.0, 0.15)

            estimated_visitors = int(
                base_daily * season_mult * weekend_mult * holiday_mult * noise
            )
            estimated_visitors = max(0, min(estimated_visitors, site["capacity_per_day"]))

            crowd_score = round(estimated_visitors / site["capacity_per_day"], 3)
            crowd_score = min(crowd_score, 1.0)

            if crowd_score >= 0.75:
                risk_level = "High"
            elif crowd_score >= 0.45:
                risk_level = "Medium"
            else:
                risk_level = "Low"

            records.append({
                "date": date_str,
                "site_id": site["site_id"],
                "site_name": site["site_name"],
                "category": site["category"],
                "day_of_week": day_of_week,
                "month": month,
                "season": season,
                "is_weekend": is_weekend,
                "is_public_holiday": is_holiday,
                "avg_temperature_c": temp,
                "avg_rainfall_mm": rainfall,
                "daily_flights_at_cmb": daily_flights,
                "capacity_per_day": site["capacity_per_day"],
                "estimated_daily_visitors": estimated_visitors,
                "crowd_score_normalized": crowd_score,
                "risk_level": risk_level
            })

        current_date += timedelta(days=1)

    df = pd.DataFrame(records)
    os.makedirs("data", exist_ok=True)
    df.to_csv("data/simulated_crowd_data.csv", index=False)

    print(f"\nDone! Generated {len(df)} records")
    print(f"Date range: {df['date'].min()} to {df['date'].max()}")
    print(f"\nRisk level distribution:")
    print(df['risk_level'].value_counts())
    print(f"\nSample:")
    print(df.head())

if __name__ == "__main__":
    generate_crowd_data()