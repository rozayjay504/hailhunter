"""
Phase 2 data pipeline — public interface for the app.

Public API
──────────
  get_storms(start_date, end_date) → (DataFrame, source_label)
      Fetches live NOAA data, enforces the schema, and returns the full
      unfiltered DataFrame plus a label: "live" | "mock".
      Falls back to mock data automatically on any failure or empty result.

  filter_storms(df, filters) → DataFrame
      Re-exported from mock_storms — schema is identical, so the same
      filter logic applies to both live and mock data unchanged.

Caching
───────
  _fetch_live_data() is decorated with @st.cache_data(ttl=6h) so the
  30–80 MB NCEI CSV download only happens once per 6-hour window per
  unique (start_date, end_date) pair.  Filter changes that don't alter
  the date range hit the cache instantly.

Schema (all columns, all rows)
──────────────────────────────
  event_id       str
  event_type     str   — Hail | Wind | Hurricane | Tropical Storm
  severity       int   — 1 (Minor) … 4 (Catastrophic)
  hail_size      float — inches; NaN for non-hail
  wind_speed     float — mph; NaN for non-wind
  lat            float
  lon            float
  city           str
  state          str   — 2-letter abbreviation
  county         str
  date           date
  homes_affected int
  avg_roof_age   int   — Phase 3: enriched from Census ACS
  owner_pct      float — Phase 3: enriched from Census ACS
  radius_miles   float
  description    str
"""

import logging
from datetime import date, timedelta
from typing import Optional

import pandas as pd
import streamlit as st

# filter_storms is re-exported so app.py only needs one import
from data.mock_storms import filter_storms, get_mock_storms  # noqa: F401
from data.noaa_client import fetch_ncei_storms, fetch_nws_alerts

log = logging.getLogger(__name__)

# Required columns and their target dtypes — enforced on every DataFrame
_SCHEMA: dict[str, str] = {
    "event_id":      "object",
    "event_type":    "object",
    "severity":      "int64",
    "hail_size":     "float64",
    "wind_speed":    "float64",
    "lat":           "float64",
    "lon":           "float64",
    "city":          "object",
    "state":         "object",
    "county":        "object",
    "homes_affected": "int64",
    "avg_roof_age":  "int64",
    "owner_pct":     "float64",
    "radius_miles":  "float64",
    "description":   "object",
}

# Fallback threshold: if live data returns fewer events than this we
# consider it a degraded response and supplement with mock data.
_MIN_LIVE_RECORDS = 5


def _enforce_schema(df: pd.DataFrame) -> pd.DataFrame:
    """Guarantee all required columns exist with correct dtypes."""
    for col, dtype in _SCHEMA.items():
        if col not in df.columns:
            df[col] = None
        if dtype == "int64":
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype("int64")
        elif dtype == "float64":
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("float64")
        else:
            df[col] = df[col].fillna("").astype(str)
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
    return df


@st.cache_data(
    ttl=3600 * 6,
    show_spinner="Fetching storm data from NOAA…",
)
def _fetch_live_data(start_date: date, end_date: date) -> list[dict]:
    """
    Download NCEI Storm Events CSV(s) + NWS active alerts.
    Cached for 6 hours per unique (start_date, end_date) pair.
    Returns a flat list of raw schema dicts.
    """
    records = fetch_ncei_storms(start_date, end_date)

    # Merge NWS real-time alerts — deduplicate against NCEI by (lat, lon, date)
    ncei_keys = {(r["lat"], r["lon"], str(r["date"])) for r in records}
    for alert in fetch_nws_alerts():
        key = (alert["lat"], alert["lon"], str(alert["date"]))
        if key not in ncei_keys:
            records.append(alert)
            ncei_keys.add(key)

    log.info("Live data total: %d records (%s → %s)", len(records), start_date, end_date)
    return records


def get_storms(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> tuple[pd.DataFrame, str]:
    """
    Fetch real NOAA storm events for the given date range.

    Returns:
        (df, source) where source is "live" or "mock".

    Falls back to mock data and logs a warning when:
      - Any exception occurs during the live fetch
      - Live data returns fewer than _MIN_LIVE_RECORDS events
    """
    if start_date is None:
        start_date = date.today() - timedelta(days=90)
    if end_date is None:
        end_date = date.today()

    try:
        records = _fetch_live_data(start_date, end_date)

        if len(records) < _MIN_LIVE_RECORDS:
            log.warning(
                "Live data returned only %d records — falling back to mock data. "
                "NCEI may not have published data for this date range yet.",
                len(records),
            )
            return _mock_fallback()

        df = pd.DataFrame(records)
        df = _enforce_schema(df)
        df = df.drop_duplicates(subset=["event_id"]).reset_index(drop=True)
        log.info("Pipeline: serving %d live records", len(df))
        return df, "live"

    except Exception as exc:
        log.exception("Live pipeline failed: %s", exc)
        return _mock_fallback()


def _mock_fallback() -> tuple[pd.DataFrame, str]:
    df = get_mock_storms()
    df = _enforce_schema(df)
    return df, "mock"
