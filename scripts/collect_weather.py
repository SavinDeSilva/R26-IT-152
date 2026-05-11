import requests
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("OPENWEATHER_API_KEY")

TOURIST_SITES = [
    {"name": "Sigiriya", "lat": 7.9570, "lon": 80.7603},
    {"name": "Galle Fort", "lat": 6.0328, "lon": 80.2168},
    {"name": "Kandy Temple", "lat": 7.2936, "lon": 80.6413},
    {"name": "Mirissa Beach", "lat": 5.9483, "lon": 80.4716},
    {"name": "Yala National Park", "lat": 6.3728, "lon": 81.5216},
    {"name": "Anuradhapura", "lat": 8.3114, "lon": 80.4037},
    {"name": "Ella", "lat": 6.8667, "lon": 81.0466},
    {"name": "Nuwara Eliya", "lat": 6.9497, "lon": 80.7891},
    {"name": "Dambulla", "lat": 7.8568, "lon": 80.6487},
    {"name": "Horton Plains", "lat": 6.8016, "lon": 80.8044},
    {"name": "Polonnaruwa", "lat": 7.9403, "lon": 81.0188},
    {"name": "Arugam Bay", "lat": 6.8397, "lon": 81.8310},
    {"name": "Pinnawala", "lat": 7.3006, "lon": 80.3498},
    {"name": "Adams Peak", "lat": 6.8096, "lon": 80.4994},
    {"name": "Trincomalee", "lat": 8.5922, "lon": 81.2152},
    {"name": "Bentota", "lat": 6.4239, "lon": 79.9958},
    {"name": "Hikkaduwa", "lat": 6.1395, "lon": 80.1063},
    {"name": "Wilpattu", "lat": 8.4557, "lon": 80.0148},
    {"name": "Colombo Museum", "lat": 6.9020, "lon": 79.8612},
    {"name": "Pidurangala", "lat": 7.9667, "lon": 80.7500},
]

def get_weather(site):
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "lat": site["lat"],
        "lon": site["lon"],
        "appid": API_KEY,
        "units": "metric"
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        return {
            "site_name": site["name"],
            "latitude": site["lat"],
            "longitude": site["lon"],
            "temperature_c": data["main"]["temp"],
            "humidity_percent": data["main"]["humidity"],
            "weather_description": data["weather"][0]["description"],
            "wind_speed_ms": data["wind"]["speed"],
            "rainfall_mm": data.get("rain", {}).get("1h", 0),
            "timestamp": pd.Timestamp.now()
        }
    else:
        print(f"Error for {site['name']}: {response.status_code}")
        return None

def collect_all_weather():
    print("Collecting weather data...")
    results = []
    for site in TOURIST_SITES:
        print(f"  Fetching: {site['name']}...")
        weather = get_weather(site)
        if weather:
            results.append(weather)
    if results:
        df = pd.DataFrame(results)
        os.makedirs("data", exist_ok=True)
        df.to_csv("data/weather_data.csv", index=False)
        print(f"\nDone! Saved {len(results)} records to data/weather_data.csv")
        print(df)
    else:
        print("No data collected. Check your API key.")

if __name__ == "__main__":
    collect_all_weather()