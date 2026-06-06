"""
Football Match Hub - Backend (FastAPI)
Chạy: uvicorn main:app --reload  (từ trong thư mục backend/)
Docs tự sinh: http://localhost:8000/docs
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from routers import fixtures, standings, teams, players, search

app = FastAPI(title="Football Match Hub API", version="0.1.0")

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


@app.get("/api/health")
def health():
    return {"status": "ok", "mock_mode": settings.use_mock}
