"""
Homeowner lead data client.

# TODO: Replace mock data with real homeowner provider
# Recommended providers: ATTOM Data, BatchSkipTrace, DataTree
# Expected input: lat/lon + radius OR zip code list
# Expected output: same DataFrame schema as mock below

Public API:
    get_homeowners_in_zone(lat, lon, radius_miles, storm_date,
                           homes_affected, storm_type, storm_severity,
                           hail_size, wind_speed) -> pd.DataFrame
"""

import math
import random

import pandas as pd


# ── Name pools ──────────────────────────────────────────────────────────────────

_FIRST = [
    "James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael", "Linda",
    "William", "Barbara", "David", "Susan", "Richard", "Jessica", "Joseph", "Sarah",
    "Thomas", "Karen", "Charles", "Lisa", "Christopher", "Nancy", "Daniel", "Betty",
    "Matthew", "Margaret", "Anthony", "Sandra", "Mark", "Ashley", "Donald", "Dorothy",
    "Steven", "Kimberly", "Paul", "Emily", "Andrew", "Donna", "Joshua", "Michelle",
    "Kenneth", "Carol", "Kevin", "Amanda", "Brian", "Melissa", "George", "Deborah",
    "Edward", "Stephanie", "Ronald", "Rebecca", "Timothy", "Sharon", "Jason", "Laura",
    "Jeffrey", "Cynthia", "Ryan", "Kathleen", "Jacob", "Amy", "Gary", "Angela",
    "Nicholas", "Shirley", "Eric", "Anna", "Jonathan", "Brenda", "Stephen", "Pamela",
    "Larry", "Emma", "Justin", "Nicole", "Scott", "Helen", "Brandon", "Samantha",
    "Benjamin", "Katherine", "Samuel", "Christine", "Raymond", "Debra", "Gregory", "Rachel",
    "Frank", "Carolyn", "Alexander", "Janet", "Patrick", "Catherine", "Jack", "Maria",
    "Dennis", "Heather", "Jerry", "Diane", "Tyler", "Julie", "Aaron", "Joyce",
    "Jose", "Victoria", "Adam", "Ruth", "Nathan", "Virginia", "Henry", "Lauren",
    "Carlos", "Evelyn", "Sean", "Judith", "Alex", "Megan", "Kyle", "Andrea",
    "Luis", "Gloria", "Eric", "Teresa", "Dylan", "Hannah", "Juan", "Madison",
]

_LAST = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
    "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker",
    "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill",
    "Flores", "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell",
    "Mitchell", "Carter", "Roberts", "Turner", "Phillips", "Evans", "Collins", "Stewart",
    "Morris", "Morales", "Murphy", "Cook", "Rogers", "Gutierrez", "Ortiz", "Morgan",
    "Cooper", "Peterson", "Bailey", "Reed", "Kelly", "Howard", "Ramos", "Kim",
    "Cox", "Ward", "Richardson", "Watson", "Brooks", "Chavez", "Wood", "James",
    "Bennett", "Gray", "Mendoza", "Ruiz", "Hughes", "Price", "Alvarez", "Castillo",
    "Sanders", "Patel", "Myers", "Long", "Ross", "Foster", "Jimenez", "Powell",
    "Jenkins", "Perry", "Russell", "Sullivan", "Bell", "Coleman", "Butler", "Henderson",
    "Barnes", "Gonzales", "Fisher", "Vasquez", "Simmons", "Romero", "Jordan", "Patterson",
]

_STREET_NAMES = [
    "Oak", "Maple", "Cedar", "Pine", "Elm", "Magnolia", "Palm", "Cypress",
    "Sunset", "Lake", "River", "Bay", "Gulf", "Coral", "Sand", "Shore",
    "Jasmine", "Hibiscus", "Flamingo", "Pelican", "Heron", "Osprey", "Eagle",
    "Palmetto", "Coconut", "Mango", "Orchid", "Sawgrass", "Seagrass", "Banyan",
    "Royal", "Sunrise", "Horizon", "Harbor", "Marina", "Cove", "Inlet", "Ridge",
]

_STREET_SFXS = ["Dr", "St", "Ave", "Blvd", "Ln", "Ct", "Way", "Pl", "Rd", "Cir", "Ter"]

_EMAIL_DOMAINS = [
    "gmail.com", "yahoo.com", "outlook.com", "icloud.com", "hotmail.com",
    "aol.com", "comcast.net", "att.net", "bellsouth.net", "earthlink.net",
]

# ── City pool (city, state, zip_base, zip_offset_max) ───────────────────────────

