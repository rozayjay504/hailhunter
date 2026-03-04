"""
NOAA data clients for Phase 2.

Two sources — both free, no token required:

  1. NCEI Storm Events CSV
       https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/
       Annual gzip-CSV files with every NWS-reported storm event.
       Covers hail (size in inches), wind (speed in knots), hurricanes,
       tropical storms, with lat/lon, county, damage, and narratives.

  2. NWS Active Alerts API
       https://api.weather.gov/alerts
       Real-time GeoJSON alerts from the National Weather Service.
       Supplements NCEI with events from the last 1–7 days that haven't
       yet been ingested into the annual CSV files.

The NOAA CDO API token (NOAA_TOKEN env var) is wired in but not consumed
here in Phase 2. It is reserved for Phase 3 station-level climate queries
via https://www.ncdc.noaa.gov/cdo-web/api/v2/ — e.g. housing density,
roof-age proxies from building permit data, and zone statistics.
"""

import csv
import gzip
import io
import logging
import os
import re
from datetime import date
from typing import Optional

import requests
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger(__name__)

# Reserved for Phase 3 CDO queries — not used in Phase 2 data fetching
NOAA_TOKEN: str = os.getenv("NOAA_TOKEN", "")

NCEI_INDEX_URL = "https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/"
NWS_ALERTS_URL = "https://api.weather.gov/alerts"

TIMEOUT_INDEX = 20   # seconds — directory listing
TIMEOUT_CSV   = 180  # seconds — annual CSV can be 30–80 MB compressed
TIMEOUT_NWS   = 20

KNOTS_TO_MPH = 1.15078  # NCEI stores wind magnitude in knots

# ── Event-type mappings ────────────────────────────────────────────────────────

# NCEI EVENT_TYPE column → our schema (None = skip this event type)
NCEI_TYPE_MAP: dict[str, Optional[str]] = {
    "Hail":                       "Hail",
    "Thunderstorm Wind":          "Wind",
    "High Wind":                  "Wind",
    "Strong Wind":                "Wind",
    "Marine Strong Wind":         "Wind",
    "Marine High Wind":           "Wind",
    "Marine Thunderstorm Wind":   "Wind",
    "Hurricane (Typhoon)":        "Hurricane",
    "Hurricane":                  "Hurricane",
    "Tropical Storm":             "Tropical Storm",
    "Tropical Depression":        "Tropical Storm",
}

# NWS alert `event` label → our schema
NWS_TYPE_MAP: dict[str, str] = {
    "Severe Thunderstorm Warning":  "Wind",
    "Severe Thunderstorm Watch":    "Wind",
    "High Wind Warning":            "Wind",
    "High Wind Watch":              "Wind",
    "Extreme Wind Warning":         "Wind",
    "Wind Advisory":                "Wind",
    "Hurricane Warning":            "Hurricane",
    "Hurricane Watch":              "Hurricane",
    "Hurricane Local Statement":    "Hurricane",
    "Tropical Storm Warning":       "Tropical Storm",
    "Tropical Storm Watch":         "Tropical Storm",
}

