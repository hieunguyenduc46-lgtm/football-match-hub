# Connecting REAL data (API-Football)

How to switch from sample (mock) data to real football data.

## 0. How it works (1-minute read)

- The backend is a **proxy**: the frontend calls `/api/...` and the backend calls API-Football, **hiding the key** and **caching** responses.
- Mock data and the real API have **the same data shape**, so switching to the real API needs **NO frontend changes**.
- The only switch is the `USE_MOCK` variable in `backend/.env`.

```
Frontend (Vue)  →  /api  →  Backend (FastAPI)  →  API-Football
                                  ↑ keeps the key + cache
```

---

## 1. Get an API key

**Option A: Direct (recommended, matches the existing code):**
1. Go to https://www.api-football.com/ → **Register**.
2. Open the **Dashboard** → copy the **API key**.
3. In `.env`: set `API_FOOTBALL_VIA=direct` (header `x-apisports-key`).

**Option B: Through RapidAPI:**
1. https://rapidapi.com/ → search for **API-Football** → **Subscribe** to the **Basic (Free)** plan.
2. Copy the **X-RapidAPI-Key**.
3. In `.env`: set `API_FOOTBALL_VIA=rapidapi`.

---

## 2. Fill in `.env` and restart

```bash
cd backend
cp .env.example .env     # if you do not have a .env file yet
```

Open `backend/.env` and edit:

```
API_FOOTBALL_KEY=paste_your_key
API_FOOTBALL_VIA=direct      # or rapidapi
USE_MOCK=false
SEASON=0                     # 0 = infer from the date; see section 4
```

Go back to the backend terminal: `Ctrl+C`, then `uvicorn main:app --reload`.

> In the Jenkins pipeline the key is **not** in `.env`: production receives it from the
> Jenkins credential `API_FOOTBALL_KEY` at release time.

---

## 3. Check that it works

- `http://localhost:8000/api/health` → must show `"mock_mode": false`.
- `http://localhost:8000/api/fixtures?date=2025-08-16` → real matches (pick a date with fixtures).
- `http://localhost:8000/docs` → try each endpoint.

If a response is **empty with no error**, it is almost certainly the **season** (section 4), not a bug.

---

## 4. Seasons: the part most often MISTAKEN for a bug ⚠️

- The **free plan usually does NOT include the current season**; it only opens a few old seasons (e.g. 2021–2023).
- If everything is empty with `SEASON=2025`, change to `SEASON=2023` (or a season your plan covers).
- To see which seasons your plan covers: call `https://v3.football.api-sports.io/leagues?id=39` (with the key header)
  and look at the `seasons` array; the `coverage` field shows which seasons have data.

---

## 5b. IMPORTANT limits of the free plan (verified)

The free API-Football plan limits each type of data differently:

- **Standings / players / teams** → seasons **2021–2023** are available (e.g. `season=2023`). ✅
- **Fixtures and results by date (`/fixtures?date=`)** → **ONLY about 3 days around today**
  (yesterday → tomorrow). Querying a historical date (e.g. 2023) returns `errors.plan: "Free plans do not
  have access to this date"`. ❌

On the free plan the home page date picker is therefore limited to yesterday → tomorrow. To browse
**any date / season**, a **paid plan** is needed (only the key changes, no code changes).
This project now uses the **Pro plan**, so every date and season is available.

## 5. Quota (free = 100 requests/day)

- Resets at 00:00 UTC every day.
- The backend caches every response (tiered TTLs: 15 s for live data up to 24 h for the league list).
- **Testing tip:** do not leave the web tab open all day: the home page refreshes live matches every 15 s and uses quota. Close the tab when not in use.
- Opening one match page costs ~3 requests (details + line-ups + events). Keep this in mind when testing a lot.

---

## 6. Choosing / adding leagues

Open `backend/mock_data.py` and edit the `CURATED_LEAGUES` list (the list used by the filter dropdown). Use the **API-Football league id**:

| League | id |
|---|---|
| World Cup | 1 |
| Champions League | 2 |
| Premier League | 39 |
| Ligue 1 | 61 |
| Bundesliga | 78 |
| Serie A | 135 |
| La Liga | 140 |
| Saudi Pro League | 307 |

> Tip: on the free plan, make the home page **filter one league by default** (e.g. Premier League) instead of "All",
> because `/fixtures?date=` without a league returns hundreds of matches from every league, which is cluttered and uses more data.

---

## 7. Which endpoints the app calls (already implemented in `api_football.py`)

| App | API-Football |
|---|---|
| `/api/fixtures?date=&league=&season=` | `/fixtures` |
| `/api/fixtures/{id}` | `/fixtures?id=` |
| `/api/fixtures/{id}/lineups` | `/fixtures/lineups?fixture=` |
| `/api/fixtures/{id}/events` | `/fixtures/events?fixture=` |
| `/api/standings?league=&season=` | `/standings` |
| `/api/teams/{id}` | `/teams?id=` |
| `/api/players/{id}?season=` | `/players?id=&season=` |
| `/api/topscorers?league=&season=` | `/players/topscorers` |
| `/api/search?q=` | `/teams?search=` + `/players/profiles?search=` |

To add a new feature (e.g. match statistics `/fixtures/statistics`): add a function in `api_football.py`,
a route in `routers/` and a mock branch in `mock_data.py`, following the same pattern as the existing parts.

---

## 8. Common errors

| Symptom | Cause / fix |
|---|---|
| 401 / 403 | Wrong key, or wrong `API_FOOTBALL_VIA` (direct vs rapidapi) |
| Empty but no error | The season is not in the free plan → change `SEASON` (section 4) |
| "Too many requests" | Daily quota used up → wait for the 00:00 UTC reset or increase caching |
| Empty home page with `USE_MOCK=false` | `/fixtures` needs `?date=` (the app already sends it); check `SEASON` |
| CORS (after deployment) | Set `FRONTEND_ORIGIN` on the backend to the frontend URL |

---

## 9. Switching back to mock at any time

Set `USE_MOCK=true` (or remove `API_FOOTBALL_KEY`) and the app runs on sample data again.
Useful for offline demos or when the quota runs out. The tests and the CI pipeline always use mock data.
