"""
Football Match Hub - Backend (FastAPI)
Chạy: uvicorn main:app --reload  (từ trong thư mục backend/)
Docs tự sinh: http://localhost:8000/docs
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from config import settings
from ratelimit import limiter
from routers import fixtures, standings, teams, players, search

app = FastAPI(title="Football Match Hub API", version="0.1.0")

# Gắn limiter (rate limit theo IP). Chỉ các route có @limiter.limit mới bị giới hạn;
# vượt giới hạn -> trả 429 (handler mặc định của slowapi), không làm hỏng các route khác.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Cho phép frontend gọi sang backend.
# FRONTEND_ORIGIN có thể là nhiều URL cách nhau dấu phẩy (dev + domain deploy).
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


# Nhận cả GET lẫn HEAD: nhiều dịch vụ uptime (UptimeRobot...) ping bằng HEAD,
# nếu chỉ khai báo GET thì HEAD bị trả 405 -> monitor báo "Down" nhầm.
@app.api_route("/api/health", methods=["GET", "HEAD"])
def health():
    return {"status": "ok", "mock_mode": settings.use_mock}
