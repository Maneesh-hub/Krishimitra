"""
Shared outbound-HTTP helper for weather / mandi providers.

- explicit connect/read timeouts
- BOUNDED retries (timeouts, network errors, 429, 5xx only) with exponential backoff + jitter and a total deadline
- NO retry for 4xx client/auth errors: those are real configuration problems and are surfaced as-is
- errors are classified (UpstreamError.kind) so the UI can show an accurate message
- never logs URLs or query parameters (they can contain API keys)
"""
import logging
import random
import time

import httpx

log = logging.getLogger("krishimitra.http")

RETRYABLE = {"timeout", "network", "server_error", "rate_limited"}


class UpstreamError(Exception):
    def __init__(self, kind: str, provider: str, status: int | None = None, retry_after: float | None = None):
        self.kind, self.provider, self.status, self.retry_after = kind, provider, status, retry_after
        super().__init__(f"{provider}: {kind}" + (f" (HTTP {status})" if status else ""))


def classify(status: int) -> str:
    if status in (401, 403):
        return "auth"
    if status == 404:
        return "not_found"
    if status == 429:
        return "rate_limited"
    if status >= 500:
        return "server_error"
    return "http_error"


_MESSAGES = {
    "timeout": "{svc} is responding slowly.",
    "network": "Could not reach {svc}.",
    "rate_limited": "{svc} is receiving too many requests right now.",
    "server_error": "{svc} is having problems right now.",
    "auth": "{svc} rejected the server's credentials (the operator must check the API key).",
    "not_found": "{svc} endpoint was not found (the operator must check the configured URL).",
    "bad_response": "{svc} returned an unexpected response.",
    "http_error": "{svc} request failed.",
}


def friendly(kind: str, svc: str) -> str:
    return _MESSAGES.get(kind, "{svc} is unavailable.").format(svc=svc)


def _retry_after(r: httpx.Response) -> float | None:
    try:
        return float(r.headers.get("retry-after", ""))
    except ValueError:
        return None


def fetch_json(url: str, params: dict | None = None, headers: dict | None = None, *, provider: str,
               attempts: int = 2, connect: float = 3.0, read: float = 8.0, deadline: float = 20.0,
               base_delay: float = 0.5, max_delay: float = 4.0, transport: httpx.BaseTransport | None = None,
               sleep=time.sleep) -> dict:
    timeout = httpx.Timeout(connect=connect, read=read, write=5.0, pool=connect)
    started = time.monotonic()
    for attempt in range(1, attempts + 1):
        try:
            with httpx.Client(timeout=timeout, transport=transport, follow_redirects=False) as c:
                r = c.get(url, params=params, headers=headers)
        except httpx.TimeoutException:
            err = UpstreamError("timeout", provider)
        except httpx.TransportError:
            err = UpstreamError("network", provider)
        else:
            if r.status_code < 400:
                try:
                    return r.json()
                except ValueError:
                    raise UpstreamError("bad_response", provider, r.status_code)
            err = UpstreamError(classify(r.status_code), provider, r.status_code, _retry_after(r))

        delay = base_delay * 2 ** (attempt - 1)
        if err.retry_after is not None:
            if err.retry_after > max_delay:      # server asks for a long wait: don't hold the user's request
                raise err
            delay = err.retry_after
        delay = min(max_delay, delay) + random.uniform(0, 0.25)
        out_of_time = time.monotonic() - started + delay > deadline
        if err.kind not in RETRYABLE or attempt == attempts or out_of_time:
            log.warning("%s failed kind=%s status=%s attempts=%d", provider, err.kind, err.status, attempt)
            raise err
        log.warning("%s transient failure kind=%s status=%s attempt=%d/%d retry_in=%.1fs",
                    provider, err.kind, err.status, attempt, attempts, delay)
        sleep(delay)
    raise UpstreamError("network", provider)  # pragma: no cover
