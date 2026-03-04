# ⚡ HailHunter

> Storm Intelligence Platform for Roofing Lead Generation

HailHunter is a dark-themed, professional storm intelligence dashboard used internally to identify homeowners affected by hail, wind, and storm events and turn them into roofing leads.

---

## Tech Stack

| Layer | Technology |
|---|---|
| UI | Python + Streamlit |
| Maps | Folium + streamlit-folium |
| Charts | Plotly |
| Data | NOAA Storm Events API + OpenWeather API |
| Processing | pandas + geopandas |
| PDF Export | ReportLab |
| Deployment | Streamlit Community Cloud |

---

## Project Structure

```
hailhunter/
├── app.py                    # Main entry point
├── requirements.txt
├── .streamlit/
│   └── config.toml           # Dark theme + server config
├── components/
│   ├── filters.py            # Sidebar filter widgets
│   └── map.py                # Folium map builder
├── data/
│   └── mock_storms.py        # Phase 1 mock data / Phase 2+ API clients
└── utils/
    └── constants.py          # Shared constants (colors, sizes, map defaults)
```

---

## Setup

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/hailhunter.git
cd hailhunter

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run
streamlit run app.py
```

---

## Build Phases

| Phase | Status | Description |
|---|---|---|
| 1 | ✅ Complete | Map shell — dark UI, sidebar filters, mock storm overlays |
| 2 | Planned | Live data — NOAA + OpenWeather API integration |
| 3 | Planned | Selection tools + zone intelligence panel |
| 4 | Planned | Time slider + animated storm playback |
| 5 | Planned | CSV, PDF, and GHL export |
| 6 | Planned | Saved zones, alerts, zone comparison |

---

## Features (Phase 1)

- **Full-screen interactive map** centered on the US with CartoDB DarkMatter tile layer
- **45 mock storm events** across the US covering the last 90 days
- **Color-coded severity overlays**: yellow (minor) → orange (moderate) → red (severe) → purple (catastrophic)
- **Clickable markers** with rich popups showing city, date, hail size, homes affected, roof age, and owner occupancy
- **Left sidebar filters**: storm type, hail size, date range with presets, roof age range, occupancy, min severity
- **Floating selection toolbar** placeholder (Draw Polygon, Pin + Radius, Zip Code, County/City, Select All)
- **Severity legend** overlaid on map
- **Live event count badge** updates as filters change

---

## Storm Severity Scale

| Level | Color | Label |
|---|---|---|
| 1 | 🟡 Yellow | Minor |
| 2 | 🟠 Orange | Moderate |
| 3 | 🔴 Red | Severe |
| 4 | 🟣 Purple | Catastrophic |

---

## Environment Variables (Phase 2+)

```bash
NOAA_TOKEN=your_noaa_api_token
OPENWEATHER_API_KEY=your_openweather_key
GHL_API_KEY=your_gohighlevel_api_key      # Phase 5
```
