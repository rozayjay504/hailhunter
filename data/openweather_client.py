"""
OpenWeather API client — Phase 2 enrichment layer.

Phase 2 uses:
  - reverse_geocode(lat, lon)   → fill city/county/state when NOAA lacks them
  - current_conditions(lat, lon) → available now, surfaced in Phase 3 panel UI

Requires OPENWEATHER_API_KEY in .env (free tier: 1,000 calls/day).
All functions degrade silently to empty dict / None when the key is absent
or any request fails — the pipeline never hard-depends on this client.

Get a free key at: https://openweathermap.org/api → "Get API key"
"""

import logging
import os
from typing import Optional

import requests
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger(__name__)

_API_KEY: str = os.getenv("OPENWEATHER_API_KEY", "")
_GEO_URL     = "http://api.openweathermap.org/geo/1.0/reverse"
_WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"
_TIMEOUT = 10


def _available() -> bool:
    return bool(_API_KEY)


def reverse_geocode(lat: float, lon: float) -> dict:
    """
    Return {city, state} for the given coordinates via OpenWeather Geocoding API.
    Used when NCEI provides lat/lon but BEGIN_LOCATION is empty.
    Returns {} silently if key is absent or request fails.
    """
    if not _available():
        return {}
    try:
        resp = requests.get(
            _GEO_URL,
            params={"lat": lat, "lon": lon, "limit": 1, "appid": _API_KEY},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        results = resp.json()
        if not results:
            return {}
        r = results[0]
        return {
            "city":  r.get("name", ""),
            "state": r.get("state", ""),
        }
    except Exception as exc:
        log.debug("OpenWeather reverse geocode (%.4f, %.4f): %s", lat, lon, exc)
        return {}


def current_conditions(lat: float, lon: float) -> Optional[dict]:
    """
    Return current weather at the given coordinates.
    Phase 2: collected but not yet wired into the map UI.
    Phase 3: surface alongside event data in the zone intelligence panel.

    Returns None silently if key is absent or request fails.
    """
    if not _available():
        return None
    try:
        resp = requests.get(
            _WEATHER_URL,
            params={"lat": lat, "lon": lon, "units": "imperial", "appid": _API_KEY},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        d = resp.json()
        return {
            "temp_f":     d.get("main", {}).get("temp"),
            "humidity":   d.get("main", {}).get("humidity"),
            # OW current speed is m/s in imperial mode — it's already mph with units=imperial
            "wind_mph":   round(d.get("wind", {}).get("speed", 0), 1),
            "conditions": d.get("weather", [{}])[0].get("description", ""),
            "icon":       d.get("weather", [{}])[0].get("icon", ""),
        }
    except Exception as exc:
        log.debug("OpenWeather conditions (%.4f, %.4f): %s", lat, lon, exc)
        return None
