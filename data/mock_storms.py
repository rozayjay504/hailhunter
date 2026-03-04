"""
Mock storm event data for Phase 1.

Schema mirrors NOAA Storm Events API so Phase 2 is a clean drop-in swap:
  event_id       — unique string identifier
  event_type     — Hail | Wind | Hurricane | Tropical Storm
  severity       — 1 (Minor) to 4 (Catastrophic)
  hail_size      — diameter in inches; None for non-hail events
  wind_speed     — mph; None for non-wind events
  lat, lon       — event epicenter coordinates
  city, state    — human-readable location
  county         — county name
  date           — ISO 8601 date string (YYYY-MM-DD)
  homes_affected — estimated impacted homes in zone
  avg_roof_age   — average roof age in zone (years)
  owner_pct      — fraction of homes that are owner-occupied (0.0–1.0)
  radius_miles   — approximate radius of the affected area
  description    — short event description
"""

import pandas as pd
from datetime import date


def get_mock_storms() -> pd.DataFrame:
    """Return a DataFrame of mock storm events covering the last ~90 days."""

    records = [
        # ── Texas Hail Corridor ─────────────────────────────────────────────
        {
            "event_id": "EVT001", "event_type": "Hail", "severity": 3,
            "hail_size": 1.75, "wind_speed": None,
            "lat": 32.78, "lon": -96.80, "city": "Dallas", "state": "TX", "county": "Dallas",
            "date": "2026-01-14", "homes_affected": 1840, "avg_roof_age": 19,
            "owner_pct": 0.58, "radius_miles": 12.0,
            "description": "Ping-pong-sized hail across North Dallas suburbs",
        },
        {
            "event_id": "EVT002", "event_type": "Hail", "severity": 4,
            "hail_size": 2.50, "wind_speed": None,
            "lat": 29.76, "lon": -95.37, "city": "Houston", "state": "TX", "county": "Harris",
            "date": "2025-12-18", "homes_affected": 3200, "avg_roof_age": 22,
            "owner_pct": 0.51, "radius_miles": 18.0,
            "description": "Baseball-sized hail — catastrophic roof damage across Houston metro",
        },
        {
            "event_id": "EVT003", "event_type": "Hail", "severity": 2,
            "hail_size": 1.25, "wind_speed": None,
            "lat": 32.75, "lon": -97.33, "city": "Fort Worth", "state": "TX", "county": "Tarrant",
            "date": "2026-01-28", "homes_affected": 920, "avg_roof_age": 15,
            "owner_pct": 0.61, "radius_miles": 9.0,
            "description": "Quarter-sized hail in Fort Worth western suburbs",
        },
        {
            "event_id": "EVT004", "event_type": "Hail", "severity": 3,
            "hail_size": 2.00, "wind_speed": None,
            "lat": 29.43, "lon": -98.49, "city": "San Antonio", "state": "TX", "county": "Bexar",
            "date": "2026-02-05", "homes_affected": 1100, "avg_roof_age": 17,
            "owner_pct": 0.55, "radius_miles": 10.5,
            "description": "Golf-ball-sized hail in the North Side",
        },
        {
            "event_id": "EVT005", "event_type": "Hail", "severity": 1,
            "hail_size": 0.75, "wind_speed": None,
            "lat": 30.27, "lon": -97.74, "city": "Austin", "state": "TX", "county": "Travis",
            "date": "2026-02-19", "homes_affected": 380, "avg_roof_age": 12,
            "owner_pct": 0.49, "radius_miles": 6.0,
            "description": "Pea-sized hail in Central Austin",
        },
        {
            "event_id": "EVT006", "event_type": "Hail", "severity": 2,
            "hail_size": 1.50, "wind_speed": None,
            "lat": 33.58, "lon": -101.86, "city": "Lubbock", "state": "TX", "county": "Lubbock",
            "date": "2026-01-07", "homes_affected": 640, "avg_roof_age": 24,
            "owner_pct": 0.63, "radius_miles": 8.0,
            "description": "Half-dollar hail across South Lubbock",
        },
        {
            "event_id": "EVT007", "event_type": "Hail", "severity": 4,
            "hail_size": 3.00, "wind_speed": None,
            "lat": 35.22, "lon": -101.83, "city": "Amarillo", "state": "TX", "county": "Potter",
            "date": "2025-12-28", "homes_affected": 2600, "avg_roof_age": 27,
            "owner_pct": 0.64, "radius_miles": 14.0,
            "description": "Baseball-plus hail — widespread catastrophic damage",
        },

        # ── Oklahoma / Kansas ────────────────────────────────────────────────
        {
            "event_id": "EVT008", "event_type": "Hail", "severity": 3,
            "hail_size": 1.75, "wind_speed": None,
            "lat": 35.47, "lon": -97.52, "city": "Oklahoma City", "state": "OK", "county": "Oklahoma",
            "date": "2026-02-12", "homes_affected": 1560, "avg_roof_age": 21,
            "owner_pct": 0.60, "radius_miles": 13.0,
            "description": "Ping-pong hail in OKC metro — second event this season",
        },
        {
            "event_id": "EVT009", "event_type": "Hail", "severity": 2,
            "hail_size": 1.25, "wind_speed": None,
            "lat": 36.15, "lon": -95.99, "city": "Tulsa", "state": "OK", "county": "Tulsa",
            "date": "2026-01-20", "homes_affected": 780, "avg_roof_age": 18,
            "owner_pct": 0.57, "radius_miles": 9.5,
            "description": "Quarter-sized hail across East Tulsa",
        },
        {
            "event_id": "EVT010", "event_type": "Hail", "severity": 3,
            "hail_size": 2.00, "wind_speed": None,
            "lat": 37.69, "lon": -97.34, "city": "Wichita", "state": "KS", "county": "Sedgwick",
            "date": "2025-12-09", "homes_affected": 1230, "avg_roof_age": 23,
            "owner_pct": 0.65, "radius_miles": 11.0,
            "description": "Golf-ball hail in Wichita suburbs",
        },

        # ── Missouri / Illinois ──────────────────────────────────────────────
        {
            "event_id": "EVT011", "event_type": "Hail", "severity": 2,
            "hail_size": 1.00, "wind_speed": None,
            "lat": 39.10, "lon": -94.58, "city": "Kansas City", "state": "MO", "county": "Jackson",
            "date": "2026-01-31", "homes_affected": 860, "avg_roof_age": 20,
            "owner_pct": 0.54, "radius_miles": 10.0,
            "description": "Dime-sized hail in South KC neighborhoods",
        },
        {
            "event_id": "EVT012", "event_type": "Hail", "severity": 1,
            "hail_size": 0.75, "wind_speed": None,
            "lat": 38.63, "lon": -90.20, "city": "St. Louis", "state": "MO", "county": "St. Louis",
            "date": "2026-02-22", "homes_affected": 420, "avg_roof_age": 31,
            "owner_pct": 0.52, "radius_miles": 7.0,
            "description": "Pea-sized hail in North St. Louis County",
        },
        {
            "event_id": "EVT013", "event_type": "Hail", "severity": 3,
            "hail_size": 1.75, "wind_speed": None,
            "lat": 41.88, "lon": -87.63, "city": "Chicago", "state": "IL", "county": "Cook",
            "date": "2026-01-10", "homes_affected": 2100, "avg_roof_age": 38,
            "owner_pct": 0.44, "radius_miles": 15.0,
            "description": "Severe hail in Chicago southwest suburbs",
        },

        # ── Southeast / Tennessee ────────────────────────────────────────────
        {
            "event_id": "EVT014", "event_type": "Hail", "severity": 2,
            "hail_size": 1.25, "wind_speed": None,
            "lat": 36.17, "lon": -86.78, "city": "Nashville", "state": "TN", "county": "Davidson",
            "date": "2026-02-08", "homes_affected": 740, "avg_roof_age": 16,
            "owner_pct": 0.59, "radius_miles": 9.0,
            "description": "Quarter hail in East Nashville and Donelson",
        },
        {
            "event_id": "EVT015", "event_type": "Hail", "severity": 3,
            "hail_size": 2.00, "wind_speed": None,
            "lat": 35.15, "lon": -90.05, "city": "Memphis", "state": "TN", "county": "Shelby",
            "date": "2025-12-21", "homes_affected": 1380, "avg_roof_age": 25,
            "owner_pct": 0.50, "radius_miles": 12.0,
            "description": "Golf-ball hail causing significant damage in Midtown Memphis",
        },
        {
            "event_id": "EVT016", "event_type": "Hail", "severity": 2,
            "hail_size": 1.50, "wind_speed": None,
            "lat": 33.52, "lon": -86.80, "city": "Birmingham", "state": "AL", "county": "Jefferson",
            "date": "2026-01-25", "homes_affected": 680, "avg_roof_age": 28,
            "owner_pct": 0.56, "radius_miles": 8.5,
            "description": "Half-dollar hail across Birmingham suburbs",
        },

        # ── Georgia / Carolinas ───────────────────────────────────────────────
        {
            "event_id": "EVT017", "event_type": "Hail", "severity": 1,
            "hail_size": 0.75, "wind_speed": None,
            "lat": 33.75, "lon": -84.39, "city": "Atlanta", "state": "GA", "county": "Fulton",
            "date": "2026-02-15", "homes_affected": 510, "avg_roof_age": 14,
            "owner_pct": 0.48, "radius_miles": 7.0,
            "description": "Minor hail event in North Atlanta suburbs",
        },
        {
            "event_id": "EVT018", "event_type": "Hail", "severity": 2,
            "hail_size": 1.25, "wind_speed": None,
            "lat": 35.23, "lon": -80.84, "city": "Charlotte", "state": "NC", "county": "Mecklenburg",
            "date": "2026-01-18", "homes_affected": 890, "avg_roof_age": 17,
            "owner_pct": 0.61, "radius_miles": 9.5,
            "description": "Quarter-sized hail in South Charlotte",
        },

        # ── Ohio Valley ──────────────────────────────────────────────────────
        {
            "event_id": "EVT019", "event_type": "Hail", "severity": 3,
            "hail_size": 1.75, "wind_speed": None,
            "lat": 39.77, "lon": -86.16, "city": "Indianapolis", "state": "IN", "county": "Marion",
            "date": "2025-12-15", "homes_affected": 1100, "avg_roof_age": 22,
            "owner_pct": 0.58, "radius_miles": 10.5,
            "description": "Severe hail event in Indy north suburbs",
        },
        {
            "event_id": "EVT020", "event_type": "Hail", "severity": 2,
            "hail_size": 1.00, "wind_speed": None,
            "lat": 39.96, "lon": -82.99, "city": "Columbus", "state": "OH", "county": "Franklin",
            "date": "2026-02-02", "homes_affected": 620, "avg_roof_age": 19,
            "owner_pct": 0.55, "radius_miles": 8.0,
            "description": "Dime-sized hail across Columbus east side",
        },

        # ── Great Plains ─────────────────────────────────────────────────────
        {
            "event_id": "EVT021", "event_type": "Hail", "severity": 4,
            "hail_size": 2.50, "wind_speed": None,
            "lat": 37.21, "lon": -93.29, "city": "Springfield", "state": "MO", "county": "Greene",
            "date": "2025-12-05", "homes_affected": 1950, "avg_roof_age": 26,
            "owner_pct": 0.62, "radius_miles": 13.0,
            "description": "Tennis-ball hail — catastrophic damage to older neighborhoods",
        },
        {
            "event_id": "EVT022", "event_type": "Hail", "severity": 2,
            "hail_size": 1.25, "wind_speed": None,
            "lat": 41.60, "lon": -93.62, "city": "Des Moines", "state": "IA", "county": "Polk",
            "date": "2026-02-25", "homes_affected": 580, "avg_roof_age": 20,
            "owner_pct": 0.64, "radius_miles": 8.0,
            "description": "Quarter hail across West Des Moines",
        },
        {
            "event_id": "EVT023", "event_type": "Hail", "severity": 3,
            "hail_size": 1.75, "wind_speed": None,
            "lat": 41.26, "lon": -95.94, "city": "Omaha", "state": "NE", "county": "Douglas",
            "date": "2026-01-03", "homes_affected": 1020, "avg_roof_age": 24,
            "owner_pct": 0.60, "radius_miles": 10.0,
            "description": "Ping-pong hail causing widespread roofing damage in Omaha",
        },

        # ── Colorado ─────────────────────────────────────────────────────────
        {
            "event_id": "EVT024", "event_type": "Hail", "severity": 4,
            "hail_size": 2.50, "wind_speed": None,
            "lat": 39.74, "lon": -104.98, "city": "Denver", "state": "CO", "county": "Denver",
            "date": "2025-12-30", "homes_affected": 3100, "avg_roof_age": 18,
            "owner_pct": 0.53, "radius_miles": 16.0,
            "description": "Catastrophic hail event in Denver metro — high claim volume expected",
        },
        {
            "event_id": "EVT025", "event_type": "Hail", "severity": 3,
            "hail_size": 2.00, "wind_speed": None,
            "lat": 38.83, "lon": -104.82, "city": "Colorado Springs", "state": "CO", "county": "El Paso",
            "date": "2026-01-22", "homes_affected": 1340, "avg_roof_age": 20,
            "owner_pct": 0.58, "radius_miles": 11.0,
            "description": "Golf-ball hail in Colorado Springs north side",
        },

        # ── Wind Events ──────────────────────────────────────────────────────
        {
            "event_id": "EVT026", "event_type": "Wind", "severity": 2,
            "hail_size": None, "wind_speed": 68,
            "lat": 34.75, "lon": -92.29, "city": "Little Rock", "state": "AR", "county": "Pulaski",
            "date": "2026-01-17", "homes_affected": 730, "avg_roof_age": 23,
            "owner_pct": 0.56, "radius_miles": 9.0,
            "description": "Straight-line winds at 68 mph — shingle damage across West Little Rock",
        },
        {
            "event_id": "EVT027", "event_type": "Wind", "severity": 3,
            "hail_size": None, "wind_speed": 82,
            "lat": 32.30, "lon": -90.18, "city": "Jackson", "state": "MS", "county": "Hinds",
            "date": "2025-12-23", "homes_affected": 1100, "avg_roof_age": 29,
            "owner_pct": 0.50, "radius_miles": 11.0,
            "description": "Severe straight-line winds tore shingles across North Jackson",
        },
        {
            "event_id": "EVT028", "event_type": "Wind", "severity": 2,
            "hail_size": None, "wind_speed": 71,
            "lat": 38.25, "lon": -85.76, "city": "Louisville", "state": "KY", "county": "Jefferson",
            "date": "2026-02-10", "homes_affected": 650, "avg_roof_age": 21,
            "owner_pct": 0.57, "radius_miles": 9.5,
            "description": "Moderate wind event in East Louisville suburbs",
        },
        {
            "event_id": "EVT029", "event_type": "Wind", "severity": 3,
            "hail_size": None, "wind_speed": 79,
            "lat": 43.55, "lon": -96.73, "city": "Sioux Falls", "state": "SD", "county": "Minnehaha",
            "date": "2026-02-01", "homes_affected": 820, "avg_roof_age": 25,
            "owner_pct": 0.66, "radius_miles": 10.0,
            "description": "Severe wind event causing roof uplift damage",
        },
        {
            "event_id": "EVT030", "event_type": "Wind", "severity": 1,
            "hail_size": None, "wind_speed": 57,
            "lat": 40.44, "lon": -79.99, "city": "Pittsburgh", "state": "PA", "county": "Allegheny",
            "date": "2026-02-20", "homes_affected": 390, "avg_roof_age": 35,
            "owner_pct": 0.60, "radius_miles": 7.0,
            "description": "Minor wind damage to aging rooftops in Pittsburgh east suburbs",
        },
        {
            "event_id": "EVT031", "event_type": "Wind", "severity": 4,
            "hail_size": None, "wind_speed": 98,
            "lat": 46.88, "lon": -96.79, "city": "Fargo", "state": "ND", "county": "Cass",
            "date": "2026-01-05", "homes_affected": 1680, "avg_roof_age": 22,
            "owner_pct": 0.62, "radius_miles": 13.0,
            "description": "Near-tornado-force winds devastated South Fargo neighborhoods",
        },
        {
            "event_id": "EVT032", "event_type": "Wind", "severity": 2,
            "hail_size": None, "wind_speed": 65,
            "lat": 44.98, "lon": -93.27, "city": "Minneapolis", "state": "MN", "county": "Hennepin",
            "date": "2026-01-29", "homes_affected": 720, "avg_roof_age": 28,
            "owner_pct": 0.53, "radius_miles": 9.0,
            "description": "Moderate straight-line wind event in SW Minneapolis",
        },
        {
            "event_id": "EVT033", "event_type": "Wind", "severity": 3,
            "hail_size": None, "wind_speed": 85,
            "lat": 35.78, "lon": -78.64, "city": "Raleigh", "state": "NC", "county": "Wake",
            "date": "2025-12-12", "homes_affected": 940, "avg_roof_age": 15,
            "owner_pct": 0.63, "radius_miles": 10.5,
            "description": "High wind event caused shingle loss in Raleigh suburbs",
        },
        {
            "event_id": "EVT034", "event_type": "Wind", "severity": 1,
            "hail_size": None, "wind_speed": 54,
            "lat": 35.08, "lon": -106.65, "city": "Albuquerque", "state": "NM", "county": "Bernalillo",
            "date": "2026-02-27", "homes_affected": 310, "avg_roof_age": 20,
            "owner_pct": 0.58, "radius_miles": 6.5,
            "description": "Minor wind event in the East Mountains foothills",
        },

        # ── Hurricane Events ─────────────────────────────────────────────────
        {
            "event_id": "EVT035", "event_type": "Hurricane", "severity": 4,
            "hail_size": None, "wind_speed": 130,
            "lat": 25.77, "lon": -80.19, "city": "Miami", "state": "FL", "county": "Miami-Dade",
            "date": "2025-12-08", "homes_affected": 12400, "avg_roof_age": 16,
            "owner_pct": 0.47, "radius_miles": 35.0,
            "description": "Category 3 landfall — catastrophic wind and debris damage across Miami-Dade",
        },
        {
            "event_id": "EVT036", "event_type": "Hurricane", "severity": 3,
            "hail_size": None, "wind_speed": 105,
            "lat": 30.33, "lon": -81.66, "city": "Jacksonville", "state": "FL", "county": "Duval",
            "date": "2025-12-10", "homes_affected": 4800, "avg_roof_age": 18,
            "owner_pct": 0.55, "radius_miles": 22.0,
            "description": "Tropical storm post-landfall — severe roof damage in coastal areas",
        },
        {
            "event_id": "EVT037", "event_type": "Hurricane", "severity": 4,
            "hail_size": None, "wind_speed": 145,
            "lat": 27.95, "lon": -82.46, "city": "Tampa", "state": "FL", "county": "Hillsborough",
            "date": "2025-12-07", "homes_affected": 9200, "avg_roof_age": 19,
            "owner_pct": 0.52, "radius_miles": 30.0,
            "description": "Major hurricane — widespread catastrophic roofing damage across Tampa Bay",
        },
        {
            "event_id": "EVT038", "event_type": "Hurricane", "severity": 3,
            "hail_size": None, "wind_speed": 112,
            "lat": 30.44, "lon": -84.28, "city": "Tallahassee", "state": "FL", "county": "Leon",
            "date": "2025-12-09", "homes_affected": 3600, "avg_roof_age": 22,
            "owner_pct": 0.57, "radius_miles": 18.0,
            "description": "Severe wind damage as storm tracked inland through North Florida",
        },
        {
            "event_id": "EVT039", "event_type": "Hurricane", "severity": 2,
            "hail_size": None, "wind_speed": 88,
            "lat": 32.08, "lon": -81.10, "city": "Savannah", "state": "GA", "county": "Chatham",
            "date": "2025-12-11", "homes_affected": 2100, "avg_roof_age": 24,
            "owner_pct": 0.53, "radius_miles": 16.0,
            "description": "Tropical-force winds as outer bands swept the Georgia coast",
        },

        # ── Tropical Storm Events ────────────────────────────────────────────
        {
            "event_id": "EVT040", "event_type": "Tropical Storm", "severity": 2,
            "hail_size": None, "wind_speed": 62,
            "lat": 32.78, "lon": -79.94, "city": "Charleston", "state": "SC", "county": "Charleston",
            "date": "2025-12-13", "homes_affected": 1340, "avg_roof_age": 21,
            "owner_pct": 0.56, "radius_miles": 12.0,
            "description": "Tropical storm remnants — widespread shingle loss in Charleston metro",
        },
        {
            "event_id": "EVT041", "event_type": "Tropical Storm", "severity": 2,
            "hail_size": None, "wind_speed": 58,
            "lat": 34.00, "lon": -81.03, "city": "Columbia", "state": "SC", "county": "Richland",
            "date": "2025-12-14", "homes_affected": 980, "avg_roof_age": 19,
            "owner_pct": 0.59, "radius_miles": 11.0,
            "description": "Tropical storm winds tracking inland through the Midlands",
        },
        {
            "event_id": "EVT042", "event_type": "Tropical Storm", "severity": 1,
            "hail_size": None, "wind_speed": 47,
            "lat": 37.54, "lon": -77.43, "city": "Richmond", "state": "VA", "county": "Richmond City",
            "date": "2025-12-15", "homes_affected": 460, "avg_roof_age": 33,
            "owner_pct": 0.52, "radius_miles": 8.0,
            "description": "Weakening tropical storm remnants caused minor roof damage",
        },
        {
            "event_id": "EVT043", "event_type": "Tropical Storm", "severity": 3,
            "hail_size": None, "wind_speed": 74,
            "lat": 35.23, "lon": -75.60, "city": "Outer Banks", "state": "NC", "county": "Dare",
            "date": "2025-12-12", "homes_affected": 1800, "avg_roof_age": 14,
            "owner_pct": 0.45, "radius_miles": 14.0,
            "description": "Direct hit on Outer Banks — coastal properties sustained severe damage",
        },
        {
            "event_id": "EVT044", "event_type": "Tropical Storm", "severity": 2,
            "hail_size": None, "wind_speed": 60,
            "lat": 31.23, "lon": -85.39, "city": "Dothan", "state": "AL", "county": "Houston",
            "date": "2025-12-10", "homes_affected": 820, "avg_roof_age": 26,
            "owner_pct": 0.61, "radius_miles": 10.0,
            "description": "Tropical storm winds swept through the Wiregrass region",
        },
        {
            "event_id": "EVT045", "event_type": "Tropical Storm", "severity": 1,
            "hail_size": None, "wind_speed": 45,
            "lat": 30.69, "lon": -88.04, "city": "Mobile", "state": "AL", "county": "Mobile",
            "date": "2025-12-09", "homes_affected": 540, "avg_roof_age": 28,
            "owner_pct": 0.54, "radius_miles": 9.0,
            "description": "Tropical storm brushed the Gulf Coast with minor wind damage",
        },
    ]

    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    return df


