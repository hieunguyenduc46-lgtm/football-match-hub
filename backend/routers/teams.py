from fastapi import APIRouter

import api_football

router = APIRouter(prefix="/api", tags=["teams"])


@router.get("/teams/{team_id}")
async def team_detail(team_id: int):
    """Team info + stadium + (mock) squad."""
    return {"response": await api_football.get_team(team_id)}


@router.get("/teams/{team_id}/fixtures")
async def team_fixtures(team_id: int):
    """The team's recent fixtures/results (for W-D-L form)."""
    return {"response": await api_football.get_team_fixtures(team_id)}


@router.get("/teams/{team_id}/upcoming")
async def team_upcoming(team_id: int):
    """The team's upcoming fixtures."""
    return {"response": await api_football.get_team_upcoming(team_id)}


@router.get("/teams/{team_id}/insights")
async def team_insights(team_id: int):
    """Season statistics (form, wins/draws/losses, average goals, clean sheets, streaks) + injury list.
    LAZY-loaded on the team page. Returns {statistics, injuries}."""
    return await api_football.get_team_insights(team_id)
