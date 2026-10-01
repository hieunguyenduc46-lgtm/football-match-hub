"""
Rate limiting per IP: stops one person from hammering the API and draining the API quota.

Why only a few 'heavy' endpoints are limited instead of all of them:
  - /standings, /fixtures, /leagues... are very cheap and use a SHARED cache (1 API request/TTL/cache key
    no matter how many users) -> spamming them costs almost no extra quota.
  - /players/{id}/motm scans ~50 matches (~50 API requests each time), /career scans many seasons,
    /search calls /players/profiles several times -> this is where a script calling many DIFFERENT ids
    could burn the whole quota. So locking down these multiplying endpoints is enough.

Uses the @limiter.limit(...) decorator per route (no global middleware), so the other
endpoints are NOT affected at all.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

# key_func = caller's IP. No default_limits -> only routes with the decorator are limited.
limiter = Limiter(key_func=get_remote_address)
