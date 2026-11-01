NOTE = "General reference information only - not a live government recommendation."
STAGES = ["land_preparation", "sowing", "seedling", "vegetative", "flowering", "fruiting", "harvesting"]


def _c(i, name, te, hi, commodity, seasons, notes):
    return {"id": i, "name": name, "names": {"en": name, "te": te, "hi": hi},
            "agmarknet_commodity": commodity, "seasons": seasons, "growth_stages": STAGES,
            "notes": notes, "reference_only": True, "reference_note": NOTE}


CROPS = [
    _c("groundnut", "Groundnut", "వేరుశనగ", "मूंगफली", "Groundnut", ["Kharif", "Rabi (some regions)"],
       ["Prefers well-drained, light soils; waterlogging is harmful.", "Pod development is sensitive to prolonged water stress."]),
    _c("paddy", "Paddy (Rice)", "వరి", "धान", "Paddy(Dhan)(Common)", ["Kharif", "Rabi (irrigated)"],
       ["Needs reliable water supply; water management differs by method and variety."]),
    _c("cotton", "Cotton", "పత్తి", "कपास", "Cotton", ["Kharif"],
       ["Deep, well-drained soils suit cotton; monitor fields regularly for pests."]),
    _c("maize", "Maize", "మొక్కజొన్న", "मक्का", "Maize", ["Kharif", "Rabi"],
       ["Sensitive to waterlogging; flowering stage is sensitive to heat and moisture stress."]),
    _c("tomato", "Tomato", "టమాటా", "टमाटर", "Tomato", ["Varies by region"],
       ["Prices swing widely; avoid waterlogging and check local planting windows."]),
    _c("chilli", "Chilli", "మిరప", "मिर्च", "Dry Chillies", ["Kharif"],
       ["Well-drained soil preferred; avoid water stress at flowering and fruit set."]),
    _c("wheat", "Wheat", "గోధుమ", "गेहूं", "Wheat", ["Rabi"],
       ["Cool-season crop; sowing time strongly affects yield, follow local guidance."]),
    _c("redgram", "Red gram (Tur)", "కందులు", "अरहर (तूर)", "Arhar (Tur/Red Gram)(Whole)", ["Kharif"],
       ["Drought-tolerant once established; avoid standing water."]),
]
