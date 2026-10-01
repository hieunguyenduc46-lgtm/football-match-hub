"""
Shared test setup for the backend.

The app is forced into MOCK mode BEFORE it is imported, so the tests never call the
real API-Football service: no network, no API quota used, and the same result on
every run (important for a CI pipeline). In pydantic-settings, environment variables
take priority over values in backend/.env, so a developer's real key is ignored here.
"""
import os

os.environ["USE_MOCK"] = "true"
os.environ["API_FOOTBALL_KEY"] = ""
os.environ["DEBUG"] = "false"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402
from ratelimit import limiter  # noqa: E402


@pytest.fixture
def client():
    """HTTP client for the FastAPI app. The rate limiter is reset so tests do not affect each other."""
    limiter.reset()
    return TestClient(main.app)