def filter_storms(df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    """
    Apply sidebar filter state to the storm DataFrame.

    filters keys:
        storm_types     list[str]  — active storm type selections
        hail_size_min   float      — minimum hail diameter in inches
        date_start      date       — start of date window
        date_end        date       — end of date window
        home_age_min    int        — minimum avg roof age
        home_age_max    int        — maximum avg roof age (50 = 50+)
        owner_type      str        — "All" | "Owners Only" | "Renters Only"
        severity_min    int        — 1–4
    """
    mask = pd.Series(True, index=df.index)

    # Storm type
    active_types = filters.get("storm_types", [])
    if active_types:
        mask &= df["event_type"].isin(active_types)
    else:
        return df.iloc[0:0]  # nothing selected → empty

    # Hail size (only applies to Hail events)
    hail_min = filters.get("hail_size_min", 0.75)
    mask &= (df["event_type"] != "Hail") | (df["hail_size"] >= hail_min)

    # Date range
    start = filters.get("date_start")
    end = filters.get("date_end")
    if start:
        mask &= df["date"] >= start
    if end:
        mask &= df["date"] <= end

    # Roof age
    age_min = filters.get("home_age_min", 0)
    age_max = filters.get("home_age_max", 50)
    mask &= df["avg_roof_age"] >= age_min
    if age_max < 50:
        mask &= df["avg_roof_age"] <= age_max

    # Occupancy
    owner_type = filters.get("owner_type", "All")
    if owner_type == "Owners Only":
        mask &= df["owner_pct"] >= 0.5
    elif owner_type == "Renters Only":
        mask &= df["owner_pct"] < 0.5

    # Severity
    sev_min = filters.get("severity_min", 1)
    mask &= df["severity"] >= sev_min

    return df[mask].reset_index(drop=True)