# NCEI STATE column (full caps) → 2-letter abbreviation
STATE_ABBREV: dict[str, str] = {
    "ALABAMA": "AL", "ALASKA": "AK", "ARIZONA": "AZ", "ARKANSAS": "AR",
    "CALIFORNIA": "CA", "COLORADO": "CO", "CONNECTICUT": "CT", "DELAWARE": "DE",
    "FLORIDA": "FL", "GEORGIA": "GA", "HAWAII": "HI", "IDAHO": "ID",
    "ILLINOIS": "IL", "INDIANA": "IN", "IOWA": "IA", "KANSAS": "KS",
    "KENTUCKY": "KY", "LOUISIANA": "LA", "MAINE": "ME", "MARYLAND": "MD",
    "MASSACHUSETTS": "MA", "MICHIGAN": "MI", "MINNESOTA": "MN", "MISSISSIPPI": "MS",
    "MISSOURI": "MO", "MONTANA": "MT", "NEBRASKA": "NE", "NEVADA": "NV",
    "NEW HAMPSHIRE": "NH", "NEW JERSEY": "NJ", "NEW MEXICO": "NM", "NEW YORK": "NY",
    "NORTH CAROLINA": "NC", "NORTH DAKOTA": "ND", "OHIO": "OH", "OKLAHOMA": "OK",
    "OREGON": "OR", "PENNSYLVANIA": "PA", "RHODE ISLAND": "RI", "SOUTH CAROLINA": "SC",
    "SOUTH DAKOTA": "SD", "TENNESSEE": "TN", "TEXAS": "TX", "UTAH": "UT",
    "VERMONT": "VT", "VIRGINIA": "VA", "WASHINGTON": "WA", "WEST VIRGINIA": "WV",
    "WISCONSIN": "WI", "WYOMING": "WY", "DISTRICT OF COLUMBIA": "DC",
    "PUERTO RICO": "PR", "VIRGIN ISLANDS": "VI", "AMERICAN SAMOA": "AS",
    "GUAM": "GU", "HAWAII WATERS": "HI",
    # Marine/lake zones — map to nearest state for display purposes
    "ATLANTIC NORTH": "NC", "ATLANTIC SOUTH": "FL", "GULF OF MEXICO": "LA",
    "LAKE MICHIGAN": "IL", "LAKE SUPERIOR": "MN", "LAKE HURON": "MI",
    "LAKE ERIE": "OH", "LAKE ONTARIO": "NY",
}


# ── Severity + geometry helpers ────────────────────────────────────────────────

def _hail_severity(inches: float) -> int:
    if inches < 1.00: return 1
    if inches < 1.50: return 2
    if inches < 2.00: return 3
    return 4


def _wind_severity(mph: float) -> int:
    if mph < 60: return 1
    if mph < 75: return 2
    if mph < 90: return 3
    return 4


def _radius_miles(severity: int, event_type: str) -> float:
    base = {1: 5.0, 2: 8.0, 3: 12.0, 4: 18.0}[severity]
    return round(base * (2.5 if event_type in ("Hurricane", "Tropical Storm") else 1.0), 1)


def _parse_damage_usd(s: str) -> float:
    """Parse NCEI damage strings like '10.00K', '1.50M', '250B' → float USD."""
    if not s:
        return 0.0
    s = s.strip().upper()
    mult = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}.get(s[-1], 1)
    try:
        return float(re.sub(r"[KMBkmb]$", "", s)) * mult
    except ValueError:
        return 0.0


def _damage_to_homes(damage_usd: float, event_type: str, severity: int) -> int:
    """Estimate number of affected homes from property damage amount."""
    if damage_usd > 0:
        # Rough average roofing claim by event type
        avg_claim = {
            "Hail": 12_000, "Wind": 8_000,
            "Hurricane": 25_000, "Tropical Storm": 10_000,
        }
        return max(10, int(damage_usd / avg_claim.get(event_type, 10_000)))
    # Fallback: estimate from severity tier
    return {1: 200, 2: 600, 3: 1_200, 4: 3_000}[severity]


def _parse_ncei_date(s: str) -> Optional[date]:
    """
    Parse NCEI BEGIN_DATE_TIME.
    Observed formats: 'M/D/YYYY H:MM:SS'  or  'YYYY-MM-DDTHH:MM:SS'
    """
    if not s:
        return None
    s = s.strip()
    try:
        date_part = s.split()[0]           # drop time component
        if "/" in date_part:
            m, d, y = date_part.split("/")
            return date(int(y), int(m), int(d))
        return date.fromisoformat(date_part[:10])
    except Exception:
        return None


# ── NCEI Storm Events CSV ──────────────────────────────────────────────────────

def _find_csv_filename(year: int, index_html: str) -> Optional[str]:
    """
    Scan the NCEI directory listing HTML for the latest details file for a year.
    NCEI filenames: StormEvents_details-ftp_v1.0_d{YEAR}_c{CREATED}.gz
    Multiple versions may exist; we take the highest (latest) creation date.
    """
    pattern = rf"StormEvents_details-ftp_v1\.0_d{year}_c\d+\.gz"
    matches = re.findall(pattern, index_html)
    return sorted(matches)[-1] if matches else None