_CITIES = [
    # Florida — largest coverage
    ("Miami",           "FL", 33101, 9),
    ("Orlando",         "FL", 32801, 35),
    ("Tampa",           "FL", 33601, 19),
    ("Jacksonville",    "FL", 32201, 77),
    ("Fort Lauderdale", "FL", 33301, 40),
    ("St. Petersburg",  "FL", 33701, 12),
    ("Tallahassee",     "FL", 32301, 16),
    ("Fort Myers",      "FL", 33901, 8),
    ("Sarasota",        "FL", 34230, 13),
    ("West Palm Beach", "FL", 33401, 20),
    ("Naples",          "FL", 34101, 20),
    ("Clearwater",      "FL", 33755, 12),
    ("Boca Raton",      "FL", 33427, 71),
    ("Gainesville",     "FL", 32601, 14),
    ("Pensacola",       "FL", 32501, 26),
    ("Daytona Beach",   "FL", 32114, 6),
    ("Cape Coral",      "FL", 33904, 14),
    ("Lakeland",        "FL", 33801, 16),
    ("Ocala",           "FL", 34470, 16),
    ("Hialeah",         "FL", 33002, 18),
    ("Coral Springs",   "FL", 33065, 10),
    ("Pompano Beach",   "FL", 33060, 8),
    # Georgia
    ("Atlanta",         "GA", 30301, 61),
    ("Savannah",        "GA", 31401, 15),
    ("Augusta",         "GA", 30901, 19),
    ("Columbus",        "GA", 31901, 10),
    # Alabama
    ("Birmingham",      "AL", 35201, 54),
    ("Mobile",          "AL", 36601, 18),
    ("Huntsville",      "AL", 35801, 16),
    # South Carolina
    ("Charleston",      "SC", 29401, 25),
    ("Myrtle Beach",    "SC", 29572, 10),
    ("Columbia",        "SC", 29201, 25),
    # North Carolina
    ("Charlotte",       "NC", 28201, 99),
    ("Raleigh",         "NC", 27601, 30),
    ("Wilmington",      "NC", 28401, 10),
]


# ── Public ──────────────────────────────────────────────────────────────────────

def get_homeowners_in_zone(
    lat: float,
    lon: float,
    radius_miles: float,
    storm_date,
    homes_affected: int,
    storm_type: str = "Hail",
    storm_severity: int = 2,
    hail_size: float | None = None,
    wind_speed: float | None = None,
) -> pd.DataFrame:
    """
    Return a DataFrame of homeowner leads for the given storm zone.

    Generates approximately one record per home affected, capped at 200.
    Uses a deterministic seed derived from lat/lon for reproducible output.

    # TODO: Replace mock data with real homeowner provider
    # Recommended providers: ATTOM Data, BatchSkipTrace, DataTree
    # Expected input: lat/lon + radius OR zip code list
    # Expected output: same DataFrame schema as mock below
    """
    _COLS = [
        "first_name", "last_name", "address", "city", "state", "zip_code",
        "phone", "email", "roof_age_years", "home_value", "owner_occupied",
        "storm_date", "storm_type", "storm_severity", "hail_size", "wind_speed",
        "lat", "lon",
    ]

    n = min(max(homes_affected, 0), 200)
    if n == 0:
        return pd.DataFrame(columns=_COLS)

    # Reproducible seed so re-renders don't shuffle the list
    seed = int(abs(lat * 10_000) + abs(lon * 10_000)) % (2 ** 31)
    rng = random.Random(seed)

    records = []
    for _ in range(n):
        first = rng.choice(_FIRST)
        last  = rng.choice(_LAST)
        city, state, zip_base, zip_max = rng.choice(_CITIES)
        zip_code = str(zip_base + rng.randint(0, zip_max)).zfill(5)
        address  = (
            f"{rng.randint(100, 9999)} "
            f"{rng.choice(_STREET_NAMES)} "
            f"{rng.choice(_STREET_SFXS)}"
        )
        area  = rng.randint(200, 999)
        phone = f"({area}) {rng.randint(200, 999)}-{rng.randint(1000, 9999)}"
        email = (
            f"{first.lower()}.{last.lower()}{rng.randint(1, 99)}"
            f"@{rng.choice(_EMAIL_DOMAINS)}"
        )
        roof_age   = rng.randint(1, 30)
        home_value = rng.randint(180, 850) * 1_000
        owner_occ  = rng.random() < 0.72

        # Scatter point within radius (uniform disk sampling)
        r     = radius_miles * math.sqrt(rng.random())
        theta = rng.uniform(0, 2 * math.pi)
        dlat  = r / 69.0
        dlon  = r / (69.0 * math.cos(math.radians(lat)))
        plat  = round(lat + dlat * math.cos(theta), 6)
        plon  = round(lon + dlon * math.sin(theta), 6)

        records.append({
            "first_name":     first,
            "last_name":      last,
            "address":        address,
            "city":           city,
            "state":          state,
            "zip_code":       zip_code,
            "phone":          phone,
            "email":          email,
            "roof_age_years": roof_age,
            "home_value":     home_value,
            "owner_occupied": owner_occ,
            "storm_date":     storm_date,
            "storm_type":     storm_type,
            "storm_severity": storm_severity,
            "hail_size":      hail_size,
            "wind_speed":     wind_speed,
            "lat":            plat,
            "lon":            plon,
        })

    return pd.DataFrame(records)
