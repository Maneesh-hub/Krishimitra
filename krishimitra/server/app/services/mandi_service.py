"""Government-data (AGMARKNET / data.gov.in) adapter, normalisation, comparison (L5, L6)."""
import logging
import httpx
from datetime import date, datetime, timezone

from ..config import get_settings
from ..data import demo_data
from ..errors import ApiError
from ..http_client import fetch_json, friendly
from . import crop_service

log = logging.getLogger("krishimitra.mandi")
COMPARISON_NOTE = "Price comparison only — not a guaranteed sale price."
SOURCE = "data.gov.in AGMARKNET"
CEDA_SOURCE = "CEDA Agri Market Data (CEDA-AMD)"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _http_get(url: str, params: dict, timeout: float = 10.0, headers: dict | None = None) -> dict:
    # 2 attempts max, ~20 s total budget; 4xx (bad key / URL) is never retried and is reported accurately
    return fetch_json(url, params, headers, provider="Mandi data service", attempts=2, read=timeout, deadline=20.0)


def parse_date(s) -> date | None:
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(str(s).strip(), fmt).date()
        except (ValueError, TypeError):
            continue
    return None


def _num(v):
    try:
        f = float(str(v).replace(",", "").strip())
        return f if f == f and f >= 0 else None
    except (ValueError, TypeError):
        return None


def normalize_record(raw: dict, fetched_at: str, default_unit: str, stale_days: int) -> dict | None:
    """Return a normalised record or None if malformed. Source values/units are preserved."""
    d = parse_date(raw.get("arrival_date") or raw.get("price_date"))
    commodity = (raw.get("commodity") or "").strip()
    prices = [_num(raw.get(k)) for k in ("min_price", "modal_price", "max_price")]
    if not d or not commodity or all(p is None for p in prices):
        return None
    unit = (raw.get("unit") or default_unit or "").strip() or None   # never assumed
    age = (date.today() - d).days
    return {"market": raw.get("market") or None, "district": raw.get("district") or None,
            "state": raw.get("state") or None, "commodity": commodity, "variety": raw.get("variety") or None,
            "price_date": d.isoformat(), "min_price": prices[0], "modal_price": prices[1],
            "max_price": prices[2], "unit": unit, "source": SOURCE, "fetched_at": fetched_at,
            "is_demo": False, "age_days": age, "is_stale": age > stale_days}


def dedupe(records: list[dict]) -> list[dict]:
    seen, out = set(), []
    for r in records:
        k = tuple(r.get(f) for f in ("market", "district", "state", "commodity", "variety",
                                     "price_date", "min_price", "modal_price", "max_price", "unit"))
        if k not in seen:
            seen.add(k)
            out.append(r)
    return out


def compare(records: list[dict]) -> dict:
    """Group only records with same commodity + unit + date; rank by modal price (L6)."""
    groups: dict = {}
    excluded = 0
    for r in records:
        if r.get("unit") is None or r.get("modal_price") is None:
            excluded += 1
            continue
        groups.setdefault((r["commodity"].lower(), r["unit"], r["price_date"]), []).append(r)
    out = []
    for (commodity, unit, d), rows in sorted(groups.items(), key=lambda kv: kv[0][2], reverse=True):
        if len(rows) >= 2:
            out.append({"commodity": rows[0]["commodity"], "unit": unit, "price_date": d,
                        "records": sorted(rows, key=lambda x: x["modal_price"], reverse=True)})
    return {"note": COMPARISON_NOTE, "groups": out, "excluded_count": excluded}


def _resp(status, records, filters, source, warnings=None, is_demo=False, skipped=0):
    return {"status": status, "records": records, "filters": filters, "source": source, "is_demo": is_demo,
            "fetched_at": _now(), "warnings": warnings or [], "skipped_count": skipped,
            "comparison": compare(records) if records else {"note": COMPARISON_NOTE, "groups": [], "excluded_count": 0}}



def _ceda_request(path: str, token: str, base_url: str, method: str = "GET", body: dict | None = None) -> dict:
    """Small bounded CEDA request helper. Never log credentials or request URLs."""
    try:
        with httpx.Client(timeout=httpx.Timeout(15.0, connect=4.0), follow_redirects=False) as client:
            headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
            if method == "POST":
                response = client.post(f"{base_url}{path}", json=body or {}, headers=headers)
            else:
                response = client.get(f"{base_url}{path}", headers=headers)
        if response.status_code >= 400:
            kind = "auth" if response.status_code in (401, 403) else ("rate_limited" if response.status_code == 429 else "http_error")
            from ..http_client import UpstreamError
            raise UpstreamError(kind, "CEDA Agmarknet", response.status_code)
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError("CEDA response was not a JSON object")
        return data
    except httpx.TimeoutException:
        from ..http_client import UpstreamError
        raise UpstreamError("timeout", "CEDA Agmarknet") from None
    except httpx.TransportError:
        from ..http_client import UpstreamError
        raise UpstreamError("network", "CEDA Agmarknet") from None


