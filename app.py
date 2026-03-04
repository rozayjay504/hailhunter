"""
HailHunter — Storm Intelligence Platform
Phase 1: Map shell with mock storm data and sidebar filters.
"""

import streamlit as st
from datetime import date, timedelta
from streamlit_folium import st_folium

from components.filters import render_sidebar, get_active_filters
from components.map import build_map
from data.pipeline import get_storms, filter_storms


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
    /* ── Hide default Streamlit chrome ── */
    #MainMenu, footer, header { visibility: hidden; }

    /* ── Layout ── */
    .block-container {
        padding-top: 0.5rem !important;
        padding-bottom: 0 !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: 100% !important;
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

    /* ── Map iframe ── */
    .stIFrame, iframe {
        border-radius: 8px !important;
        border: 1px solid rgba(255, 255, 255, 0.06) !important;
    }

    /* ── Top info bar ── */
    .top-bar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 6px 4px 8px;
        border-bottom: 1px solid rgba(255,255,255,0.05);
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
        "date_preset":      "90D",
        "date_start":       date.today() - timedelta(days=90),
        "date_end":         date.today(),
        "home_age_min":     0,
        "home_age_max":     50,
        "owner_type":       "All",
        "severity_min":     1,
        # Map interaction (Phase 3+)
        "selected_zone":    None,
        "saved_zones":      [],
        "map_return":       None,
        # Map interaction (Phase 3+) — n_visible_storms removed; written
        # directly to st.sidebar after filtering to avoid session-state lag.
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    _inject_css()
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

    # Write the count badge now — after filtering — so it is always current.
    with st.sidebar:
        st.markdown('<div class="filter-divider"></div>', unsafe_allow_html=True)
        st.markdown(
            f'<div style="text-align:center;color:#6B7280;font-size:11px;padding:8px 0;">'
            f'<span style="color:#FF6B35;font-weight:700;">{len(filtered_df)}</span>'
            f' storm events visible</div>',
            unsafe_allow_html=True,
        )

    # ── Top bar ──────────────────────────────────────────────────────────────
    n = len(filtered_df)
    total = len(raw_df)
    src_color = "#10B981" if data_source == "live" else "#6B7280"
    src_label = "LIVE" if data_source == "live" else "MOCK"
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

    # ── Map ──────────────────────────────────────────────────────────────────
    folium_map = build_map(filtered_df)

    map_return = st_folium(
        folium_map,
        use_container_width=True,
        height=760,
        key="main_map",
        returned_objects=[],   # Phase 1: no click handling needed
    )
    st.session_state.map_return = map_return


if __name__ == "__main__":
    main()
