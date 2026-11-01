"""Fictional sample records. Everything here is marked is_demo=True. UI/workflow testing only."""
from datetime import date, datetime, timedelta, timezone

LABEL = "Sample data - fictional values for UI and workflow testing only. Not current real-world conditions."

SAMPLE_LOCATIONS = [
    {"id": "demo_1", "village_or_mandal": "Sample Mandal A", "district": "Sample District A",
     "state": "Sample State", "latitude": None, "longitude": None, "is_demo": True},
    {"id": "demo_2", "village_or_mandal": "Sample Mandal B", "district": "Sample District B",
     "state": "Sample State", "latitude": None, "longitude": None, "is_demo": True},
]

# (tmax, tmin, rain_mm, rain_prob_pct, wind_kmh) for 7 days
_FORECASTS = {
    "demo_1": [(34, 24, 0, 10, 14), (33, 24, 12, 70, 16), (31, 23, 46, 88, 22), (32, 23, 5, 40, 15),
               (34, 24, 0, 15, 12), (35, 25, 0, 10, 11), (35, 25, 0, 5, 10)],
    "demo_2": [(38, 27, 0, 5, 18), (41, 28, 0, 0, 20), (40, 28, 0, 10, 19), (37, 27, 8, 50, 25),
               (36, 26, 15, 60, 22), (35, 26, 2, 30, 18), (36, 26, 0, 10, 16)],
}
_CURRENT = {"demo_1": (31.5, 58, 0.0, 12.4), "demo_2": (36.2, 44, 0.0, 17.8)}


def sample_weather_raw(location_id: str) -> dict:
    lid = location_id if location_id in _FORECASTS else "demo_1"
    today = date.today()
    t, h, p, w = _CURRENT[lid]
    now = datetime.now().strftime("%Y-%m-%dT%H:%M")
    forecast = [{"date": (today + timedelta(days=i)).isoformat(), "temp_max_c": a, "temp_min_c": b,
                 "precipitation_sum_mm": c, "precipitation_probability_pct": d,
                 "wind_speed_max": e, "wind_speed_unit": "km/h"} for i, (a, b, c, d, e) in enumerate(_FORECASTS[lid])]
    current = {"time": now, "temperature_c": t, "humidity_pct": h, "precipitation_mm": p,
               "wind_speed": w, "wind_speed_unit": "km/h"}
    return {"current": current, "forecast": forecast, "location": {"sample_id": lid}}


def sample_mandi(crop_id: str) -> list[dict]:
    """Three markets today + one older record (different date)."""
    table = {"groundnut": 6000, "paddy": 2200, "cotton": 6800}
    base = table.get(crop_id)
    if base is None:
        return []
    names = {"groundnut": "Groundnut", "paddy": "Paddy(Dhan)(Common)", "cotton": "Cotton"}
    today = date.today()
    rows = [("Sample Market A", 0, 0), ("Sample Market B", 0, 150), ("Sample Market C", 0, -80),
            ("Sample Market D", 2, 60)]
    fetched = datetime.now(timezone.utc).isoformat()
    out = []
    for market, age, delta in rows:
        modal = base + delta
        out.append({"market": market, "district": "Sample District A", "state": "Sample State",
                    "commodity": names[crop_id], "variety": "Sample variety",
                    "price_date": (today - timedelta(days=age)).isoformat(),
                    "min_price": modal - 200, "modal_price": modal, "max_price": modal + 250,
                    "unit": "INR/quintal", "source": "demo", "fetched_at": fetched, "is_demo": True})
    return out


SAMPLE_SOIL = [
    {"id": "demo_soil_1", "ph": 6.5, "nitrogen": 120, "nitrogen_unit": "kg/ha", "phosphorus": 40,
     "phosphorus_unit": "kg/ha", "potassium": 80, "potassium_unit": "kg/ha", "organic_carbon": 0.6,
     "organic_carbon_unit": "%", "soil_source": "sample", "is_demo": True},
    {"id": "demo_soil_2", "ph": 7.8, "nitrogen": 300, "nitrogen_unit": "kg/ha", "phosphorus": 12,
     "phosphorus_unit": "kg/ha", "potassium": 150, "potassium_unit": "kg/ha", "organic_carbon": 0.9,
     "organic_carbon_unit": "%", "soil_source": "sample", "is_demo": True},
]

SAMPLE_CROP_PROFILES = [
    {"location_id": "demo_1", "crop_id": "groundnut", "growth_stage": "flowering", "sowing_date": None, "is_demo": True},
    {"location_id": "demo_2", "crop_id": "paddy", "growth_stage": "vegetative", "sowing_date": None, "is_demo": True},
    {"location_id": "demo_2", "crop_id": "cotton", "growth_stage": "sowing", "sowing_date": None, "is_demo": True},
]
