"""
Sidebar filter panel.

Renders all filter widgets into st.sidebar and keeps st.session_state
in sync. No return value — filters are read from session state by the
caller via get_active_filters().
"""

import streamlit as st
from datetime import date, timedelta
from utils.constants import STORM_TYPES, HAIL_SIZE_MARKS, HAIL_SIZE_MIN, HAIL_SIZE_MAX


def _section(label: str) -> None:
    """Render a styled section divider + header."""
    st.markdown(f'<div class="filter-label">{label}</div>', unsafe_allow_html=True)


def render_sidebar() -> None:
    """Render the full sidebar filter panel."""

    with st.sidebar:
        # ── Brand header ──────────────────────────────────────────────────────
        st.markdown("""
        <div class="sidebar-brand">
            <h1>⚡ HAILHUNTER</h1>
            <p>Storm Intelligence Platform</p>
        </div>
        """, unsafe_allow_html=True)

        # ── Storm Type ────────────────────────────────────────────────────────
        _section("Storm Type")
        col1, col2 = st.columns(2)
        storm_types = []
        with col1:
            if st.checkbox("🌨 Hail", value="Hail" in st.session_state.storm_types, key="cb_hail"):
                storm_types.append("Hail")
            if st.checkbox("🌀 Hurricane", value="Hurricane" in st.session_state.storm_types, key="cb_hurricane"):
                storm_types.append("Hurricane")
        with col2:
            if st.checkbox("💨 Wind", value="Wind" in st.session_state.storm_types, key="cb_wind"):
                storm_types.append("Wind")
            if st.checkbox("🌊 Tropical", value="Tropical Storm" in st.session_state.storm_types, key="cb_tropical"):
                storm_types.append("Tropical Storm")
        st.session_state.storm_types = storm_types

        # ── Hail Size ─────────────────────────────────────────────────────────
        st.markdown('<div class="filter-divider"></div>', unsafe_allow_html=True)
        _section("Min Hail Size")
        hail_size = st.slider(
            "hail_size_slider_label",
            min_value=HAIL_SIZE_MIN,
            max_value=HAIL_SIZE_MAX,
            step=0.25,
            value=float(st.session_state.hail_size_min),
            key="hail_size_slider",
            label_visibility="collapsed",
            format='%.2f"',
        )
        size_name = HAIL_SIZE_MARKS.get(round(hail_size, 2), f'{hail_size:.2f}"')
        st.caption(f"≥ **{hail_size:.2f}\"** — {size_name}")
        st.session_state.hail_size_min = hail_size

        # ── Date Range ────────────────────────────────────────────────────────
        st.markdown('<div class="filter-divider"></div>', unsafe_allow_html=True)
        _section("Date Range")

        preset_options = ["7D", "30D", "90D", "Custom"]
        preset_idx = preset_options.index(st.session_state.date_preset) if st.session_state.date_preset in preset_options else 1
        preset = st.radio(
            "date_preset_radio_label",
            options=preset_options,
            index=preset_idx,
            horizontal=True,
            key="date_preset_radio",
            label_visibility="collapsed",
        )
        st.session_state.date_preset = preset

        today = date.today()
        if preset == "7D":
            st.session_state.date_start = today - timedelta(days=7)
            st.session_state.date_end = today
            st.caption(f"{st.session_state.date_start.strftime('%b %d')} → {today.strftime('%b %d, %Y')}")
        elif preset == "30D":
            st.session_state.date_start = today - timedelta(days=30)
            st.session_state.date_end = today
            st.caption(f"{st.session_state.date_start.strftime('%b %d')} → {today.strftime('%b %d, %Y')}")
        elif preset == "90D":
            st.session_state.date_start = today - timedelta(days=90)
            st.session_state.date_end = today
            st.caption(f"{st.session_state.date_start.strftime('%b %d')} → {today.strftime('%b %d, %Y')}")
        else:
            dates = st.date_input(
                "Custom range",
                value=(st.session_state.date_start, st.session_state.date_end),
                key="custom_date_range",
                label_visibility="collapsed",
            )
            if isinstance(dates, (list, tuple)) and len(dates) == 2:
                st.session_state.date_start, st.session_state.date_end = dates[0], dates[1]

        # ── Home / Roof Age ───────────────────────────────────────────────────
        st.markdown('<div class="filter-divider"></div>', unsafe_allow_html=True)
        _section("Roof Age (years)")
        age_range = st.slider(
            "roof_age_label",
            min_value=0,
            max_value=50,
            value=(st.session_state.home_age_min, st.session_state.home_age_max),
            key="home_age_slider",
            label_visibility="collapsed",
            format="%d yr",
        )
        st.session_state.home_age_min, st.session_state.home_age_max = age_range[0], age_range[1]
        max_label = "50+" if age_range[1] == 50 else f"{age_range[1]} yr"
        st.caption(f"{age_range[0]} yr — {max_label}")

        # ── Occupancy ─────────────────────────────────────────────────────────
        st.markdown('<div class="filter-divider"></div>', unsafe_allow_html=True)
        _section("Occupancy")
        occupancy_options = ["All", "Owners Only", "Renters Only"]
        owner_idx = occupancy_options.index(st.session_state.owner_type) if st.session_state.owner_type in occupancy_options else 0
        owner_type = st.radio(
            "occupancy_radio_label",
            options=occupancy_options,
            index=owner_idx,
            key="owner_type_radio",
            label_visibility="collapsed",
        )
        st.session_state.owner_type = owner_type

        # ── Min Severity ──────────────────────────────────────────────────────
        st.markdown('<div class="filter-divider"></div>', unsafe_allow_html=True)
        _section("Min Severity")

        severity_labels = {
            1: "1 — Minor",
            2: "2 — Moderate",
            3: "3 — Severe",
            4: "4 — Catastrophic",
        }
        severity_min = st.select_slider(
            "severity_slider_label",
            options=[1, 2, 3, 4],
            value=st.session_state.severity_min,
            format_func=lambda x: severity_labels[x],
            key="severity_slider",
            label_visibility="collapsed",
        )
        st.session_state.severity_min = severity_min

        # ── Footer stats ──────────────────────────────────────────────────────
        st.markdown('<div class="filter-divider"></div>', unsafe_allow_html=True)
        n_visible = st.session_state.get("n_visible_storms", 0)
        st.markdown(
            f'<div style="text-align:center; color:#6B7280; font-size:11px; padding:8px 0;">'
            f'<span style="color:#FF6B35; font-weight:700;">{n_visible}</span> storm events visible'
            f'</div>',
            unsafe_allow_html=True,
        )


def get_active_filters() -> dict:
    """Return the current filter state as a plain dict for use in data/map layers."""
    return {
        "storm_types":   st.session_state.get("storm_types", STORM_TYPES),
        "hail_size_min": st.session_state.get("hail_size_min", HAIL_SIZE_MIN),
        "date_start":    st.session_state.get("date_start"),
        "date_end":      st.session_state.get("date_end"),
        "home_age_min":  st.session_state.get("home_age_min", 0),
        "home_age_max":  st.session_state.get("home_age_max", 50),
        "owner_type":    st.session_state.get("owner_type", "All"),
        "severity_min":  st.session_state.get("severity_min", 1),
    }
