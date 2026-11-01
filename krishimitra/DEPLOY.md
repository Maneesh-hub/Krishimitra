# Deploying KrishiMitra AI (GitHub → Render server → Vercel client)

You do every step below in your own accounts; nothing here can be done for you. Windows PowerShell commands.
Order matters because the two services need each other's URL: **server → client → back to server (CORS)**.

## 0. Accounts and keys you need
| Need | Required? | Where |
|---|---|---|
| GitHub, Render, Vercel accounts | yes (free tiers work) | github.com, render.com, vercel.com |
| Gemini API key | optional (without it the app shows "AI demo mode") | Google AI Studio → "Get API key" |
| Gemini model name | required if you set a key | pick a current Flash-class model from https://ai.google.dev/gemini-api/docs/models |
| Mandi data key/URL | optional (without it live prices show "unavailable" + sample data) | data.gov.in (register, create API key) |
| CEDA Bearer token | recommended for live mandi prices | CEDA API portal / API documentation |

## 1. Check for secrets, then push to GitHub
Run from the `krishimitra` folder (the one containing `server`, `client`, `scripts`).
```powershell
git init
git add .
git status                                   # read the list: there must be NO .env, .venv, node_modules, dist, *.db
python scripts\check_secrets.py --staged     # must end with "No secrets or forbidden files found."
```
Only when both look right:
```powershell
git commit -m "KrishiMitra AI"
git branch -M main
git remote add origin https://github.com/<you>/<repo>.git     # create an EMPTY repo on GitHub first (no README)
git push -u origin main
```
If `git commit` complains about identity: `git config user.name "Your Name"` and `git config user.email "you@example.com"`.
If a real key was ever committed, treat it as leaked: revoke it at the provider and create a new one; deleting the file is not enough.

## 2. server on Render
1. Render dashboard → **New + → Web Service** → connect GitHub → select the repo.
2. Settings: **Language** Python 3 · **Branch** main · **Root Directory** `server` ·
   **Build Command** `pip install -r requirements.txt` ·
   **Start Command** `uvicorn app.main:app --host 0.0.0.0 --port $PORT` · **Instance type** Free (check current free-plan limits).
3. **Advanced → Health Check Path** `/api/health`.
4. **Environment variables** (add in the dashboard; never in the repo):

| Key | Value |
|---|---|
| `PYTHON_VERSION` | `3.12.8` |
| `APP_ENV` | `production` |
| `client_ORIGIN` | `http://localhost:5173` for now (fixed in step 4) |
| `GEMINI_API_KEY` | your key (optional) |
| `GEMINI_MODEL` | model name you chose (required if key set) |
| `CEDA_API_TOKEN` | your private CEDA Bearer token (recommended for live mandi prices) |
| `CEDA_API_BASE_URL` | `https://api.ceda.ashoka.edu.in/v1` (default) |
| `MANDI_API_BASE_URL`, `MANDI_API_KEY`, `MANDI_DEFAULT_UNIT` | optional legacy data.gov.in fallback |

5. **Create Web Service**, wait for "Live", copy the URL (`https://<name>.onrender.com`).
6. Open `https://<name>.onrender.com/api/health?deep=true`. Expect `"status":"ok"`. If you set a Gemini key,
   `services.ai.check` must be `"ok"`; `model_not_found` → fix `GEMINI_MODEL`; `auth_failed` → fix the key.

(Alternative: **New + → Blueprint** uses `render.yaml` in the repo root and prompts for the `sync: false` values.)

## 3. client on Vercel
1. Vercel → **Add New… → Project** → import the same repo.
2. **Root Directory**: `client`. Framework preset: **Vite** (Build `npm run build`, Output `dist`).
3. **Environment Variables**: `VITE_API_BASE_URL` = your Render URL, **no trailing slash** (e.g. `https://krishimitra-api.onrender.com`). Tick Production (and Preview if you use previews).
4. **Deploy**, then copy the URL (`https://<project>.vercel.app`).
   `VITE_API_BASE_URL` is baked in at build time: if you change it later you must **redeploy**.
   `client/vercel.json` makes deep links like `/mandi` work after a refresh.

## 4. Allow the client in the server (CORS)
Render → your service → **Environment** → set `client_ORIGIN` to the Vercel URL exactly as the browser shows it:
scheme + host, **no path, no trailing slash** (`https://<project>.vercel.app`). Save; Render redeploys.
Several origins (e.g. a custom domain too): comma-separated. Vercel *preview* URLs differ per deployment and need adding too.

## 5. Verify the deployment
```powershell
python scripts\smoke_test.py --server https://<name>.onrender.com --client https://<project>.vercel.app
```
It checks health, CORS for your exact client origin, every API route, that the client bundle points at your server,
and that `/mandi` survives a refresh. Then open the site, click **Load sample data**, and use each page.
Paste the output to me if anything fails.

## Things that will bite you on demo day
- **Free Render instances sleep when idle**; the first request can take about a minute. Open the site 2–3 minutes before presenting.
- **Live mandi prices may not work from Render**: other developers report data.gov.in not answering from cloud hosts. Test
  `https://<name>.onrender.com/api/mandi/prices?crop=groundnut&state=Andhra%20Pradesh` early. The app then shows an honest
  "unavailable" message and offers clearly-labelled sample data; it never shows made-up prices as live.
- **Weather** needs outbound internet from Render to Open-Meteo (normally fine).

## Troubleshooting
| Symptom | Fix |
|---|---|
| Browser console: CORS error | `client_ORIGIN` ≠ the exact client origin (typo, `http` vs `https`, trailing slash, preview URL) |
| App says "server not reachable" | `VITE_API_BASE_URL` missing/wrong at build time → set it and redeploy Vercel; or server asleep → wait and retry |
| `/mandi` 404 after refresh | `client/vercel.json` missing from the deployed commit |
| `AI_MODEL_UNAVAILABLE` / `AI_AUTH_FAILED` | wrong `GEMINI_MODEL` / key (see `/api/health?deep=true`) |
| `AI_RATE_LIMITED` | Gemini quota/rate limit; wait or use another key/model |
| Render build fails on Python version | confirm `PYTHON_VERSION` is a full version such as `3.12.8` |

## What to do with the `.env.example` files
They are **templates that stay in Git with empty/placeholder values**. They are never filled in or deployed.
- **Local development**: copy `server/.env.example` → `server/.env`, and (optionally) `client/.env.example` → `client/.env.local`; fill them in. Both are git-ignored.
- **Production**: do NOT upload `.env` files. Type the same variable names into the Render and Vercel dashboards (steps 2–4).
- Keep the `.env.example` files updated whenever you add a variable, and never put a real value in them.
- client variables are public (they end up in the browser bundle): only `VITE_API_BASE_URL`, never a secret.
