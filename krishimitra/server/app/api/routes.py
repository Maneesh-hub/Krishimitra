import logging
import math
import uuid

import httpx
from fastapi import APIRouter, Query

from ..config import MAX_QUESTION_LENGTH, SUPPORTED_LANGUAGES, GROWTH_STAGES, get_settings
from ..data import demo_data
from ..errors import ApiError
from ..models.schemas import AdvisoryContext, AdvisoryRequest, SoilInput
from ..services import ai_service, crop_service, mandi_service, soil_service, weather_service

router = APIRouter(prefix="/api")
log = logging.getLogger("krishimitra.api")


def parse_coords(lat, lon) -> tuple[float, float]:
    if lat in (None, "") or lon in (None, ""):
        raise ApiError(400, "LOCATION_REQUIRED", "Select your location or enter coordinates to view local information.")
    try:
        la, lo = float(lat), float(lon)
    except (TypeError, ValueError):
        raise ApiError(422, "INVALID_COORDINATES", "Enter valid latitude (-90 to 90) and longitude (-180 to 180).")
    if not (math.isfinite(la) and math.isfinite(lo) and -90 <= la <= 90 and -180 <= lo <= 180):
        raise ApiError(422, "INVALID_COORDINATES", "Enter valid latitude (-90 to 90) and longitude (-180 to 180).")
    return la, lo


@router.get("/health")
def health(deep: bool = False):
    s = get_settings()
    weather = {"configured": True, "key_required": False}
    if deep:
        try:
            weather_service._http_get(weather_service.OPEN_METEO_URL, {"latitude": 0, "longitude": 0, "current": "temperature_2m"}, timeout=3)
            weather["reachable"] = True
        except Exception:
            weather["reachable"] = False
    ai = ai_service.health_status(deep=deep)
    return {"status": "ok", "app_env": s.app_env,
            "services": {"weather": weather,
                         "mandi": {"configured": bool(s.mandi_api_base_url), "demo_fallback": True},
                         "ai": ai.model_dump()}}


@router.get("/crops")
def crops():
    return {"crops": crop_service.list_crops()}


@router.get("/weather")
def weather(latitude: str | None = None, longitude: str | None = None, demo: bool = False, location_id: str = "demo_1"):
    if demo:
        return weather_service.get_weather(None, None, demo=True, location_id=location_id)
    la, lo = parse_coords(latitude, longitude)
    return weather_service.get_weather(la, lo)


@router.get("/mandi/prices")
def mandi_prices(crop: str | None = None, state: str | None = None, district: str | None = None,
                 date_from: str | None = Query(None, alias="from"), date_to: str | None = Query(None, alias="to"),
                 demo: bool = False):
    return mandi_service.get_prices(crop, state, district, date_from, date_to, demo)


@router.post("/soil/analyze")
def soil_analyze(soil: SoilInput):
    return soil_service.analyze(soil)


@router.post("/advisory")
def advisory(req: AdvisoryRequest):
    q, c = (req.question or "").strip(), req.context
    if not q:
        raise ApiError(422, "QUESTION_REQUIRED", "Enter your farming question before submitting.")
    if len(q) > MAX_QUESTION_LENGTH:
        raise ApiError(422, "QUESTION_TOO_LONG", "Please keep your question within 1000 characters.")
    if c.language not in SUPPORTED_LANGUAGES:
        raise ApiError(422, "UNSUPPORTED_LANGUAGE", "Unsupported language.")
    if not (c.location.state or "").strip() or not (c.location.district or "").strip():
        raise ApiError(400, "LOCATION_REQUIRED", "Select your state and district to view local information.")
    if c.location.latitude is not None or c.location.longitude is not None:
        parse_coords(c.location.latitude, c.location.longitude)
    crop = crop_service.get_crop(c.crop.crop_id)
    if c.crop.growth_stage not in GROWTH_STAGES:
        raise ApiError(422, "INVALID_GROWTH_STAGE", "Unknown growth stage.")
    if c.soil:
        soil_service.analyze(c.soil)  # validates ranges (E8)
    c.crop.crop_name = c.crop.crop_name or crop["name"]
    ctx = AdvisoryContext(**c.model_dump(), question=q)
    result = ai_service.generate_advisory(ctx)
    result.request_id = result.request_id or uuid.uuid4().hex[:12]
    # L15 audit line: no coordinates, no question text, no secrets
    log.info("advisory id=%s mode=%s crop=%s state=%s district=%s weather=%s mandi=%s status=%s",
             result.request_id, result.mode, crop["id"], c.location.state, c.location.district,
             (c.weather or {}).get("status"), (c.mandi or {}).get("status"), result.status)
    return result


@router.get("/demo")
def demo():
    crops_demo = [{**{k: v for k, v in c.items()}, "is_demo": True} for c in crop_service.list_crops()[:3]]
    return {"is_demo": True, "label": demo_data.LABEL, "locations": demo_data.SAMPLE_LOCATIONS,
            "weather": {l["id"]: weather_service.get_weather(None, None, demo=True, location_id=l["id"])
                        for l in demo_data.SAMPLE_LOCATIONS},
            "mandi": {c: mandi_service.get_prices(c, "Sample State", None, None, None, demo=True)
                      for c in ("groundnut", "paddy", "cotton")},
            "soil": demo_data.SAMPLE_SOIL, "crop_profiles": demo_data.SAMPLE_CROP_PROFILES, "crops": crops_demo}
