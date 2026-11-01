# KrishiMitra AI

Multilingual (en, te, hi, kn, ta, ml, mr, bn, gu) farmer information app: weather + alerts, mandi prices + comparison,
soil input checks and an AI advisory assistant. React + Vite + Tailwind client, FastAPI server.
**Educational buildathon MVP — not certified agronomic advice.** Runs fully without API keys (clearly labelled sample/demo mode).

## Run locally (two terminals)
```powershell
# server → http://localhost:8000  (docs at /docs)
cd server
python -m venv .venv ; .venv\Scripts\python.exe -m pip install -r requirements-dev.txt
copy .env.example .env                        # optional; edit to add keys
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000

# client → http://localhost:5173  (dev server proxies /api to :8000)
cd client
npm install
npm run dev
```
Click **Load sample data** to see every screen with labelled fictional data.

## Tests / build
```powershell
cd server ; .venv\Scripts\python.exe -m pytest -q     # 42 tests (the client build test needs `npm install` first)
cd client ; npm run build
python scripts\check_secrets.py                        # scan for leaked secrets before committing
```

## Configuration
See `server/.env.example` (server secrets) and `client/.env.example` (public server URL only). Production setup: **DEPLOY.md**.

## Data behaviour (important)
- Weather: Open-Meteo. On failure → "unavailable" with the reason; sample data only on explicit request.
- Mandi prices: CEDA Agmarknet API using a server-side Bearer token (`CEDA_API_TOKEN`); optional legacy data.gov.in adapter remains supported. Not configured / failing → "unavailable"; sample data is a separate, labelled view. Units are never assumed.
- AI: Gemini when `GEMINI_API_KEY` + `GEMINI_MODEL` are set (transient errors retried ≤2×; real errors shown, never replaced by demo advice); otherwise labelled demo mode.
- Outbound calls have timeouts and bounded retries (`server/app/http_client.py`). Logs never contain URLs, keys or questions.

## Known limitations
- CEDA integration uses the documented `/v1/agmarknet` Bearer-authenticated endpoints. Live access still requires a valid private `CEDA_API_TOKEN`; verify with your CEDA account before demo day.
- District coordinates cover 15 districts (approximate); use "Other" for any other place.
- Demo-mode advisories are English only. Soil bands are indicative only.
- Not implemented: map picker, saved profiles, voice input.
