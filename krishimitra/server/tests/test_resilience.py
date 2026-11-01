import logging

import httpx
import pytest
from google.genai import errors as gerrors

from app import config
from app.http_client import UpstreamError, fetch_json
from app.services import ai_service, mandi_service, weather_service
from tests.conftest import advisory_body

URL = "https://example.test/data"


def transport(*responses):
    """MockTransport answering with each item in turn (Response or Exception); records call count."""
    calls = []

    def handler(request):
        i = min(len(calls), len(responses) - 1)
        calls.append(request)
        item = responses[i]
        if isinstance(item, Exception):
            raise item
        return item
    t = httpx.MockTransport(handler)
    t.calls = calls
    return t


def get(t, **kw):
    return fetch_json(URL, {"api-key": "SECRET123"}, provider="Test", transport=t, sleep=lambda s: None, **kw)


# ---------------- http_client ----------------
def test_transient_5xx_is_retried_then_succeeds():
    t = transport(httpx.Response(503), httpx.Response(200, json={"ok": 1}))
    assert get(t) == {"ok": 1} and len(t.calls) == 2


def test_retries_are_bounded():
    t = transport(httpx.Response(503))
    with pytest.raises(UpstreamError) as e:
        get(t, attempts=3)
    assert e.value.kind == "server_error" and len(t.calls) == 3


def test_auth_error_is_not_retried_and_is_classified():
    t = transport(httpx.Response(401))
    with pytest.raises(UpstreamError) as e:
        get(t)
    assert e.value.kind == "auth" and len(t.calls) == 1


def test_timeout_is_retried_then_reported():
    t = transport(httpx.ReadTimeout("slow"))
    with pytest.raises(UpstreamError) as e:
        get(t)
    assert e.value.kind == "timeout" and len(t.calls) == 2


def test_long_retry_after_is_not_waited_for():
    t = transport(httpx.Response(429, headers={"retry-after": "120"}))
    with pytest.raises(UpstreamError) as e:
        get(t)
    assert e.value.kind == "rate_limited" and len(t.calls) == 1


def test_non_json_body_is_reported_as_bad_response():
    t = transport(httpx.Response(200, text="<html>blocked</html>"))
    with pytest.raises(UpstreamError) as e:
        get(t)
    assert e.value.kind == "bad_response"


def test_api_key_never_appears_in_logs(caplog):
    caplog.set_level(logging.INFO)
    get(transport(httpx.Response(503), httpx.Response(200, json={})))
    assert "SECRET123" not in caplog.text


# ---------------- user-facing provider messages ----------------
def test_weather_failure_reports_accurate_reason(client, monkeypatch):
    def boom(*a, **k):
        raise UpstreamError("rate_limited", "Open-Meteo", 429)
    monkeypatch.setattr(weather_service, "_http_get", boom)
    w = client.get("/api/weather", params={"latitude": 14.7, "longitude": 77.6}).json()
    assert w["status"] == "unavailable" and w["warnings"][0]["reason"] == "rate_limited"
    assert "too many requests" in w["warnings"][0]["message"]


def test_mandi_bad_key_is_reported_as_credentials_problem(client, monkeypatch):
    monkeypatch.setenv("MANDI_API_BASE_URL", "https://example.test/r")
    def boom(*a, **k):
        raise UpstreamError("auth", "Mandi data service", 403)
    monkeypatch.setattr(mandi_service, "_http_get", boom)
    m = client.get("/api/mandi/prices", params={"crop": "groundnut", "state": "X"}).json()
    assert m["status"] == "unavailable" and m["warnings"][0]["reason"] == "auth"
    assert "API key" in m["warnings"][0]["message"] and m["records"] == []