def _name(value) -> str:
    return "".join(ch for ch in str(value or "").casefold() if ch.isalnum())


def _ceda_rows(response: dict):
    """Unwrap CEDA's {output: {type, message, data}} response envelope."""
    output = response.get("output", response)
    if isinstance(output, dict):
        return output.get("data", output.get("commodities", output.get("geographies", [])))
    return output if isinstance(output, list) else []


def _ceda_prices(crop: dict, state: str, district: str | None, d_from: date | None,
                 d_to: date | None, settings) -> dict:
    """Use the documented CEDA v1 endpoints and translate their numeric IDs into app records."""
    from datetime import timedelta
    base_url, token = settings.ceda_api_base_url, settings.ceda_api_token
    try:
        commodities = _ceda_rows(_ceda_request("/agmarknet/commodities", token, base_url))
        geographies = _ceda_rows(_ceda_request("/agmarknet/geographies", token, base_url))
        if not isinstance(commodities, list) or not isinstance(geographies, list):
            raise ValueError("Unexpected CEDA lookup response")
        target_names = {_name(crop.get("agmarknet_commodity")), _name(crop.get("name"))}
        target_names.discard("")
        commodity = next((x for x in commodities if isinstance(x, dict) and
                          (_name(x.get("commodity_name", x.get("name"))) in target_names or
                           any(n and (n in _name(x.get("commodity_name", x.get("name"))) or
                                      _name(x.get("commodity_name", x.get("name"))) in n)
                               for n in target_names))), None)
        if not commodity:
            return _resp("unavailable", [], {"crop": crop["id"], "state": state, "district": district},
                         CEDA_SOURCE, [{"code": "CEDA_COMMODITY_NOT_FOUND", "message": "This crop is not available in CEDA's commodity list."}])
        state_obj = next((x for x in geographies if isinstance(x, dict) and
                          _name(x.get("state_name", x.get("name"))) == _name(state)), None)
        if not state_obj:
            return _resp("unavailable", [], {"crop": crop["id"], "state": state, "district": district},
                         CEDA_SOURCE, [{"code": "CEDA_STATE_NOT_FOUND", "message": "This state was not found in CEDA's geography list."}])
        state_id = state_obj.get("state_id", state_obj.get("census_state_id"))
        districts = state_obj.get("districts") if isinstance(state_obj.get("districts"), list) else []
        district_obj = next((x for x in districts if isinstance(x, dict) and
                             _name(x.get("district_name", x.get("name"))) == _name(district)), None) if district else None
        if district and not district_obj:
            return _resp("unavailable", [], {"crop": crop["id"], "state": state, "district": district},
                         CEDA_SOURCE, [{"code": "CEDA_DISTRICT_NOT_FOUND", "message": "This district was not found under the selected state in CEDA's geography list."}])
        district_ids = [district_obj.get("district_id")] if district_obj else []
        market_ids, market_names = [], {}
        if district_obj:
            markets_data = _ceda_request("/agmarknet/markets", token, base_url, "POST", {
                "commodity_id": commodity.get("commodity_id", commodity.get("id")), "state_id": state_id,
                "district_id": district_obj.get("district_id"), "indicator": "price"
            })
            markets = _ceda_rows(markets_data)
            if isinstance(markets, list):
                market_ids = [m.get("market_id") for m in markets if isinstance(m, dict) and m.get("market_id") is not None]
                market_names = {str(m.get("market_id")): m.get("market_name") for m in markets if isinstance(m, dict)}
        end = d_to or date.today()
        start = d_from or (end - timedelta(days=30))
        if start > end:
            raise ValueError("Invalid CEDA date range")
        payload = {"commodity_id": commodity.get("commodity_id", commodity.get("id")), "state_id": state_id,
                   "district_id": district_ids, "market_id": market_ids,
                   "from_date": start.isoformat(), "to_date": end.isoformat()}
        data = _ceda_request("/agmarknet/prices", token, base_url, "POST", payload)
        rows = _ceda_rows(data)
        if not isinstance(rows, list):
            raise ValueError("Unexpected CEDA prices response")
        fetched = _now()
        out = []
        for raw in rows:
            if not isinstance(raw, dict):
                continue
            d = parse_date(raw.get("date"))
            if not d:
                continue
            min_p, modal_p, max_p = (_num(raw.get(k)) for k in ("min_price", "modal_price", "max_price"))
            if all(v is None for v in (min_p, modal_p, max_p)):
                continue
            market_id = raw.get("market_id")
            out.append({"market": market_names.get(str(market_id)) if market_id is not None else None,
                        "district": district_obj.get("district_name") if district_obj else next(
                            (x.get("district_name") for x in districts if isinstance(x, dict) and x.get("district_id") == raw.get("census_district_id")), None),
                        "state": state_obj.get("state_name"), "commodity": commodity.get("commodity_name", commodity.get("name")) or crop["name"],
                        "variety": None, "price_date": d.isoformat(), "min_price": min_p,
                        "modal_price": modal_p, "max_price": max_p, "unit": None,
                        "source": CEDA_SOURCE, "fetched_at": fetched, "is_demo": False,
                        "age_days": (date.today() - d).days, "is_stale": (date.today() - d).days > settings.mandi_stale_days})
        out = dedupe(out)
        out.sort(key=lambda r: r["price_date"], reverse=True)
        warning = [{"code": "UNIT_NOT_PROVIDED", "message": "CEDA's documented response does not specify a price unit; comparisons requiring units are disabled."}] if out else []
        return _resp("live" if out else "empty", out, {"crop": crop["id"], "commodity": commodity.get("commodity_name", commodity.get("name")),
                     "state": state, "district": district, "from": start.isoformat(), "to": end.isoformat()},
                     CEDA_SOURCE, warning)
    except Exception as e:
        kind = getattr(e, "kind", "bad_response")
        log.warning("CEDA mandi provider failure kind=%s", kind)
        return _resp("unavailable", [], {"crop": crop["id"], "state": state, "district": district},
                     CEDA_SOURCE, [{"code": "MANDI_UNAVAILABLE", "reason": kind,
                                    "message": "CEDA live prices are unavailable. Check the CEDA token, endpoint response, and selected crop/location."}])


