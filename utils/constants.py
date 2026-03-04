# Severity levels → display properties
SEVERITY_COLORS = {
    1: "#FFC107",   # Minor        — yellow
    2: "#FF6B35",   # Moderate     — orange
    3: "#EF4444",   # Severe       — red
    4: "#9333EA",   # Catastrophic — purple
}

SEVERITY_LABELS = {
    1: "Minor",
    2: "Moderate",
    3: "Severe",
    4: "Catastrophic",
}

SEVERITY_RADIUS = {
    1: 10,
    2: 14,
    3: 20,
    4: 28,
}

# Storm types (order matches UI)
STORM_TYPES = ["Hail", "Wind", "Hurricane", "Tropical Storm"]

# Hail diameter scale (inches → common name)
HAIL_SIZE_MARKS = {
    0.75: "Pea",
    1.00: "Dime",
    1.25: "Quarter",
    1.50: "Half Dollar",
    1.75: "Ping Pong",
    2.00: "Golf Ball",
    2.50: "Tennis Ball",
    3.00: "Baseball+",
}

HAIL_SIZE_MIN = 0.75
HAIL_SIZE_MAX = 3.00

# Region definitions — state lists and map viewport per region
REGIONS: dict[str, list[str]] = {
    "Southeast": ["FL", "TX", "LA", "MS", "AL", "GA", "NC", "SC"],
    "Northeast": ["NY", "PA", "NJ", "CT", "MA", "RI", "VT", "NH", "ME", "MD", "DE"],
    "Midwest":   ["IL", "IN", "OH", "MI", "WI", "MN", "IA", "MO", "ND", "SD", "NE", "KS"],
    "Southwest": ["AZ", "NM", "NV", "UT", "CO"],
    "Northwest": ["WA", "OR", "ID", "MT", "WY"],
    "All States": [],
}

REGION_MAP_CONFIG: dict[str, dict] = {
    "Southeast": {"center": [32.5,  -83.5],  "zoom": 6},
    "Northeast": {"center": [42.5,  -74.0],  "zoom": 6},
    "Midwest":   {"center": [41.5,  -93.0],  "zoom": 5},
    "Southwest": {"center": [36.0, -111.0],  "zoom": 6},
    "Northwest": {"center": [46.0, -116.0],  "zoom": 6},
    "All States": {"center": [38.0,  -96.0], "zoom": 4},
}

# Maximum storm events rendered on the map at once
MAP_EVENT_CAP = 500

# Map defaults
MAP_CENTER = [39.5, -98.35]
MAP_ZOOM = 5

# Dark tile URL (CartoDB DarkMatter)
MAP_TILE_URL = (
    "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
)
MAP_TILE_ATTR = (
    "&copy; <a href='https://www.openstreetmap.org/copyright'>OpenStreetMap</a>"
    " contributors &copy; <a href='https://carto.com/attributions'>CARTO</a>"
)
