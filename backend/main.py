"""
Football Match Hub - Backend (FastAPI)
Run: uvicorn main:app --reload  (from inside the backend/ folder)
Auto-generated docs: http://localhost:8000/docs
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from config import settings
from ratelimit import limiter
from routers import fixtures, standings, teams, players, search

app = FastAPI(title="Football Match Hub API", version="0.1.0")

# Attach the limiter (rate limit per IP). Only routes with @limiter.limit are limited;
# exceeding the limit -> returns 429 (slowapi's default handler) without affecting other routes.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Allow the frontend to call the backend.
# FRONTEND_ORIGIN can be several URLs separated by commas (dev + deployed domain).
_origins = [o.strip() for o in settings.frontend_origin.split(",") if o.strip()]
_origins = list({*_origins, "http://localhost:5173"})

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(fixtures.router)
app.include_router(standings.router)
app.include_router(teams.router)
app.include_router(players.router)
app.include_router(search.router)


# Accept both GET and HEAD: many uptime services (UptimeRobot...) ping with HEAD;
# if only GET is declared, HEAD returns 405 -> the monitor wrongly reports 'Down'.
@app.api_route("/api/health", methods=["GET", "HEAD"])
def health():
    return {"status": "ok", "mock_mode": settings.use_mock}
