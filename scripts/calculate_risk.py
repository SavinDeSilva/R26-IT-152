import pandas as pd

# Load merged dataset
df = pd.read_csv("data/merged_data.csv")

# Simple risk calculation
def calculate_risk(row):
    risk = 0

    # Example thresholds
    if row.get("temperature_c", 0) > 35:
        risk += 2
    if row.get("wind_speed_ms", 0) > 8:
        risk += 2
    if row.get("rainfall_mm", 0) > 5:
        risk += 3
    if row.get("crowd_level", 0) > 70:
        risk += 3

    return risk

df["risk_score"] = df.apply(calculate_risk, axis=1)

# Save risk scores
df.to_csv("data/risk_scores.csv", index=False)
print("Risk scores saved to data/risk_scores.csv")