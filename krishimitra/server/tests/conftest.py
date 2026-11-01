import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import weather_service


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for k in ("GEMINI_API_KEY", "MANDI_API_BASE_URL", "MANDI_API_KEY", "MANDI_DEFAULT_UNIT"):
        monkeypatch.delenv(k, raising=False)
    weather_service._CACHE.clear()


@pytest.fixture
def client():
    return TestClient(app)


def advisory_body(question, **over):
    body = {"question": question, "context": {
        "language": "en",
        "location": {"state": "Sample State", "district": "Sample District A"},
        "crop": {"crop_id": "groundnut", "crop_name": "Groundnut", "growth_stage": "flowering"}}}
    body["context"].update(over)
    return body