def _ncei_row_to_record(row: dict, event_type: str) -> Optional[dict]:
    """
    Normalize one NCEI CSV row into our schema dict.
    Returns None to discard the row (missing coords, sub-threshold, parse error).
    """
    try:
        lat_s = row.get("BEGIN_LAT", "").strip()
        lon_s = row.get("BEGIN_LON", "").strip()
        if not lat_s or not lon_s:
            return None  # skip county-level events with no precise coords
        lat, lon = float(lat_s), float(lon_s)
        if lat == 0.0 and lon == 0.0:
            return None

        event_date = _parse_ncei_date(row.get("BEGIN_DATE_TIME", ""))
        if event_date is None:
            return None

        mag_s = row.get("MAGNITUDE", "").strip()
        magnitude = float(mag_s) if mag_s else None

        hail_size: Optional[float] = None
        wind_speed: Optional[float] = None

        if event_type == "Hail":
            # NCEI MAGNITUDE for hail = diameter in inches
            if magnitude is None or magnitude < 0.75:
                return None  # below reportable threshold
            hail_size = round(magnitude, 2)
            severity = _hail_severity(hail_size)

        else:
            # NCEI MAGNITUDE for wind = speed in knots → convert to mph
            if magnitude is not None:
                wind_speed = round(magnitude * KNOTS_TO_MPH, 1)

            # Hurricanes: use CATEGORY (Saffir-Simpson 1–5) for severity if present
            cat_s = row.get("CATEGORY", "").strip()
            if event_type == "Hurricane" and cat_s:
                try:
                    severity = min(4, max(1, int(float(cat_s))))
                except ValueError:
                    severity = _wind_severity(wind_speed or 0)
            else:
                severity = _wind_severity(wind_speed or 0)

            # Tropical storms: clamp to 2–3 (never catastrophic by definition here)
            if event_type == "Tropical Storm":
                severity = min(3, max(2, severity))

        damage_usd = _parse_damage_usd(row.get("DAMAGE_PROPERTY", ""))
        homes = _damage_to_homes(damage_usd, event_type, severity)

        state = STATE_ABBREV.get(
            row.get("STATE", "").strip().upper(),
            row.get("STATE", "")[:2].upper(),
        )
        city   = (row.get("BEGIN_LOCATION") or "").strip().title()
        county = (row.get("CZ_NAME") or "").strip().title()
        if not city:
            city = county  # fall back to county/zone name

        narrative = (
            row.get("EVENT_NARRATIVE") or row.get("EPISODE_NARRATIVE") or ""
        ).strip()
        description = (
            narrative[:120]
            if narrative
            else f"{event_type} event in {city or county}, {state}"
        )

        return {
            "event_id":      f"NCEI-{row.get('EVENT_ID', '').strip()}",
            "event_type":    event_type,
            "severity":      severity,
            "hail_size":     hail_size,
            "wind_speed":    wind_speed,
            "lat":           round(lat, 4),
            "lon":           round(lon, 4),
            "city":          city or county or "Unknown",
            "state":         state,
            "county":        county or city or "Unknown",
            "date":          event_date,
            "homes_affected": homes,
            # Phase 3: enrich avg_roof_age and owner_pct from Census ACS data
            "avg_roof_age":  20,
            "owner_pct":     0.55,
            "radius_miles":  _radius_miles(severity, event_type),
            "description":   description,
        }
    except Exception as exc:
        log.debug("Skipping NCEI row (EVENT_ID=%s): %s", row.get("EVENT_ID"), exc)
        return None


