import requests

API = "http://192.168.1.96:5000"

endpoints = [
    "/health",
    "/sites",
    "/predict?site_id=1&date=2026-05-08",
    "/alert?site_id=1&date=2026-05-08",
    "/green-sites?date=2026-05-08",
    "/model-metrics",
    "/pipeline-status",
    "/best-times?site_id=1&month=5",
    "/flights",
]

print("🚀 Testing all endpoints...\n")

for ep in endpoints:
    url = f"{API}{ep}"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            print(f"✅ GET {ep} — {res.status_code}")
            print(f"   {res.json()}\n")
        else:
            print(f"❌ GET {ep} — HTTP {res.status_code}\n")
    except Exception as e:
        print(f"💥 GET {ep} — {e}\n")

print("Done!")