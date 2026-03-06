"""
Sidebar filter panel.

Renders all filter widgets into st.sidebar and keeps st.session_state
in sync. No return value — filters are read from session state by the
caller via get_active_filters().
"""

import streamlit as st
from datetime import date, timedelta
from utils.constants import STORM_TYPES, HAIL_SIZE_MARKS, HAIL_SIZE_MIN, HAIL_SIZE_MAX, REGIONS


_LABEL_STYLE = (
    "font-size:9px;font-weight:800;letter-spacing:0.16em;color:#9CA3AF;"
    "text-transform:uppercase;display:block;margin:1.2rem 0 0.6rem;padding:0;"
)


def _section(label: str) -> None:
    """Render a styled section divider + header."""
    st.markdown(f'<div style="{_LABEL_STYLE}">{label}</div>', unsafe_allow_html=True)


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

        # ── Region ───────────────────────────────────────────────────────────
        _section("Region")
        region_options = list(REGIONS.keys())
        region_idx = region_options.index(st.session_state.selected_region) \
            if st.session_state.selected_region in region_options else 0
        selected_region = st.selectbox(
            "region_selector_label",
            options=region_options,
            index=region_idx,
            key="region_selectbox",
            label_visibility="collapsed",
        )
        # When region changes reset state selection to the first state in new region
        if selected_region != st.session_state.selected_region:
            st.session_state.selected_region = selected_region
            region_list = list(REGIONS[selected_region])
            st.session_state.selected_states = [region_list[0]] if region_list else []

        # ── States ───────────────────────────────────────────────────────────
        region_states = REGIONS[selected_region]
        if region_states:
            _section("States")
            # Key changes with region so widget re-renders fresh on region switch
            selected_states = st.multiselect(
                "states_multiselect_label",
                options=region_states,
                default=st.session_state.selected_states or region_states,
                key=f"states_ms_{selected_region}",
                label_visibility="collapsed",
            )
            st.session_state.selected_states = list(selected_states)
        else:
            st.session_state.selected_states = []

        st.markdown('<div class="filter-divider"></div>', unsafe_allow_html=True)

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
        st.markdown('<div style="height:10px"></div>', unsafe_allow_html=True)
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
        st.markdown('<div style="height:10px"></div>', unsafe_allow_html=True)

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

        # ── Dev: cache control ────────────────────────────────────────────────
        st.markdown('<div class="filter-divider"></div>', unsafe_allow_html=True)
        if st.button("🗑 Clear Cache", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        # Footer (count + export) rendered by render_sidebar_footer() below,
        # called from app.py after filtering so it always reflects live results.


def render_sidebar_footer(
    n_display: int,
    total_filtered: int,
    map_event_cap: int,
    leads_csv: bytes,
) -> None:
    """Render count badge + export button in the same sidebar block as the filter widgets."""
    with st.sidebar:
        st.markdown('<div style="border:none;border-top:1px solid rgba(255,255,255,0.05);margin:0.6rem 0 0;"></div>', unsafe_allow_html=True)
        st.markdown(
            f'<div style="text-align:center;color:#6B7280;font-size:11px;padding:8px 0 4px;">'
            f'<span style="color:#FF6B35;font-weight:700;">{n_display}</span>'
            f' storm events visible</div>',
            unsafe_allow_html=True,
        )
        if total_filtered > map_event_cap:
            st.markdown(
                f'<div style="text-align:center;color:#6B7280;font-size:10px;padding:0 0 4px;">'
                f'Showing {map_event_cap} of {total_filtered} — narrow filters to see all.'
                f'</div>',
                unsafe_allow_html=True,
            )
        st.markdown('<div style="height:12px"></div>', unsafe_allow_html=True)
        st.download_button(
            "📥 Export All Visible (CSV)",
            data=leads_csv,
            file_name="hailhunter_export.csv",
            mime="text/csv",
            use_container_width=True,
            key="sidebar_export_csv",
        )


def get_active_filters() -> dict:
    """Return the current filter state as a plain dict for use in data/map layers."""
    return {
        "storm_types":     st.session_state.get("storm_types", STORM_TYPES),
        "hail_size_min":   st.session_state.get("hail_size_min", HAIL_SIZE_MIN),
        "date_start":      st.session_state.get("date_start"),
        "date_end":        st.session_state.get("date_end"),
        "home_age_min":    st.session_state.get("home_age_min", 0),
        "home_age_max":    st.session_state.get("home_age_max", 50),
        "owner_type":      st.session_state.get("owner_type", "All"),
        "severity_min":    st.session_state.get("severity_min", 1),
        "selected_states": st.session_state.get("selected_states", []),
    }