# ---------------- Gemini ----------------
@pytest.fixture
def ai_on(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-key")
    monkeypatch.setenv("GEMINI_MODEL", "test-model")
    monkeypatch.setattr(ai_service, "_sleep", lambda s: None)
    monkeypatch.setattr(ai_service, "_client_ready", lambda: True)


GOOD = '{"summary":"ok","actions":[{"action":"a","reason":"r","urgency":"low"}],"data_used":[],"cautions":["c"],"sources":[{"name":"INVENTED","status":"live"}]}'


def seq(*items):
    calls = []

    def fn(ctx, correction, timeout_s):
        calls.append(1)
        item = items[min(len(calls) - 1, len(items) - 1)]
        if isinstance(item, Exception):
            raise item
        return item
    fn.calls = calls
    return fn


def ask(client, q="Should I irrigate?"):
    return client.post("/api/advisory", json=advisory_body(q))


def test_gemini_transient_503_is_retried(client, ai_on, monkeypatch):
    f = seq(gerrors.ServerError(503, {"error": {"message": "overloaded", "status": "UNAVAILABLE"}}), GOOD)
    monkeypatch.setattr(ai_service, "_gemini_once", f)
    r = ask(client)
    assert r.status_code == 200 and r.json()["mode"] == "ai" and len(f.calls) == 2


def test_gemini_persistent_503_gives_clear_error_after_bounded_retries(client, ai_on, monkeypatch):
    f = seq(gerrors.ServerError(503, {"error": {"message": "x", "status": "UNAVAILABLE"}}))
    monkeypatch.setattr(ai_service, "_gemini_once", f)
    r = ask(client)
    assert r.status_code == 503 and r.json()["error"]["code"] == "AI_UNAVAILABLE" and len(f.calls) == ai_service.MAX_ATTEMPTS


def test_gemini_bad_key_is_not_retried_or_hidden(client, ai_on, monkeypatch):
    f = seq(gerrors.ClientError(403, {"error": {"message": "denied", "status": "PERMISSION_DENIED"}}))
    monkeypatch.setattr(ai_service, "_gemini_once", f)
    r = ask(client)
    assert r.json()["error"]["code"] == "AI_AUTH_FAILED" and len(f.calls) == 1   # and NOT demo advice


def test_gemini_invalid_key_400_maps_to_auth_failed(client, ai_on, monkeypatch):
    monkeypatch.setattr(ai_service, "_gemini_once", seq(gerrors.ClientError(400, {"error": {"message": "API key not valid. Please pass a valid API key.", "status": "INVALID_ARGUMENT"}})))
    assert ask(client).json()["error"]["code"] == "AI_AUTH_FAILED"


def test_gemini_unknown_model_is_reported(client, ai_on, monkeypatch):
    monkeypatch.setattr(ai_service, "_gemini_once", seq(gerrors.ClientError(404, {"error": {"message": "not found", "status": "NOT_FOUND"}})))
    assert ask(client).json()["error"]["code"] == "AI_MODEL_UNAVAILABLE"


def test_gemini_quota_exhausted_is_reported_as_rate_limited(client, ai_on, monkeypatch):
    monkeypatch.setattr(ai_service, "_gemini_once", seq(gerrors.ClientError(429, {"error": {"message": "quota", "status": "RESOURCE_EXHAUSTED"}})))
    assert ask(client).json()["error"]["code"] == "AI_RATE_LIMITED"


def test_gemini_network_timeout_is_retried(client, ai_on, monkeypatch):
    f = seq(httpx.ReadTimeout("slow"), GOOD)
    monkeypatch.setattr(ai_service, "_gemini_once", f)
    assert ask(client).status_code == 200 and len(f.calls) == 2


def test_programming_errors_are_not_disguised_as_provider_outages(ai_on, monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    monkeypatch.setattr(ai_service, "_gemini_once", seq(TypeError("bug")))
    r = TestClient(app, raise_server_exceptions=False).post("/api/advisory", json=advisory_body("Should I irrigate?"))
    assert r.status_code == 500 and r.json()["error"]["code"] == "INTERNAL_ERROR"


def test_model_must_be_set_when_key_is_set(client, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-key")
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    monkeypatch.setattr(config, "get_settings", config.get_settings)
    monkeypatch.setenv("GEMINI_MODEL", "")
    assert ask(client).json()["error"]["code"] == "AI_MODEL_NOT_SET"


def test_ai_sources_come_from_context_not_from_model_output(client, ai_on, monkeypatch):
    monkeypatch.setattr(ai_service, "_gemini_once", seq(GOOD))
    j = ask(client).json()
    assert "INVENTED" not in str(j["sources"]) and j["sources"][-1]["status"] == "reference"
    assert any("not certified agronomic advice" in c for c in j["cautions"])


# ---------------- CORS ----------------
def test_client_origin_trailing_slash_and_lists_are_normalised(monkeypatch):
    monkeypatch.setenv("client_ORIGIN", "https://app.vercel.app/, http://localhost:5173")
    assert config.allowed_origins() == ["https://app.vercel.app", "http://localhost:5173"]
