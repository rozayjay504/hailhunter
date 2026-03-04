"""
Folium map builder.

build_map(df) is the single public function — it takes a filtered storm
DataFrame and returns a configured folium.Map ready for st_folium().
"""

import folium
import pandas as pd
from branca.element import MacroElement
from jinja2 import Template

from utils.constants import (
    MAP_CENTER, MAP_ZOOM, MAP_TILE_URL, MAP_TILE_ATTR,
    SEVERITY_COLORS, SEVERITY_LABELS, SEVERITY_RADIUS,
)


# ── Public ─────────────────────────────────────────────────────────────────────

def build_map(df: pd.DataFrame) -> folium.Map:
    """Build and return a fully configured dark Folium map with storm overlays."""

    m = folium.Map(
        location=MAP_CENTER,
        zoom_start=MAP_ZOOM,
        tiles=None,
        prefer_canvas=True,
        zoom_control=True,
    )

    # Dark tile layer
    folium.TileLayer(
        tiles=MAP_TILE_URL,
        attr=MAP_TILE_ATTR,
        name="Dark Map",
        max_zoom=20,
        control=False,
    ).add_to(m)

    # Storm markers
    _add_storm_markers(m, df)

    # UI overlays (injected into map iframe HTML)
    _add_legend(m)
    _add_toolbar(m)

    return m


# ── Private ────────────────────────────────────────────────────────────────────

def _add_storm_markers(m: folium.Map, df: pd.DataFrame) -> None:
    """Add a CircleMarker for every storm event in the DataFrame."""
    for _, row in df.iterrows():
        severity = max(1, min(4, int(row["severity"])))  # clamp 1–4 defensively
        color = SEVERITY_COLORS[severity]
        radius = SEVERITY_RADIUS[severity]

        # Build popup HTML
        popup_html = _popup_html(row)
        tooltip_text = f"{row['city']}, {row['state']} — {row['event_type']} ({SEVERITY_LABELS[severity]})"

        folium.CircleMarker(
            location=[row["lat"], row["lon"]],
            radius=radius,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.35,
            weight=2,
            opacity=0.9,
            popup=folium.Popup(popup_html, max_width=280),
            tooltip=folium.Tooltip(tooltip_text, style=(
                "background-color:#0D1117; color:#E5E7EB; "
                "border:1px solid rgba(255,255,255,0.1); "
                "border-radius:4px; font-size:12px; padding:4px 8px;"
            )),
        ).add_to(m)


def _popup_html(row: pd.Series) -> str:
    """Return styled HTML string for a marker popup."""
    color = SEVERITY_COLORS[row["severity"]]
    sev_label = SEVERITY_LABELS[row["severity"]]

    # Hail size line (only for Hail events)
    hail_line = ""
    if row["event_type"] == "Hail" and pd.notna(row.get("hail_size")):
        hail_line = f'<div class="pp-row"><span class="pp-key">Hail Size</span><span class="pp-val">{row["hail_size"]:.2f}"</span></div>'

    # Wind speed line (for wind/hurricane/tropical events)
    wind_line = ""
    if row["event_type"] != "Hail" and pd.notna(row.get("wind_speed")):
        wind_line = f'<div class="pp-row"><span class="pp-key">Wind Speed</span><span class="pp-val">{int(row["wind_speed"])} mph</span></div>'

    date_str = row["date"].strftime("%b %d, %Y") if hasattr(row["date"], "strftime") else str(row["date"])
    owner_pct = int(row["owner_pct"] * 100)

    return f"""
    <div style="
        background:#111827; color:#E5E7EB;
        padding:14px 16px; border-radius:8px;
        min-width:230px; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
        border-top:3px solid {color};
    ">
        <style>
            .pp-title{{font-size:14px;font-weight:700;margin-bottom:3px;}}
            .pp-meta{{font-size:10px;color:#9CA3AF;letter-spacing:.05em;margin-bottom:10px;text-transform:uppercase;}}
            .pp-row{{display:flex;justify-content:space-between;font-size:12px;padding:3px 0;border-bottom:1px solid rgba(255,255,255,0.05);}}
            .pp-key{{color:#9CA3AF;}}
            .pp-val{{color:#E5E7EB;font-weight:600;}}
            .pp-sev{{display:inline-block;padding:2px 8px;border-radius:12px;font-size:10px;font-weight:700;background:{color}22;color:{color};border:1px solid {color}55;}}
        </style>
        <div class="pp-title">{row['city']}, {row['state']}</div>
        <div class="pp-meta">{date_str} &middot; {row['event_type']} &middot; {row['county']} Co.</div>
        <div class="pp-row">
            <span class="pp-key">Severity</span>
            <span class="pp-sev">{sev_label}</span>
        </div>
        {hail_line}
        {wind_line}
        <div class="pp-row"><span class="pp-key">Homes Affected</span><span class="pp-val">{row['homes_affected']:,}</span></div>
        <div class="pp-row"><span class="pp-key">Avg Roof Age</span><span class="pp-val">{row['avg_roof_age']} yrs</span></div>
        <div class="pp-row"><span class="pp-key">Owner-Occupied</span><span class="pp-val">{owner_pct}%</span></div>
        <div style="margin-top:8px;font-size:10px;color:#6B7280;font-style:italic;">{row['description']}</div>
    </div>
    """