def get_prices(crop_id, state, district, date_from, date_to, demo=False) -> dict:
    crop = crop_service.get_crop(crop_id)
    d_from, d_to = (parse_date(date_from) if date_from else None), (parse_date(date_to) if date_to else None)
    if (date_from and not d_from) or (date_to and not d_to):
        raise ApiError(422, "INVALID_DATE", "Dates must use the format YYYY-MM-DD.")
    if d_from and d_to and d_from > d_to:
        raise ApiError(422, "INVALID_DATE", "The 'from' date must not be after the 'to' date.")
    filters = {"crop": crop_id, "commodity": crop["agmarknet_commodity"], "state": state,
               "district": district, "from": date_from, "to": date_to}

    def in_range(r):
        d = parse_date(r["price_date"])
        return (not d_from or d >= d_from) and (not d_to or d <= d_to)

    if demo:
        recs = [r for r in demo_data.sample_mandi(crop_id) if in_range(r)]
        w = [{"code": "SAMPLE_DATA", "message": demo_data.LABEL}]
        return _resp("sample" if recs else "empty", recs, filters, "demo", w, is_demo=True)

    s = get_settings()
    if not state:
        raise ApiError(400, "LOCATION_REQUIRED", "Select your state to view local mandi prices.")
    unavailable = lambda msg, reason="unavailable": _resp("unavailable", [], filters, SOURCE,
                                                         [{"code": "MANDI_UNAVAILABLE", "reason": reason, "message": msg}])
    # Prefer CEDA when its token is configured; keep the existing data.gov.in adapter as a fallback.
    if s.ceda_api_token:
        return _ceda_prices(crop, state, district, d_from, d_to, s)
    if not s.mandi_api_base_url:
        return unavailable("Live mandi prices are unavailable: configure CEDA_API_TOKEN or MANDI_API_BASE_URL. You can view sample data.", "not_configured")
    params = {"format": "json", "limit": 500, "filters[commodity]": crop["agmarknet_commodity"],
              "filters[state]": state}
    if district:
        params["filters[district]"] = district
    if s.mandi_api_key:
        params["api-key"] = s.mandi_api_key
    try:
        data = _http_get(s.mandi_api_base_url, params)
        raw_records = data.get("records")
        if not isinstance(raw_records, list):
            raise ValueError("unexpected response shape")
    except Exception as e:
        kind = getattr(e, "kind", "network" if e.__class__.__module__.startswith("httpx") else "bad_response")
        log.warning("mandi provider failure kind=%s", kind)
        return unavailable("Live mandi prices are unavailable. " + friendly(kind, "The mandi data service") + " You can retry or view sample data.", kind)
    fetched = _now()
    good = [normalize_record(r, fetched, s.mandi_default_unit, s.mandi_stale_days) for r in raw_records]
    skipped = sum(1 for g in good if g is None)
    recs = [r for r in dedupe([g for g in good if g]) if in_range(r)]
    recs.sort(key=lambda r: r["price_date"], reverse=True)
    warnings = [{"code": "RECORDS_SKIPPED", "message": f"{skipped} malformed record(s) skipped."}] if skipped else []
    return _resp("live" if recs else "empty", recs, filters, SOURCE, warnings, skipped=skipped)
