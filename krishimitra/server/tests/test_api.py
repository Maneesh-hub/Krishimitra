import shutil
import subprocess
from pathlib import Path

import httpx
import pytest

from app.services import ai_service, mandi_service, weather_service
from tests.conftest import advisory_body


def test_health_endpoint_returns_ok(client, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "super-secret-value")
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"
    assert r.json()["services"]["ai"]["configured"] is True
    assert "super-secret-value" not in r.text


def test_crops_list_is_non_empty(client):
    crops = client.get("/api/crops").json()["crops"]
    assert crops and all(c["id"] and c["name"] for c in crops)


def test_invalid_coordinates_are_rejected(client):
    r = client.get("/api/weather", params={"latitude": 95, "longitude": 10})
    assert r.status_code == 422 and r.json()["error"]["code"] == "INVALID_COORDINATES"
    r = client.get("/api/weather")
    assert r.status_code == 400 and r.json()["error"]["code"] == "LOCATION_REQUIRED"


def test_missing_crop_is_rejected_for_crop_advisory(client):
    body = advisory_body("Should I irrigate?")
    body["context"]["crop"] = {}
    r = client.post("/api/advisory", json=body)
    assert r.status_code == 400 and r.json()["error"]["code"] == "CROP_REQUIRED"


def test_soil_ph_out_of_range_is_rejected(client):
    for bad in (-1, 15):
        r = client.post("/api/soil/analyze", json={"ph": bad})
        assert r.status_code == 422 and r.json()["error"]["code"] == "INVALID_SOIL_PH"


def test_npk_without_units_is_not_interpreted(client):
    r = client.post("/api/soil/analyze", json={"ph": 6.5, "nitrogen": 120, "phosphorus": 40, "potassium": 80})
    items = {i["parameter"]: i for i in r.json()["items"]}
    assert items["ph"]["status"] == "interpreted"
    for n in ("nitrogen", "phosphorus", "potassium"):
        assert items[n]["status"] == "not_interpreted" and items[n]["band"] is None


def test_npk_with_units_gets_cautious_interpretation(client):
    r = client.post("/api/soil/analyze", json={"ph": 6.5, "nitrogen": 120, "nitrogen_unit": "kg/ha"})
    assert r.json()["is_user_provided"] is True
    assert any("laboratory" in c.lower() for c in r.json()["cautions"])


def test_weather_provider_failure_is_reported(client, monkeypatch):
    def boom(*a, **k):
        raise httpx.ConnectError("down")
    monkeypatch.setattr(weather_service, "_http_get", boom)
    r = client.get("/api/weather", params={"latitude": 14.7, "longitude": 77.6})
    j = r.json()
    assert j["status"] == "unavailable" and j["is_demo"] is False and j["current"] is None
    assert j["warnings"][0]["code"] == "WEATHER_UNAVAILABLE"


def test_weather_live_parse_and_missing_field_has_no_alert(client, monkeypatch):
    raw = {"latitude": 14.7, "longitude": 77.6, "timezone": "Asia/Kolkata",
           "current": {"time": "2026-10-31T10:00", "temperature_2m": 30.1, "relative_humidity_2m": None, "precipitation": 0, "wind_speed_10m": 9},
           "current_units": {"wind_speed_10m": "km/h"}, "daily_units": {"wind_speed_10m_max": "km/h"},
           "daily": {"time": ["2026-10-31"], "temperature_2m_max": [None], "temperature_2m_min": [22],
                     "precipitation_sum": [None], "precipitation_probability_max": [None], "wind_speed_10m_max": [12]}}
    monkeypatch.setattr(weather_service, "_http_get", lambda *a, **k: raw)
    j = client.get("/api/weather", params={"latitude": 14.7, "longitude": 77.6}).json()
    assert j["status"] == "live" and j["current"]["humidity_pct"] is None
    assert j["alerts"] == []  # missing rain/temperature values never create alerts


def test_mandi_provider_failure_does_not_masquerade_as_live_data(client, monkeypatch):
    monkeypatch.setenv("MANDI_API_BASE_URL", "https://example.invalid/resource")
    def boom(*a, **k):
        raise httpx.ConnectError("down")
    monkeypatch.setattr(mandi_service, "_http_get", boom)
    j = client.get("/api/mandi/prices", params={"crop": "groundnut", "state": "Andhra Pradesh"}).json()
    assert j["status"] == "unavailable" and j["records"] == [] and j["is_demo"] is False
    assert j["warnings"][0]["code"] == "MANDI_UNAVAILABLE"


def test_mandi_not_configured_is_unavailable_not_sample(client):
    j = client.get("/api/mandi/prices", params={"crop": "paddy", "state": "Telangana"}).json()
    assert j["status"] == "unavailable" and j["records"] == []