def _add_legend(m: folium.Map) -> None:
    """Inject a floating severity legend into the map iframe."""
    legend_html = """
    <div id="hh-legend" style="
        position:absolute; bottom:30px; left:10px; z-index:9999;
        background:rgba(13,17,23,0.96);
        border:1px solid rgba(255,255,255,0.08);
        border-radius:10px; padding:12px 16px;
        font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
        box-shadow:0 4px 24px rgba(0,0,0,0.7);
        pointer-events:none;
    ">
        <div style="font-size:9px;font-weight:700;letter-spacing:.15em;color:#6B7280;
                    text-transform:uppercase;margin-bottom:10px;">
            Storm Severity
        </div>
        <div style="display:flex;flex-direction:column;gap:6px;">
            <div style="font-size:12px;color:#E5E7EB;display:flex;align-items:center;gap:8px;">
                <span style="color:#FFC107;font-size:18px;line-height:1;">&#9679;</span>Minor
            </div>
            <div style="font-size:12px;color:#E5E7EB;display:flex;align-items:center;gap:8px;">
                <span style="color:#FF6B35;font-size:18px;line-height:1;">&#9679;</span>Moderate
            </div>
            <div style="font-size:12px;color:#E5E7EB;display:flex;align-items:center;gap:8px;">
                <span style="color:#EF4444;font-size:18px;line-height:1;">&#9679;</span>Severe
            </div>
            <div style="font-size:12px;color:#E5E7EB;display:flex;align-items:center;gap:8px;">
                <span style="color:#9333EA;font-size:18px;line-height:1;">&#9679;</span>Catastrophic
            </div>
        </div>
    </div>
    """
    _inject_html(m, legend_html)


def _add_toolbar(m: folium.Map) -> None:
    """Inject a floating selection toolbar into the map iframe (Phase 1: visual only)."""
    toolbar_html = """
    <style>
        .hh-tb-btn {
            font-size:11px; color:#9CA3AF; cursor:default;
            padding:6px 10px; border-radius:5px;
            border:1px solid transparent;
            white-space:nowrap; display:flex; align-items:center; gap:6px;
            transition:background .15s;
            user-select:none;
        }
        .hh-tb-btn:hover {
            background:rgba(255,107,53,.1);
            border-color:rgba(255,107,53,.3);
            color:#FF6B35;
        }
        .hh-tb-btn-primary {
            color:#FF6B35;
            border-color:rgba(255,107,53,.35) !important;
            background:rgba(255,107,53,.06);
        }
        .hh-tb-divider {
            border:none; border-top:1px solid rgba(255,255,255,.07); margin:4px 0;
        }
    </style>
    <div id="hh-toolbar" style="
        position:absolute; top:70px; right:10px; z-index:9999;
        background:rgba(13,17,23,0.96);
        border:1px solid rgba(255,107,53,0.35);
        border-radius:10px; padding:10px 8px;
        min-width:138px;
        font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
        box-shadow:0 4px 24px rgba(0,0,0,0.7);
    ">
        <div style="font-size:9px;font-weight:700;letter-spacing:.15em;color:#6B7280;
                    text-transform:uppercase;text-align:center;
                    padding:0 0 8px;border-bottom:1px solid rgba(255,255,255,.07);
                    margin-bottom:8px;">
            Selection Tools
        </div>
        <div style="display:flex;flex-direction:column;gap:3px;">
            <div class="hh-tb-btn">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polygon points="12 2 22 20 2 20"></polygon>
                </svg>
                Draw Polygon
            </div>
            <div class="hh-tb-btn">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="10"></circle><circle cx="12" cy="12" r="3"></circle>
                </svg>
                Pin + Radius
            </div>
            <div class="hh-tb-btn">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="3" y="3" width="18" height="18" rx="2"></rect>
                    <path d="M9 3v18M15 3v18M3 9h18M3 15h18"></path>
                </svg>
                Zip Code
            </div>
            <div class="hh-tb-btn">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M3 6h18M3 12h18M3 18h18"></path>
                </svg>
                County / City
            </div>
            <hr class="hh-tb-divider">
            <div class="hh-tb-btn hh-tb-btn-primary">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="2" y="2" width="9" height="9"></rect><rect x="13" y="2" width="9" height="9"></rect>
                    <rect x="2" y="13" width="9" height="9"></rect><rect x="13" y="13" width="9" height="9"></rect>
                </svg>
                Select All
            </div>
        </div>
    </div>
    """
    _inject_html(m, toolbar_html)


def _inject_html(m: folium.Map, html: str) -> None:
    """Add a raw HTML string to the Folium map's root HTML."""

    class _RawHTML(MacroElement):
        def __init__(self, content: str):
            super().__init__()
            self._name = "_RawHTML"
            self._template = Template(
                "{% macro html(this, kwargs) %}{% raw %}" + content + "{% endraw %}{% endmacro %}"
            )

    m.get_root().add_child(_RawHTML(html))
