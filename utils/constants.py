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
