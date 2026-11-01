"""Curated crop reference data (general information only, NOT a government recommendation)."""
from ..data.crops_data import CROPS
from ..errors import ApiError


def list_crops() -> list[dict]:
    return CROPS


def get_crop(crop_id: str | None) -> dict:
    if not crop_id:
        raise ApiError(400, "CROP_REQUIRED", "Choose a crop to receive crop-specific guidance.")
    for c in CROPS:
        if c["id"] == crop_id:
            return c
    raise ApiError(422, "UNSUPPORTED_CROP", "This crop is not in the current demo crop list.")
