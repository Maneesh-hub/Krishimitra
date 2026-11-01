"""Open-Meteo adapter + transparent rule-based alerts (L3, L4)."""
import logging
import time
from datetime import datetime, timezone

from ..config import ALERT_THRESHOLDS as T
from ..data import demo_data
from ..http_client import fetch_json, friendly

log = logging.getLogger("krishimitra.weather")

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
SOURCE = "Open-Meteo"
CACHE_TTL = 600            # seconds a cached result counts as fresh
CACHE_MAX_STALE = 6 * 3600  # seconds a cached result may be served if the provider is down
_CACHE: dict = {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _http_get(url: str, params: dict, timeout: float = 8.0, headers: dict | None = None) -> dict:
    # 2 attempts max, ~15 s total budget; retries only timeouts/network/429/5xx (see http_client)
    return fetch_json(url, params, headers, provider=SOURCE, attempts=2, read=timeout, deadline=15.0)


def build_alerts(forecast: list[dict], source: str) -> list[dict]:
    """Informational app alerts. A rule only fires from a returned (non-null) value."""
    alerts = []
    for d in forecast or []:
        day = d.get("date")
        rain, prob = d.get("precipitation_sum_mm"), d.get("precipitation_probability_pct")
        tmax, wind, wunit = d.get("temp_max_c"), d.get("wind_speed_max"), d.get("wind_speed_unit")
        if rain is not None and rain >= T["heavy_rain_mm"]:
            alerts.append({"type": "heavy_rain", "severity": "caution", "title": "Heavy rainfall possible",
                           "value": rain, "unit": "mm", "period": day, "source": source,
                           "message": f"Forecast daily rainfall {rain} mm (app threshold {T['heavy_rain_mm']} mm)."})
        if prob is not None and prob >= T["rain_probability_pct"]:
            alerts.append({"type": "rain_chance", "severity": "info", "title": "High chance of rain",
                           "value": prob, "unit": "%", "period": day, "source": source,
                           "message": f"Forecast rain probability {prob}% (app threshold {T['rain_probability_pct']}%)."})
        if tmax is not None and tmax >= T["high_temp_c"]:
            alerts.append({"type": "heat", "severity": "caution", "title": "High temperature",
                           "value": tmax, "unit": "°C", "period": day, "source": source,
                           "message": f"Forecast maximum {tmax} °C (app threshold {T['high_temp_c']} °C)."})
        if wind is not None and wunit == "km/h" and wind >= T["strong_wind_kmh"]:
            alerts.append({"type": "wind", "severity": "caution", "title": "Strong wind",
                           "value": wind, "unit": "km/h", "period": day, "source": source,
                           "message": f"Forecast maximum wind {wind} km/h (app threshold {T['strong_wind_kmh']} km/h)."})
    return alerts


def _normalize(data: dict) -> dict:
    cur, cu = data.get("current") or {}, data.get("current_units") or {}
    daily = data.get("daily") or {}

    def pick(key, i):
        arr = daily.get(key) or []
        return arr[i] if i < len(arr) else None

    forecast = [{
        "date": t, "temp_max_c": pick("temperature_2m_max", i), "temp_min_c": pick("temperature_2m_min", i),
        "precipitation_sum_mm": pick("precipitation_sum", i),
        "precipitation_probability_pct": pick("precipitation_probability_max", i),
        "wind_speed_max": pick("wind_speed_10m_max", i),
        "wind_speed_unit": (data.get("daily_units") or {}).get("wind_speed_10m_max"),
    } for i, t in enumerate(daily.get("time") or [])]
    current = {"time": cur.get("time"), "temperature_c": cur.get("temperature_2m"),
               "humidity_pct": cur.get("relative_humidity_2m"), "precipitation_mm": cur.get("precipitation"),
               "wind_speed": cur.get("wind_speed_10m"), "wind_speed_unit": cu.get("wind_speed_10m")}
    return {"current": current, "forecast": forecast,
            "location": {"latitude": data.get("latitude"), "longitude": data.get("longitude"),
                         "timezone": data.get("timezone")}}


def _response(status, source, raw=None, warnings=None, fetched_at=None, is_demo=False):
    raw = raw or {}
    forecast = raw.get("forecast") or []
    return {"status": status, "source": source, "is_demo": is_demo, "fetched_at": fetched_at or _now(),
            "location": raw.get("location"), "current": raw.get("current"), "forecast": forecast,
            "alerts": build_alerts(forecast, source) if forecast else [],
            "warnings": warnings or [],
            "alert_disclaimer": "App-generated informational alerts only - not official weather warnings."}


def get_weather(lat: float | None, lon: float | None, demo: bool = False, location_id: str = "demo_1") -> dict:
    if demo:
        return _response("sample", "demo", demo_data.sample_weather_raw(location_id),
                         [{"code": "SAMPLE_DATA", "message": demo_data.LABEL}], is_demo=True)
    key = (round(lat, 2), round(lon, 2))
    hit = _CACHE.get(key)
    if hit and time.time() - hit[0] < CACHE_TTL:
        return _response("cached", SOURCE, hit[1], [], hit[3])
    params = {"latitude": lat, "longitude": lon, "timezone": "auto", "forecast_days": 7,
              "current": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m",
              "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,"
                       "precipitation_probability_max,wind_speed_10m_max"}
    try:
        raw = _normalize(_http_get(OPEN_METEO_URL, params))
    except Exception as e:  # network, HTTP or parse failure -> never fall back silently to sample values
        kind = getattr(e, "kind", "network" if e.__class__.__module__.startswith("httpx") else "bad_response")
        log.warning("weather unavailable kind=%s", kind)
        if hit and time.time() - hit[0] < CACHE_MAX_STALE:
            return _response("cached", SOURCE, hit[1], [{"code": "WEATHER_STALE_CACHE", "reason": kind,
                             "message": "Live weather could not be refreshed; showing the last saved result."}], hit[3])
        return _response("unavailable", SOURCE, None, [{"code": "WEATHER_UNAVAILABLE", "reason": kind,
                         "message": friendly(kind, "The weather service") + " Retry, or view clearly labelled sample data."}])
    fetched = _now()
    _CACHE[key] = (time.time(), raw, [], fetched)
    return _response("live", SOURCE, raw, [], fetched)
