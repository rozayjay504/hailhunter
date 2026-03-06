"""
HailHunter — Storm Intelligence Platform
Phase 1: Map shell with mock storm data and sidebar filters.
"""

import streamlit as st
import streamlit.components.v1 as components
from datetime import date, timedelta
from streamlit_folium import st_folium

from components.filters import render_sidebar, get_active_filters
from components.map import build_map
from components.timeline import init_timeline_state, render_timeline
from components.zone_panel import (
    render_selection_tools,
    render_zone_panel,
    render_radius_panel,
    events_within_radius,
    find_nearest_event,
)
from data.pipeline import get_storms, filter_storms
from utils.constants import REGIONS, REGION_MAP_CONFIG, MAP_EVENT_CAP


# ── Page config (must be first Streamlit call) ─────────────────────────────────

st.set_page_config(
    page_title="HailHunter",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ── CSS injection ──────────────────────────────────────────────────────────────

def _inject_css() -> None:
    st.markdown("""
    <style>
    /* ── Full-viewport lock — no page scroll ── */
    html, body {
        height: 100vh !important;
        overflow: hidden !important;
    }
    .stApp {
        height: 100vh !important;
        overflow: hidden !important;
    }

    /* ── Hide only what we need to — let Streamlit render its own header ── */
    #MainMenu, footer { visibility: hidden; }

    /* ── Layout ── */
    .block-container {
        padding-top: 0.5rem !important;
        padding-bottom: 0 !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: 100% !important;
        overflow: hidden !important;
    }

    /* ── Sidebar shell ── */
    [data-testid="stSidebar"] {
        background-color: #0D1117 !important;
        border-right: 1px solid rgba(255, 255, 255, 0.06) !important;
    }
    [data-testid="stSidebar"] > div:first-child {
        padding-top: 0 !important;
    }
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
        gap: 0 !important;
    }

    /* ── Brand header ── */
    .sidebar-brand {
        background: linear-gradient(160deg, #0d1117 0%, #161b27 100%);
        padding: 1.4rem 1rem 1.1rem;
        text-align: center;
        border-bottom: 1px solid rgba(255, 107, 53, 0.18);
        margin-bottom: 0.4rem;
    }
    .sidebar-brand h1 {
        font-size: 20px !important;
        font-weight: 900 !important;
        letter-spacing: 0.12em !important;
        background: linear-gradient(135deg, #FF6B35 0%, #EF4444 100%);
        -webkit-background-clip: text !important;
        -webkit-text-fill-color: transparent !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    .sidebar-brand p {
        font-size: 9px !important;
        color: #4B5563 !important;
        letter-spacing: 0.2em !important;
        text-transform: uppercase !important;
        margin: 5px 0 0 !important;
    }

    /* ── Filter section labels ── */
    .filter-label {
        font-size: 9px;
        font-weight: 800;
        letter-spacing: 0.14em;
        color: #4B5563;
        text-transform: uppercase;
        margin: 0.9rem 0 0.3rem;
        padding: 0 0.1rem;
    }

    /* ── Dividers ── */
    .filter-divider {
        border: none;
        border-top: 1px solid rgba(255, 255, 255, 0.05);
        margin: 0.5rem 0 0;
    }

    /* ── Checkboxes — tighter spacing ── */
    [data-testid="stCheckbox"] {
        margin-bottom: 0 !important;
    }

    /* ── Scrollbar ── */
    ::-webkit-scrollbar { width: 4px; height: 4px; }
    ::-webkit-scrollbar-track { background: #0A0E1A; }
    ::-webkit-scrollbar-thumb { background: #1F2937; border-radius: 2px; }
    ::-webkit-scrollbar-thumb:hover { background: #374151; }

    /* ── Hide raw slider thumb number (date label above is the display) ── */
    .stSlider [data-testid="stThumbValue"] { display: none !important; }

    /* ── Map iframe — fill remaining viewport height ── */
    .stIFrame, iframe {
        border-radius: 8px !important;
        border: 1px solid rgba(255, 255, 255, 0.06) !important;
        height: calc(100vh - 140px) !important;
    }

    /* ── Date picker — every known Baseweb/Streamlit calendar container ── */
    [data-baseweb="popover"] {
        transform: translateY(40px) !important;
    }
    [role="dialog"] > div {
        padding-top: 40px !important;
    }
    li[data-baseweb="menu-item"] {
        display: block !important;
    }

    /* ── Top info bar ── */
    .top-bar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 6px 4px 8px;
        border-bottom: 1px solid rgba(255,255,255,0.05);
        margin-top: 28px;
        margin-bottom: 6px;
    }
    .top-bar-title {
        font-size: 11px;
        font-weight: 700;
        color: #6B7280;
        letter-spacing: .12em;
        text-transform: uppercase;
    }
    .top-bar-badge {
        font-size: 11px;
        color: #FF6B35;
        font-weight: 700;
        background: rgba(255,107,53,.1);
        border: 1px solid rgba(255,107,53,.25);
        padding: 2px 10px;
        border-radius: 20px;
    }
    </style>
    """, unsafe_allow_html=True)


# ── Session state init ─────────────────────────────────────────────────────────

def _init_session_state() -> None:
    defaults = {
        # Filters
        "storm_types":      ["Hail", "Wind", "Hurricane", "Tropical Storm"],
        "hail_size_min":    0.75,
        "date_preset":      "30D",
        "date_start":       date.today() - timedelta(days=30),
        "date_end":         date.today(),
        "home_age_min":     0,
        "home_age_max":     50,
        "owner_type":       "All",
        "severity_min":     1,
        "selected_region":  "Southeast",
        "selected_states":  list(REGIONS["Southeast"]),
        # Map interaction
        "selected_zone":    None,
        "saved_zones":      [],
        "map_return":       None,
        # Phase 4 — timeline
        "timeline_visible": False,
        "timeline_playing": False,
        "timeline_speed":   "Normal",
        "timeline_date":    None,
        # Phase 3 — click / pin+radius state
        "selection_mode":   "click",
        "pin_radius_miles": 25,
        "pin_location":     None,
        "clicked_lat":      None,
        "clicked_lon":      None,
        "_last_obj_click":  None,
        "_last_map_click":  None,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


# ── Main ───────────────────────────────────────────────────────────────────────

def _inject_calendar_fix() -> None:
    """
    MutationObserver that watches for Baseweb calendar popovers appearing in
    the parent document (they render as a portal at the bottom of the DOM,
    outside the sidebar) and nudges them down so the month/year nav row is
    fully visible.  Injected via components.html so the <script> is not
    stripped by Streamlit's markdown sanitiser.
    """
    components.html("""
    <script>
    (function () {
        var doc = window.parent.document;
        function nudgePopover(calNode) {
            var el = calNode;
            for (var i = 0; i < 12; i++) {
                if (!el || el === doc.body) break;
                if (el.getAttribute && el.getAttribute('data-baseweb') === 'popover') {
                    el.style.marginTop = '52px';
                    el.style.top = 'auto';
                    return;
                }
                el = el.parentElement;
            }
        }
        var observer = new MutationObserver(function (mutations) {
            mutations.forEach(function (m) {
                m.addedNodes.forEach(function (node) {
                    if (node.nodeType !== 1) return;
                    if (node.getAttribute && node.getAttribute('data-baseweb') === 'calendar') {
                        nudgePopover(node);
                    }
                    if (node.querySelectorAll) {
                        node.querySelectorAll('[data-baseweb="calendar"]').forEach(nudgePopover);
                    }
                });
            });
        });
        observer.observe(doc.body, { childList: true, subtree: true });
    })();
    </script>
    """, height=0)


def main() -> None:
    _inject_css()
    _inject_calendar_fix()
    _init_session_state()

    # Sidebar renders first — writes to session_state
    render_sidebar()

    # Load + filter data
    filters = get_active_filters()
    raw_df, data_source = get_storms(
        start_date=filters.get("date_start"),
        end_date=filters.get("date_end"),
    )
    filtered_df = filter_storms(raw_df, filters)

    # Cap at MAP_EVENT_CAP, prioritising highest severity then most recent
    total_filtered = len(filtered_df)
    display_df = (
        filtered_df
        .sort_values(["severity", "date"], ascending=[False, False])
        .head(MAP_EVENT_CAP)
        .reset_index(drop=True)
    )

    # Sidebar: count badge + cap notice
    with st.sidebar:
        st.markdown('<div class="filter-divider"></div>', unsafe_allow_html=True)
        st.markdown(
            f'<div style="text-align:center;color:#6B7280;font-size:11px;padding:8px 0;">'
            f'<span style="color:#FF6B35;font-weight:700;">{len(display_df)}</span>'
            f' storm events visible</div>',
            unsafe_allow_html=True,
        )
        if total_filtered > MAP_EVENT_CAP:
            st.markdown(
                f'<div style="text-align:center;color:#6B7280;font-size:10px;padding:0 0 6px;">'
                f'Showing {MAP_EVENT_CAP} of {total_filtered} — narrow filters to see all.'
                f'</div>',
                unsafe_allow_html=True,
            )

    # ── Resolve slider date from session state (before map renders) ──────────
    tl_visible  = st.session_state.get("timeline_visible", False)
    date_start  = filters.get("date_start")
    date_end    = filters.get("date_end")
    if tl_visible and date_start and date_end:
        init_timeline_state(date_start, date_end)
        raw_sd      = st.session_state.get("timeline_date")
        slider_date = max(date_start, min(date_end, raw_sd)) if raw_sd else date_end
        # Cumulative view: show events up to slider position
        map_df = display_df[
            display_df["date"].apply(
                lambda d: (d.date() if hasattr(d, "date") else d) <= slider_date
            )
        ].copy()
    else:
        slider_date = None
        map_df      = display_df

    # ── Top bar + Timeline toggle (columns so button sits alongside bar) ──────
    n = len(display_df)
    total = len(raw_df)
    src_color = "#10B981" if data_source == "live" else "#6B7280"
    src_label = "LIVE" if data_source == "live" else "MOCK"

    c_bar, c_tl_toggle = st.columns([10, 2])
    with c_bar:
        st.markdown(
            f'<div class="top-bar">'
            f'<span class="top-bar-title">⚡ HailHunter &nbsp;·&nbsp; Storm Intelligence</span>'
            f'<span style="display:flex;align-items:center;gap:8px;">'
            f'<span style="font-size:10px;font-weight:700;color:{src_color};'
            f'background:{src_color}18;border:1px solid {src_color}44;'
            f'padding:2px 8px;border-radius:20px;letter-spacing:.08em;">{src_label}</span>'
            f'<span class="top-bar-badge">{n} / {total} Events</span>'
            f'</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with c_tl_toggle:
        # Spacer aligns button with top bar content (which has margin-top:28px)
        st.markdown('<div style="height:32px;"></div>', unsafe_allow_html=True)
        tl_btn_label = "📅 Hide" if tl_visible else "📅 Timeline"
        if st.button(
            tl_btn_label,
            key="tl_toggle_btn",
            use_container_width=True,
            type="primary" if tl_visible else "secondary",
        ):
            st.session_state.timeline_visible = not tl_visible
            if not st.session_state.timeline_visible:
                st.session_state.timeline_playing = False
            st.rerun()

    # ── Timeline strip (between top bar and map columns) ─────────────────────
    if tl_visible and date_start and date_end:
        render_timeline(date_start, date_end, display_df)
        st.markdown(
            '<div style="text-align:center;font-size:10px;color:#374151;'
            'letter-spacing:.04em;margin-top:-6px;margin-bottom:2px;">'
            'Drag slider to travel through time &nbsp;·&nbsp; '
            'Play animates storms chronologically &nbsp;·&nbsp; '
            'S / N / F controls speed'
            '</div>',
            unsafe_allow_html=True,
        )

    # ── Two-column layout: map (left) + zone panel (right) ───────────────────
    col_map, col_panel = st.columns([7, 3])

    with col_map:
        region_cfg = REGION_MAP_CONFIG.get(
            st.session_state.get("selected_region", "Southeast"),
            REGION_MAP_CONFIG["All States"],
        )
        folium_map = build_map(
            map_df,
            center=region_cfg["center"],
            zoom=region_cfg["zoom"],
            slider_date=slider_date,
        )

        map_height = 560 if tl_visible else 680
        map_return = st_folium(
            folium_map,
            use_container_width=True,
            height=map_height,
            key="main_map",
            returned_objects=["last_object_clicked", "last_clicked"],
        )
        st.session_state.map_return = map_return

    # ── Click processing (runs after map renders, before panel renders) ───────
    obj_click = (map_return or {}).get("last_object_clicked") or {}
    map_click  = (map_return or {}).get("last_clicked") or {}

    # Marker click → store lat/lon for zone panel
    if obj_click and obj_click != st.session_state.get("_last_obj_click"):
        st.session_state._last_obj_click = obj_click
        lat = obj_click.get("lat")
        lon = obj_click.get("lng")
        if lat is not None and lon is not None:
            st.session_state.clicked_lat = lat
            st.session_state.clicked_lon = lon
            st.session_state.pin_location = None  # clear any radius pin

    # Background map click → drop pin (only when in radius mode)
    if (
        st.session_state.get("selection_mode") == "radius"
        and map_click
        and map_click != st.session_state.get("_last_map_click")
    ):
        st.session_state._last_map_click = map_click
        lat = map_click.get("lat")
        lon = map_click.get("lng")
        if lat is not None and lon is not None:
            st.session_state.pin_location = (lat, lon)
            st.session_state.clicked_lat = None
            st.session_state.clicked_lon = None

    # ── Right panel ───────────────────────────────────────────────────────────
    with col_panel:
        render_selection_tools()

        clat = st.session_state.get("clicked_lat")
        clon = st.session_state.get("clicked_lon")
        pin  = st.session_state.get("pin_location")

        if clat is not None and clon is not None:
            event = find_nearest_event(display_df, clat, clon)
            if event is not None:
                render_zone_panel(event, display_df)
        elif st.session_state.get("selection_mode") == "radius" and pin is not None:
            lat, lon = pin
            radius = st.session_state.get("pin_radius_miles", 25)
            nearby = events_within_radius(display_df, lat, lon, radius)
            render_radius_panel(nearby, lat, lon, radius)



if __name__ == "__main__":
    main()
