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

# NCEI MAGNITUDE for wind is recorded in the units used by the reporting
# office — in practice the Storm Events database values align with mph
# (NWS warning thresholds are stated in mph: 58 mph = severe thunderstorm).
# We do NOT apply a knots conversion; doing so inflates typical 55–75 mph
# events by 15 % and pushes most into severity 3, collapsing the color range.

# ── Event-type mappings ────────────────────────────────────────────────────────

# NCEI EVENT_TYPE column → our schema (None = skip this event type)
NCEI_TYPE_MAP: dict[str, Optional[str]] = {
    "Hail":                       "Hail",
    "Marine Hail":                "Hail",
    "Thunderstorm Wind":          "Wind",
    "High Wind":                  "Wind",
    "Strong Wind":                "Wind",
    "Tornado":                    "Wind",
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

# NCEI STATE column → 2-letter abbreviation.
# Keys are title-cased to match .title() normalization applied at lookup time
# (NCEI sends ALL CAPS; row.get("STATE").strip().title() normalises both).
STATE_ABBREV: dict[str, str] = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR",
    "California": "CA", "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE",
    "Florida": "FL", "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID",
    "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS",
    "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
    "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS",
    "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV",
    "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY",
    "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK",
    "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC",
    "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT",
    "Vermont": "VT", "Virginia": "VA", "Washington": "WA", "West Virginia": "WV",
    "Wisconsin": "WI", "Wyoming": "WY", "District Of Columbia": "DC",
    "Puerto Rico": "PR", "Virgin Islands": "VI", "American Samoa": "AS",
    "Guam": "GU", "Hawaii Waters": "HI",
    # Marine/lake zones — map to nearest state for display purposes
    "Atlantic North": "NC", "Atlantic South": "FL", "Gulf Of Mexico": "LA",
    "Lake Michigan": "IL", "Lake Superior": "MN", "Lake Huron": "MI",
    "Lake Erie": "OH", "Lake Ontario": "NY",
}

# Geographic center of each state — used as lat/lon fallback when NCEI
# omits BEGIN_LAT/BEGIN_LON (county/zone-level events with no point data).
STATE_CENTROIDS: dict[str, tuple[float, float]] = {
    "AL": (32.799, -86.807), "AK": (64.201, -153.494), "AZ": (34.274, -111.660),
    "AR": (34.894, -92.443), "CA": (37.184, -119.470), "CO": (38.997, -105.548),
    "CT": (41.622, -72.727), "DE": (39.318, -75.507), "FL": (28.631, -82.450),
    "GA": (32.641, -83.443), "HI": (20.293, -156.374), "ID": (44.351, -114.613),
    "IL": (40.042, -89.197), "IN": (39.894, -86.282), "IA": (42.075, -93.496),
    "KS": (38.494, -98.380), "KY": (37.535, -85.302), "LA": (31.069, -91.997),
    "ME": (45.370, -69.243), "MD": (39.055, -76.791), "MA": (42.260, -71.808),
    "MI": (44.347, -85.410), "MN": (46.281, -94.305), "MS": (32.736, -89.668),
    "MO": (38.357, -92.458), "MT": (47.053, -109.633), "NE": (41.538, -99.795),
    "NV": (39.329, -116.631), "NH": (43.681, -71.581), "NJ": (40.191, -74.673),
    "NM": (34.407, -106.113), "NY": (42.954, -75.527), "NC": (35.556, -79.388),
    "ND": (47.450, -100.466), "OH": (40.286, -82.794), "OK": (35.589, -97.494),
    "OR": (43.934, -120.558), "PA": (40.878, -77.800), "RI": (41.676, -71.556),
    "SC": (33.917, -80.896), "SD": (44.444, -100.226), "TN": (35.858, -86.351),
    "TX": (31.476, -99.331), "UT": (39.306, -111.094), "VT": (44.069, -72.666),
    "VA": (37.521, -78.854), "WA": (47.383, -120.447), "WV": (38.641, -80.623),
    "WI": (44.624, -89.994), "WY": (42.996, -107.551), "DC": (38.904, -77.017),
    "PR": (18.221, -66.590),
}


# ── Severity + geometry helpers ────────────────────────────────────────────────

def _hail_severity(inches: float) -> int:
    # 1 — Minor      < 1.00"  pea / dime       cosmetic damage only
    # 2 — Moderate   < 1.75"  quarter–ping pong moderate shingle damage
    # 3 — Severe     < 2.50"  golf–tennis ball  significant damage
    # 4 — Catastrophic ≥ 2.50" baseball+        full replacement needed
    if inches < 1.00: return 1
    if inches < 1.75: return 2
    if inches < 2.50: return 3
    return 4


