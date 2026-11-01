#!/usr/bin/env python3
"""
Post-deployment smoke test (standard library only).

  python scripts/smoke_test.py --server https://YOUR-API.onrender.com --client https://YOUR-APP.vercel.app

Reports PASS / FAIL / NOTE per check. Nothing here sends secrets. The first request may take ~1 minute on a sleeping
free-tier server, so each request is retried a few times.
"""
import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

results = []


def req(url, method="GET", headers=None, data=None, tries=4, timeout=60):
    last = None
    for i in range(tries):
        try:
            r = urllib.request.Request(url, method=method, headers=headers or {}, data=data)
            with urllib.request.urlopen(r, timeout=timeout) as resp:
                return resp.status, dict(resp.headers), resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            return e.code, dict(e.headers), e.read().decode("utf-8", "replace")
        except Exception as e:
            last = e
            time.sleep(3 * (i + 1))
    return None, {}, f"unreachable: {type(last).__name__}"


def check(name, ok, detail=""):
    results.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" - {detail}" if detail else ""))


def note(msg):
    print(f"[NOTE] {msg}")


def jget(url):
    s, h, b = req(url)
    try:
        return s, json.loads(b)
    except ValueError:
        return s, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--server", required=True)
    ap.add_argument("--client", required=True)
    a = ap.parse_args()
    be, fe = a.server.rstrip("/"), a.client.rstrip("/")

    s, j = jget(f"{be}/api/health?deep=true")
    check("server /api/health returns status ok", s == 200 and j and j.get("status") == "ok", f"HTTP {s}")
    if j:
        sv = j["services"]
        note(f"weather reachable from server: {sv['weather'].get('reachable')}; mandi configured: {sv['mandi']['configured']}; "
             f"AI configured: {sv['ai']['configured']}, mode: {sv['ai']['mode']}, deep check: {sv['ai'].get('check')}")
        check("health response contains no key-like strings", not re.search(r"AIza[0-9A-Za-z_\-]{20,}|[0-9a-f]{40,}", json.dumps(j)))

    s, j = jget(f"{be}/api/crops")
    check("GET /api/crops returns crops", s == 200 and j and len(j.get("crops", [])) > 0)
    s, j = jget(f"{be}/api/demo")
    check("GET /api/demo is labelled sample data", s == 200 and j and j.get("is_demo") is True)

    s, h, _ = req(f"{be}/api/health", method="OPTIONS", headers={"Origin": fe, "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type"})
    allow = {k.lower(): v for k, v in h.items()}.get("access-control-allow-origin")
    check("CORS allows the client origin", allow == fe, f"allow-origin={allow!r} (set client_ORIGIN={fe} on the server)" if allow != fe else "")

    s, j = jget(f"{be}/api/weather?latitude=14.68&longitude=77.6")
    check("weather endpoint answers", s == 200 and j is not None, f"status={j and j.get('status')}")
    if j and j.get("status") == "unavailable":
        note(f"live weather unavailable: {j['warnings'][0].get('reason')}")

    q = urllib.parse.urlencode({"crop": "groundnut", "state": "Andhra Pradesh", "district": "Anantapur"})
    s, j = jget(f"{be}/api/mandi/prices?{q}")
    check("mandi endpoint answers honestly", s == 200 and j is not None and not (j.get("status") == "sample"), f"status={j and j.get('status')}")
    if j:
        note(f"mandi status: {j.get('status')} ({len(j.get('records', []))} records); " + (j['warnings'][0]['message'] if j.get("warnings") else ""))

    body = json.dumps({"question": "Should I irrigate my field today?", "context": {"language": "en",
        "location": {"state": "Andhra Pradesh", "district": "Anantapur"}, "crop": {"crop_id": "groundnut", "growth_stage": "flowering"}}}).encode()
    s, h, b = req(f"{be}/api/advisory", method="POST", headers={"Content-Type": "application/json"}, data=body, timeout=120)
    try:
        j = json.loads(b)
    except ValueError:
        j = {}
    if s == 200:
        check("advisory works", True, f"mode={j.get('mode')}")
    else:
        check("advisory returns a controlled error", s in (502, 503) and "error" in j, f"HTTP {s} code={j.get('error', {}).get('code')}")

    s, h, html = req(fe)
    check("client loads", s == 200 and '<div id="root">' in html, f"HTTP {s}")
    s2, _, html2 = req(f"{fe}/mandi")
    check("client deep link /mandi works (SPA rewrite)", s2 == 200 and '<div id="root">' in html2, f"HTTP {s2}")
    m = re.search(r'src="(/assets/[^"]+\.js)"', html or "")
    if m:
        _, _, js = req(fe + m.group(1))
        host = urllib.parse.urlparse(be).netloc
        check("client bundle points at the server URL", host in js, "VITE_API_BASE_URL not baked in: set it in Vercel and redeploy" if host not in js else "")
    else:
        check("client JS bundle found", False)

    print(f"\n{sum(results)}/{len(results)} checks passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
