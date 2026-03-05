"""
Folium map builder.

build_map(df) is the single public function — it takes a filtered storm
DataFrame and returns a configured folium.Map ready for st_folium().
"""

import folium
from branca.element import MacroElement
from jinja2 import Template

from utils.constants import (
    MAP_CENTER, MAP_ZOOM, MAP_TILE_URL, MAP_TILE_ATTR,
    SEVERITY_COLORS, SEVERITY_LABELS, SEVERITY_RADIUS,
)


# ── Public ─────────────────────────────────────────────────────────────────────

def build_map(
    df: pd.DataFrame,
    center: list | None = None,
    zoom: int | None = None,
) -> folium.Map:
    """Build and return a fully configured dark Folium map with storm overlays."""

    m = folium.Map(
        location=center or MAP_CENTER,
        zoom_start=zoom or MAP_ZOOM,
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

    return m


# ── Private ────────────────────────────────────────────────────────────────────

def _add_storm_markers(m: folium.Map, df: pd.DataFrame) -> None:
    """Add a CircleMarker for every storm event in the DataFrame."""
    for _, row in df.iterrows():
        severity = max(1, min(4, int(row["severity"])))  # clamp 1–4 defensively
        color = SEVERITY_COLORS[severity]
        radius = SEVERITY_RADIUS[severity]

        date_str = row["date"].strftime("%b %d, %Y") if hasattr(row["date"], "strftime") else str(row["date"])
        tooltip_text = f"{row['city']}, {row['state']}  ·  {row['event_type']}  ·  {date_str}"

        folium.CircleMarker(
            location=[row["lat"], row["lon"]],
            radius=radius,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.35,
            weight=2,
            opacity=0.9,
            tooltip=folium.Tooltip(tooltip_text, style=(
                "background-color:#0D1117; color:#E5E7EB; "
                "border:1px solid rgba(255,255,255,0.1); "
                "border-radius:4px; font-size:12px; padding:4px 8px;"
            )),
        ).add_to(m)


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
