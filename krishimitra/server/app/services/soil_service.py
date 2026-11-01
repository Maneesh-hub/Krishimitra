"""Deterministic soil validation and conservative interpretation (L7)."""
import math
from datetime import datetime, timezone

from ..errors import ApiError
from ..models.schemas import SoilInput

# General Indian soil-test rating bands (low/medium cut-offs). Methods and labs differ: indicative only.
KG_HA = {"kg/ha", "kgha", "kg/hectare"}
BANDS_KG_HA = {"nitrogen": (280, 560), "phosphorus": (10, 25), "potassium": (110, 280)}
OC_BANDS_PCT = (0.5, 0.75)
NUTRIENTS = ("nitrogen", "phosphorus", "potassium", "organic_carbon")


def _rate(v, lo, hi):
    return "low" if v < lo else ("medium" if v <= hi else "high")


def ph_band(ph: float) -> str:
    if ph < 5.5:
        return "strongly_acidic"
    if ph < 6.5:
        return "moderately_acidic"
    if ph <= 7.5:
        return "near_neutral"
    return "alkaline"


def analyze(soil: SoilInput) -> dict:
    if soil.soil_source not in ("user_entered", "lab_report", "sample"):
        raise ApiError(422, "INVALID_SOIL_SOURCE", "Soil source must be user_entered, lab_report or sample.")
    if soil.ph is not None and (not math.isfinite(soil.ph) or soil.ph < 0 or soil.ph > 14):
        raise ApiError(422, "INVALID_SOIL_PH", "Soil pH must be between 0 and 14.")
    for n in NUTRIENTS:
        v = getattr(soil, n)
        if v is not None and (not math.isfinite(v) or v < 0):
            raise ApiError(422, "INVALID_SOIL_VALUE", f"{n.replace('_', ' ').title()} must be a number of 0 or more.")
    items, missing = [], []
    if soil.ph is None:
        missing.append("ph")
    else:
        items.append({"parameter": "ph", "value": soil.ph, "unit": None, "status": "interpreted",
                      "band": ph_band(soil.ph),
                      "note": "pH band is a general guide; crop needs and local soil conditions vary."})
    for n in NUTRIENTS:
        v, unit = getattr(soil, n), (getattr(soil, n + "_unit") or "").strip()
        if v is None:
            missing.append(n)
            continue
        item = {"parameter": n, "value": v, "unit": unit or None, "status": "not_interpreted", "band": None}
        key = unit.lower().replace(" ", "")
        if not unit:
            item["note"] = "Add the unit (for example, kg/ha) before we interpret this reading."
        elif n in BANDS_KG_HA and key in KG_HA:
            item.update(status="interpreted", band=_rate(v, *BANDS_KG_HA[n]),
                        note="Indicative band for kg/ha readings; depends on the test method. Confirm with a soil test.")
        elif n == "organic_carbon" and key == "%":
            item.update(status="interpreted", band=_rate(v, *OC_BANDS_PCT),
                        note="Indicative band for % organic carbon. Confirm with a soil test.")
        else:
            item["note"] = "Unit recorded, but no built-in reference band for this unit; not interpreted."
        items.append(item)
    cautions = ["Readings are not laboratory-verified unless taken from a lab report; interpretation is indicative only.",
                "Do not decide fertiliser quantities from these readings. Consult a local soil-testing lab or agricultural officer."]
    if missing:
        cautions.append("Missing values: " + ", ".join(missing) + ".")
    return {"is_user_provided": soil.soil_source != "lab_report", "soil_source": soil.soil_source,
            "items": items, "missing": missing, "cautions": cautions,
            "generated_at": datetime.now(timezone.utc).isoformat()}