def test_mandi_live_records_are_normalised_and_unit_not_assumed(client, monkeypatch):
    monkeypatch.setenv("MANDI_API_BASE_URL", "https://example.invalid/resource")
    today = mandi_service.date.today().strftime("%d/%m/%Y")
    rec = {"state": "AP", "district": "Anantapur", "market": "M1", "commodity": "Groundnut", "variety": "Bold",
           "arrival_date": today, "min_price": "5000", "modal_price": "5500", "max_price": "6000"}
    monkeypatch.setattr(mandi_service, "_http_get", lambda *a, **k: {"records": [rec, rec, {"commodity": "Groundnut"}]})
    j = client.get("/api/mandi/prices", params={"crop": "groundnut", "state": "AP"}).json()
    assert j["status"] == "live" and len(j["records"]) == 1 and j["skipped_count"] == 1
    assert j["records"][0]["unit"] is None and j["comparison"]["groups"] == []


def test_mandi_comparison_only_for_same_unit_and_date():
    base = dict(commodity="Groundnut", price_date="2026-10-30", source="x", state="s", district="d")
    recs = [{**base, "market": "A", "modal_price": 100, "unit": "Rs/Quintal"},
            {**base, "market": "B", "modal_price": 200, "unit": "Rs/Quintal"},
            {**base, "market": "C", "modal_price": 999, "unit": "Rs/Kg"},
            {**base, "market": "D", "modal_price": 300, "unit": "Rs/Quintal", "price_date": "2026-10-01"}]
    groups = mandi_service.compare(recs)["groups"]
    assert len(groups) == 1 and [r["market"] for r in groups[0]["records"]] == ["B", "A"]


def test_demo_records_are_marked_as_sample(client):
    j = client.get("/api/demo").json()
    assert j["is_demo"] is True and len(j["locations"]) >= 2 and len(j["mandi"]) >= 3
    assert all(l["is_demo"] for l in j["locations"]) and all(s["is_demo"] for s in j["soil"])
    for w in j["weather"].values():
        assert w["status"] == "sample" and w["is_demo"] is True and w["source"] == "demo"
    for m in j["mandi"].values():
        assert m["is_demo"] and all(r["is_demo"] and r["source"] == "demo" for r in m["records"])


def test_ai_stub_returns_demo_mode_without_api_key(client):
    q = "There may be rain tomorrow. Should I irrigate my groundnut field today?"
    j = client.post("/api/advisory", json=advisory_body(q)).json()
    assert j["mode"] == "rule_based_demo" and j["actions"] and j["request_id"]
    assert "unavailable" in j["summary"].lower()  # no weather supplied -> must say so (Scenario 5)
    assert j["status"] == "partial" and "weather" in j["missing_sources"]


def test_demo_advisory_uses_supplied_weather_only(client):
    w = client.get("/api/weather", params={"demo": "true"}).json()
    j = client.post("/api/advisory", json=advisory_body("Should I irrigate today?", weather=w)).json()
    assert "rain probability" in j["summary"] and any("Weather forecast" in d for d in j["data_used"])


def test_pesticide_dose_request_gets_no_dosage(client):
    j = client.post("/api/advisory", json=advisory_body("What exact pesticide dose should I spray?")).json()
    assert "label" in j["summary"].lower() and not any(ch.isdigit() for ch in j["summary"])


def test_unknown_question_without_api_key_returns_not_configured(client):
    r = client.post("/api/advisory", json=advisory_body("Tell me a story about the moon"))
    assert r.status_code == 503 and r.json()["error"]["code"] == "AI_NOT_CONFIGURED"


def test_advisory_input_validation(client):
    assert client.post("/api/advisory", json=advisory_body("  ")).json()["error"]["code"] == "QUESTION_REQUIRED"
    assert client.post("/api/advisory", json=advisory_body("x" * 1001)).json()["error"]["code"] == "QUESTION_TOO_LONG"
    b = advisory_body("irrigate?"); b["context"]["location"] = {}
    assert client.post("/api/advisory", json=b).json()["error"]["code"] == "LOCATION_REQUIRED"


def test_invalid_ai_response_is_not_returned_as_trusted_advice(client, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "dummy")
    calls = []
    monkeypatch.setattr(ai_service, "_call_model", lambda ctx, correction=None: calls.append(1) or "NOT JSON <script>")
    r = client.post("/api/advisory", json=advisory_body("Should I irrigate?"))
    assert r.status_code == 502 and r.json()["error"]["code"] == "AI_RESPONSE_INVALID"
    assert "NOT JSON" not in r.text and len(calls) == 2  # one retry only


def test_valid_ai_response_is_accepted_with_server_set_mode(client, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "dummy")
    good = '{"summary":"ok","actions":[{"action":"a","reason":"r","urgency":"low"}],"data_used":[],"cautions":["c"],"sources":[]}'
    monkeypatch.setattr(ai_service, "_call_model", lambda ctx, correction=None: good)
    j = client.post("/api/advisory", json=advisory_body("Should I irrigate?")).json()
    assert j["mode"] == "ai" and j["language"] == "en"


def test_client_build_succeeds():
    fe = Path(__file__).resolve().parents[2] / "client"
    if not shutil.which("npm") or not (fe / "node_modules").exists():
        pytest.skip("run `npm install` in client/ first")
    r = subprocess.run(["npm", "run", "build"], cwd=fe, capture_output=True, text=True, timeout=240)
    assert r.returncode == 0, r.stdout[-800:] + r.stderr[-800:]