def fetch_ncei_storms(start_date: date, end_date: date) -> list[dict]:
    """
    Download NCEI Storm Events detail CSV files for all years in [start_date, end_date]
    and return records normalized to our schema.

    Files are 30–80 MB compressed. Streamlit's @st.cache_data in pipeline.py
    ensures this download only happens once per 6-hour window.
    """
    try:
        resp = requests.get(NCEI_INDEX_URL, timeout=TIMEOUT_INDEX)
        resp.raise_for_status()
        index_html = resp.text
    except Exception as exc:
        log.warning("NCEI index fetch failed: %s", exc)
        return []

    records: list[dict] = []
    years = sorted({start_date.year, end_date.year})

    for year in years:
        filename = _find_csv_filename(year, index_html)
        if not filename:
            log.warning("No NCEI details file found for year %d (may not be published yet)", year)
            continue

        url = NCEI_INDEX_URL + filename
        log.info("Downloading NCEI storm events: %s", url)
        try:
            csv_resp = requests.get(url, timeout=TIMEOUT_CSV)
            csv_resp.raise_for_status()
        except Exception as exc:
            log.warning("NCEI download failed (%s): %s", filename, exc)
            continue

        try:
            with gzip.open(io.BytesIO(csv_resp.content)) as gz:
                reader = csv.DictReader(io.TextIOWrapper(gz, encoding="latin-1"))
                for row in reader:
                    et = NCEI_TYPE_MAP.get(row.get("EVENT_TYPE", ""))
                    if et is None:
                        continue
                    record = _ncei_row_to_record(row, et)
                    if record is None:
                        continue
                    if not (start_date <= record["date"] <= end_date):
                        continue
                    records.append(record)
        except Exception as exc:
            log.warning("NCEI parse error (%s): %s", filename, exc)

    log.info("NCEI: %d records for %s → %s", len(records), start_date, end_date)
    return records


# ── NWS Active Alerts ──────────────────────────────────────────────────────────

def fetch_nws_alerts() -> list[dict]:
    """
    Fetch active NWS severe weather alerts (GeoJSON).
    Covers the last 1–7 days — supplements NCEI for very recent events
    that haven't yet been added to the annual CSV files.
    Returns an empty list on any failure (non-critical path).
    """
    try:
        resp = requests.get(
            NWS_ALERTS_URL,
            params={"status": "actual", "message_type": "alert"},
            headers={"User-Agent": "HailHunter/2.0 (github.com/rozayjay504/hailhunter)"},
            timeout=TIMEOUT_NWS,
        )
        resp.raise_for_status()
        features = resp.json().get("features", [])
    except Exception as exc:
        log.warning("NWS Alerts fetch failed: %s", exc)
        return []

    records: list[dict] = []
    for feat in features:
        props = feat.get("properties", {})
        et = NWS_TYPE_MAP.get(props.get("event", ""))
        if et is None:
            continue

        # Extract centroid from polygon or point geometry
        geom = feat.get("geometry")
        lat = lon = None
        if geom:
            if geom["type"] == "Polygon":
                coords = geom["coordinates"][0]
                lat = round(sum(c[1] for c in coords) / len(coords), 4)
                lon = round(sum(c[0] for c in coords) / len(coords), 4)
            elif geom["type"] == "Point":
                lon = round(geom["coordinates"][0], 4)
                lat = round(geom["coordinates"][1], 4)
        if lat is None:
            continue

        try:
            onset = props.get("onset") or props.get("effective") or ""
            event_date = date.fromisoformat(onset[:10])
        except Exception:
            event_date = date.today()

        severity_label = (props.get("severity") or "Minor").lower()
        severity = {"minor": 1, "moderate": 2, "severe": 3, "extreme": 4}.get(
            severity_label, 2
        )

        area_desc = (props.get("areaDesc") or "")[:60]
        description = (
            props.get("headline") or props.get("description") or props.get("event", et)
        )[:120].strip()

        records.append({
            "event_id":      f"NWS-{feat.get('id', '')[-16:]}",
            "event_type":    et,
            "severity":      severity,
            "hail_size":     None,
            "wind_speed":    None,
            "lat":           lat,
            "lon":           lon,
            "city":          area_desc or "Active Alert",
            "state":         "US",
            "county":        area_desc or "Active Alert",
            "date":          event_date,
            "homes_affected": {1: 200, 2: 600, 3: 1_200, 4: 3_000}[severity],
            "avg_roof_age":  20,
            "owner_pct":     0.55,
            "radius_miles":  _radius_miles(severity, et),
            "description":   description,
        })

    log.info("NWS Alerts: %d records", len(records))
    return records
