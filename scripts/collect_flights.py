import requests
import pandas as pd
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
API_KEY = os.getenv("AVIATIONSTACK_API_KEY")

def collect_flight_data():
    print("Collecting real flight data from AviationStack...")
    print(f"API Key: {API_KEY[:8]}...")

    url = "http://api.aviationstack.com/v1/flights"
    params = {
        "access_key": API_KEY,
        "arr_iata": "CMB",
        "limit": 100
    }

    response = requests.get(url, params=params)
    print(f"Status code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()

        if "data" not in data:
            print("No flight data returned. Response:")
            print(data)
            return None

        flights = data["data"]
        print(f"Received {len(flights)} flights")

        records = []
        for flight in flights:
            try:
                records.append({
                    "flight_date": flight.get("flight_date", ""),
                    "airline": flight.get("airline", {}).get("name", "Unknown"),
                    "flight_number": flight.get("flight", {}).get("iata", ""),
                    "origin_airport": flight.get("departure", {}).get("airport", ""),
                    "origin_iata": flight.get("departure", {}).get("iata", ""),
                    "scheduled_arrival": flight.get("arrival", {}).get("scheduled", ""),
                    "actual_arrival": flight.get("arrival", {}).get("actual", ""),
                    "delay_minutes": flight.get("arrival", {}).get("delay", 0),
                    "flight_status": flight.get("flight_status", ""),
                    "collected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
            except Exception as e:
                print(f"Error processing flight: {e}")
                continue

        if records:
            df = pd.DataFrame(records)
            os.makedirs("data", exist_ok=True)
            df.to_csv("data/flight_data.csv", index=False)
            print(f"\nSaved {len(records)} flight records to data/flight_data.csv")
            print(df.head())

            # Create daily summary for model
            df['flight_date'] = pd.to_datetime(df['flight_date'], errors='coerce')
            daily = df.groupby('flight_date').size().reset_index(name='daily_flights')
            daily.to_csv("data/daily_flight_summary.csv", index=False)
            print(f"\nDaily summary saved to data/daily_flight_summary.csv")
            print(daily)
            return df
        else:
            print("No records processed.")
            return None
    else:
        print(f"API Error: {response.status_code}")
        print(response.text)

        # Free tier limitation — create simulated but realistic flight data
        print("\nFree tier may not support this endpoint.")
        print("Creating realistic simulated flight data instead...")
        create_simulated_flight_data()

def create_simulated_flight_data():
    import numpy as np
    from datetime import timedelta

    np.random.seed(42)
    records = []
    airlines = [
        "SriLankan Airlines", "Emirates", "Qatar Airways",
        "Singapore Airlines", "Cathay Pacific", "Air India",
        "Malaysian Airlines", "Thai Airways", "Flydubai", "IndiGo"
    ]
    origins = [
        "Dubai", "Doha", "Singapore", "London", "Frankfurt",
        "Mumbai", "Delhi", "Bangkok", "Kuala Lumpur", "Hong Kong"
    ]
    origin_iatas = [
        "DXB", "DOH", "SIN", "LHR", "FRA",
        "BOM", "DEL", "BKK", "KUL", "HKG"
    ]

    start_date = datetime(2024, 1, 1)
    for i in range(365 * 2):
        current_date = start_date + timedelta(days=i)
        month = current_date.month

        # Realistic daily flights based on season
        if month in [12, 1, 2, 3]:
            num_flights = np.random.randint(55, 80)
        elif month in [7, 8, 9]:
            num_flights = np.random.randint(35, 55)
        else:
            num_flights = np.random.randint(45, 65)

        for j in range(num_flights):
            idx = np.random.randint(0, len(airlines))
            delay = max(0, int(np.random.normal(15, 20)))
            records.append({
                "flight_date": current_date.strftime("%Y-%m-%d"),
                "airline": airlines[idx],
                "flight_number": f"{airlines[idx][:2].upper()}{np.random.randint(100, 999)}",
                "origin_airport": origins[idx],
                "origin_iata": origin_iatas[idx],
                "scheduled_arrival": f"{np.random.randint(0, 23):02d}:{np.random.randint(0, 59):02d}",
                "actual_arrival": f"{np.random.randint(0, 23):02d}:{np.random.randint(0, 59):02d}",
                "delay_minutes": delay,
                "flight_status": "landed",
                "collected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

    df = pd.DataFrame(records)
    os.makedirs("data", exist_ok=True)
    df.to_csv("data/flight_data.csv", index=False)
    print(f"Saved {len(records)} realistic flight records to data/flight_data.csv")

    # Daily summary
    daily = df.groupby('flight_date').size().reset_index(name='daily_flights')
    daily.to_csv("data/daily_flight_summary.csv", index=False)
    print(f"Daily summary saved: {len(daily)} days")
    print(daily.head(10))

if __name__ == "__main__":
    collect_flight_data()