def _wind_severity(mph: float) -> int:
    # Bands aligned to NWS damage tiers (values treated as mph):
    # 1 — Minor      < 58 mph  below severe thunderstorm threshold
    # 2 — Moderate   < 75 mph  severe thunderstorm / high-wind warning range
    # 3 — Severe     < 100 mph significant structural / roofing damage
    # 4 — Catastrophic ≥ 100 mph hurricane-force / extreme wind
    if mph < 58:  return 1
    if mph < 75:  return 2
    if mph < 100: return 3
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

def find_ncei_filename(year: int, index_html: str) -> Optional[str]:
    """
    Scan the NCEI directory listing HTML for the latest details file for a year.
    NCEI filenames: StormEvents_details-ftp_v1.0_d{YEAR}_c{CREATED}.gz
    Multiple versions may exist; we take the highest creation date (last sorted).
    The creation-date suffix acts as a natural cache-buster in pipeline.py:
    if NCEI re-publishes a year's file, the new filename produces a new cache key.
    """
    all_detail_files = re.findall(r"StormEvents_details[^\s\"'<>]+\.gz", index_html)
    matches = [f for f in all_detail_files if f"_d{year}_" in f]
    return sorted(matches)[-1] if matches else None


def fetch_ncei_index_html() -> str:
    """Fetch the raw HTML of the NCEI storm-events CSV directory listing."""
    resp = requests.get(NCEI_INDEX_URL, timeout=TIMEOUT_INDEX)
    resp.raise_for_status()
    return resp.text


def fetch_ncei_year_records(filename: str) -> list[dict]:
    """
    Download and fully parse one annual NCEI Storm Events detail CSV.

    Returns ALL relevant records for the year with no date filtering —
    the caller (pipeline.py) applies the date window after assembling
    records from one or more cached annual files.

    filename: exact name from the NCEI index, e.g.
              'StormEvents_details-ftp_v1.0_d2025_c20260301.gz'
    """
    url = NCEI_INDEX_URL + filename
    log.info("Downloading NCEI: %s", url)
    resp = requests.get(url, timeout=TIMEOUT_CSV)
    resp.raise_for_status()

    records: list[dict] = []
    try:
        with gzip.open(io.BytesIO(resp.content)) as gz:
            reader = csv.DictReader(io.TextIOWrapper(gz, encoding="latin-1"))
            for row in reader:
                et = NCEI_TYPE_MAP.get(row.get("EVENT_TYPE", ""))
                if et is None:
                    continue
                record = _ncei_row_to_record(row, et)
                if record is not None:
                    records.append(record)
    except Exception as exc:
        log.warning("NCEI parse error (%s): %s", filename, exc)

    log.info("NCEI %s: %d relevant records parsed", filename, len(records))
    return records


def _ncei_row_to_record(row: dict, event_type: str) -> Optional[dict]:
    """
    Normalize one NCEI CSV row into our schema dict.
    Returns None to discard the row (missing coords, sub-threshold, parse error).
    """
    try:
        lat_s = row.get("BEGIN_LAT", "").strip()
        lon_s = row.get("BEGIN_LON", "").strip()
        lat = lon = None
        if lat_s and lon_s:
            try:
                lat, lon = float(lat_s), float(lon_s)
                if lat == 0.0 and lon == 0.0:
                    lat = lon = None
            except ValueError:
                pass
        if lat is None:
            # Fall back to state centroid for county/zone-level events
            state_key = STATE_ABBREV.get(row.get("STATE", "").strip().title(), "")
            centroid = STATE_CENTROIDS.get(state_key)
            if centroid is None:
                return None
            lat, lon = centroid

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
            # NCEI MAGNITUDE for wind — used directly as mph (see note above)
            if magnitude is not None:
                wind_speed = round(magnitude, 1)

            # Hurricanes: use CATEGORY (Saffir-Simpson 1–5) for severity if present
            cat_s = row.get("CATEGORY", "").strip()
            if event_type == "Hurricane" and cat_s:
                try:
                    severity = min(4, max(1, int(float(cat_s))))
                except ValueError:
                    severity = _wind_severity(wind_speed or 0)
            elif row.get("EVENT_TYPE") == "Tornado":
                # MAGNITUDE is typically null for tornadoes; use EF/F scale instead
                tor = row.get("TOR_F_SCALE", "").strip()
                m = re.search(r"\d", tor)
                ef = int(m.group()) if m else 2  # unknown → assume EF2
                severity = 4 if ef >= 4 else (3 if ef >= 2 else 2)
            else:
                severity = _wind_severity(wind_speed or 0)

            # Tropical storms: clamp to 2–3 (never catastrophic by definition here)
            if event_type == "Tropical Storm":
                severity = min(3, max(2, severity))

        damage_usd = _parse_damage_usd(row.get("DAMAGE_PROPERTY", ""))
        homes = _damage_to_homes(damage_usd, event_type, severity)

        state = STATE_ABBREV.get(
            row.get("STATE", "").strip().title(),
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
