"""
Phase 2 data pipeline — public interface for the app.

Public API
──────────
  get_storms(start_date, end_date) → (DataFrame, source_label)
      Returns live NOAA storm events normalized to the HailHunter schema,
      or mock data if live sources are unavailable.

  filter_storms(df, filters) → DataFrame
      Re-exported from mock_storms — schema is identical for both live
      and mock DataFrames, so the same filter logic applies to both.

Caching strategy
────────────────
  Annual CSV files are the expensive part (30–80 MB each, compressed).
  They are cached INDEPENDENTLY, keyed by the exact NCEI filename which
  already embeds the file's creation date, e.g.:

      StormEvents_details-ftp_v1.0_d2025_c20260301.gz
                                        ────────────
                                        creation date = natural cache-buster

  This means:
  • The 2025 CSV is downloaded once and reused for any query that includes 2025.
  • Changing the date range (e.g. 90D → year-long) does NOT re-download files
    that are already cached — it just re-slices from the cached annual data.
  • If NCEI publishes an updated file (new creation date), the filename changes
    and the old cache entry is no longer referenced — automatic invalidation.
  • Each calendar year in the requested range is fetched independently, so a
    3-year span correctly downloads and caches 3 separate files.

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

# filter_storms re-exported so app.py has a single import point
from data.mock_storms import filter_storms, get_mock_storms  # noqa: F401
from data.noaa_client import (
    fetch_ncei_index_html,
    fetch_ncei_year_records,
    fetch_nws_alerts,
    find_ncei_filename,
)

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


# ── Per-layer caches ───────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def _ncei_index() -> str:
    """Cache the NCEI directory listing HTML for 1 hour."""
    return fetch_ncei_index_html()


@st.cache_data(
    ttl=3600 * 6,
    show_spinner="Downloading NCEI storm data…",
)
def _ncei_year(filename: str) -> list[dict]:
    """
    Cache one annual NCEI CSV keyed by its exact filename.

    The filename contains the NCEI creation date (e.g. _c20260301.gz), so:
    • Changing the date range hits this cache and returns instantly —
      no re-download needed for years already fetched.
    • If NCEI re-publishes a year with a new creation date, the new
      filename is a different key and the updated file is downloaded.
    """
    return fetch_ncei_year_records(filename)


# ── Assembly ───────────────────────────────────────────────────────────────────

def _assemble_live(start_date: date, end_date: date) -> list[dict]:
    """
    Assemble storm events for [start_date, end_date] from per-year cache entries.

    Covers every calendar year in the range via range(), so a span like
    Jan 2024 – Mar 2026 correctly fetches 2024, 2025, and 2026 files.
    Date filtering is applied after assembling the full multi-year pool.
    NWS active alerts are merged in to cover the NCEI publication lag.
    """
    try:
        index_html = _ncei_index()
    except Exception as exc:
        log.warning("NCEI index unavailable: %s", exc)
        return []

    records: list[dict] = []
    for year in range(start_date.year, end_date.year + 1):
        filename = find_ncei_filename(year, index_html)
        if not filename:
            log.warning("No NCEI file for year %d (not yet published)", year)
            continue
        try:
            year_records = _ncei_year(filename)
            records.extend(year_records)
        except Exception as exc:
            log.warning("NCEI year %d failed (%s): %s", year, filename, exc)

    # Apply date window across the assembled multi-year pool
    records = [r for r in records if start_date <= r["date"] <= end_date]

    # Merge NWS real-time alerts (fills the NCEI lag for the last few days)
    ncei_keys = {(r["lat"], r["lon"], str(r["date"])) for r in records}
    for alert in fetch_nws_alerts():
        key = (alert["lat"], alert["lon"], str(alert["date"]))
        if key not in ncei_keys and start_date <= alert["date"] <= end_date:
            records.append(alert)
            ncei_keys.add(key)

    log.info("Assembled %d records for %s → %s", len(records), start_date, end_date)
    return records


# ── Public interface ───────────────────────────────────────────────────────────

def get_storms(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> tuple[pd.DataFrame, str]:
    """
    Return storm events for the given date range as (DataFrame, source_label).
    source_label is "live" when NOAA data loads successfully, "mock" otherwise.

    Falls back to mock data when:
      • Any exception occurs during the live fetch
      • Live data returns fewer than _MIN_LIVE_RECORDS events (NCEI lag /
        no data yet published for that date range)
    """
    if start_date is None:
        start_date = date.today() - timedelta(days=90)
    if end_date is None:
        end_date = date.today()

    try:
        records = _assemble_live(start_date, end_date)

        if len(records) < _MIN_LIVE_RECORDS:
            log.warning(
                "Live data returned only %d records for %s → %s — "
                "falling back to mock data (NCEI may not have published yet).",
                len(records), start_date, end_date,
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
