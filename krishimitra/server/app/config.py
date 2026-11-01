"""Central configuration. Secrets come only from environment variables (never hardcoded)."""
import os
from dataclasses import dataclass

SUPPORTED_LANGUAGES = ("en", "te", "hi", "kn", "ta", "ml", "mr", "bn", "gu")
GROWTH_STAGES = ("land_preparation", "sowing", "seedling", "vegetative",
                 "flowering", "fruiting", "harvesting", "unknown")
SOIL_SOURCES = ("user_entered", "lab_report", "sample")
MAX_QUESTION_LENGTH = 1000
MAX_BODY_BYTES = 200_000

# L4: alert thresholds live in ONE place. These are general app alerts, NOT official warnings.
ALERT_THRESHOLDS = {
    "heavy_rain_mm": 40.0,          # daily precipitation sum
    "rain_probability_pct": 80.0,   # daily max precipitation probability
    "high_temp_c": 40.0,            # daily max temperature
    "strong_wind_kmh": 40.0,        # daily max wind (only when provider unit is km/h)
}


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str
    gemini_model: str
    mandi_api_base_url: str
    mandi_api_key: str
    ceda_api_token: str
    ceda_api_base_url: str
    mandi_default_unit: str
    mandi_stale_days: int
    client_origin: str
    app_env: str
    database_url: str


def allowed_origins() -> list[str]:
    """client_ORIGIN may hold several comma-separated origins. A trailing slash is stripped because
    browsers send origins without one (a pasted 'https://app.vercel.app/' would otherwise fail CORS)."""
    return [o.strip().rstrip("/") for o in get_settings().client_origin.split(",") if o.strip()]


def get_settings() -> Settings:
    """Read env on every call so tests/operators can change values without restarts."""
    e = os.environ.get
    return Settings(
        gemini_api_key=(e("GEMINI_API_KEY") or "").strip(),
        gemini_model=(e("GEMINI_MODEL") or "").strip(),   # no default: model availability changes, operator must choose
        mandi_api_base_url=(e("MANDI_API_BASE_URL") or "").strip(),
        mandi_api_key=(e("MANDI_API_KEY") or "").strip(),
        ceda_api_token=(e("CEDA_API_TOKEN") or "").strip(),
        ceda_api_base_url=(e("CEDA_API_BASE_URL") or "https://api.ceda.ashoka.edu.in/v1").strip().rstrip("/"),
        mandi_default_unit=(e("MANDI_DEFAULT_UNIT") or "").strip(),
        mandi_stale_days=int(e("MANDI_STALE_DAYS") or 3),
        client_origin=(e("client_ORIGIN") or "http://localhost:5173").strip(),
        app_env=(e("APP_ENV") or "development").strip(),
        database_url=(e("DATABASE_URL") or "sqlite:///./krishimitra.db").strip(),
    )
