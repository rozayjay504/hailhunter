"""
Zone Intelligence panel — Phase 3

Public API:
    haversine_miles()       great-circle distance helper
    events_within_radius()  filter DataFrame to events within a radius
    find_nearest_event()    match a lat/lon to the closest event row
    render_selection_tools() mode selector + radius input (right column)
    render_zone_panel()     single-marker click intelligence panel
    render_radius_panel()   pin + radius aggregate intelligence panel
"""

import math

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.constants import SEVERITY_COLORS, SEVERITY_LABELS

# ── Lead economics ──────────────────────────────────────────────────────────────
_LEAD_RATE = 0.40    # 40 % of homes → potential leads
_AVG_JOB   = 8_500  # average roofing job value ($)


# ── Geo helpers ─────────────────────────────────────────────────────────────────

def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return great-circle distance in miles between two (lat, lon) points."""
    R = 3_958.8
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    Δφ = math.radians(lat2 - lat1)
    Δλ = math.radians(lon2 - lon1)
    a = math.sin(Δφ / 2) ** 2 + math.cos(φ1) * math.cos(φ2) * math.sin(Δλ / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def events_within_radius(
    df: pd.DataFrame, lat: float, lon: float, radius_miles: float
) -> pd.DataFrame:
    """Return subset of *df* whose events are within *radius_miles* of (lat, lon)."""
    if df.empty:
        return df
    mask = df.apply(
        lambda r: haversine_miles(lat, lon, r["lat"], r["lon"]) <= radius_miles,
        axis=1,
    )
    return df[mask].copy()


def find_nearest_event(
    df: pd.DataFrame, lat: float, lon: float, tol: float = 0.001
) -> "pd.Series | None":
    """Return the DataFrame row closest to (lat, lon), or None if beyond *tol* degrees."""
    if df.empty:
        return None
    dists = (df["lat"] - lat).abs() + (df["lon"] - lon).abs()
    idx = dists.idxmin()
    return df.loc[idx] if dists[idx] <= tol else None


# ── Panel renderers ─────────────────────────────────────────────────────────────

def render_selection_tools() -> None:
    """Render the Selection Mode panel in the right column."""
    st.markdown(
        '<div style="font-size:9px;font-weight:700;letter-spacing:.15em;color:#6B7280;'
        'text-transform:uppercase;padding:6px 0 8px;'
        'border-bottom:1px solid rgba(255,255,255,.07);margin-bottom:8px;">'
        "Selection Mode"
        "</div>",
        unsafe_allow_html=True,
    )

    mode = st.session_state.get("selection_mode", "click")

    c1, c2 = st.columns(2)
    with c1:
        if st.button(
            "📍 Marker",
            use_container_width=True,
            type="primary" if mode == "click" else "secondary",
            key="mode_click_btn",
        ):
            st.session_state.selection_mode = "click"
            st.session_state.pin_location = None
            st.rerun()
    with c2:
        if st.button(
            "⭕ Radius",
            use_container_width=True,
            type="primary" if mode == "radius" else "secondary",
            key="mode_radius_btn",
        ):
            st.session_state.selection_mode = "radius"
            st.session_state.clicked_lat = None
            st.session_state.clicked_lon = None
            st.rerun()

    for cs_label in ["Draw Polygon", "Zip Code", "County / City"]:
        st.button(
            f"🔒 {cs_label}  ·  Coming Soon",
            use_container_width=True,
            disabled=True,
            key=f"cs_{cs_label.lower().replace(' ', '_').replace('/', '_')}",
        )

    if mode == "radius":
        st.markdown('<div style="height:4px;"></div>', unsafe_allow_html=True)
        radius = st.number_input(
            "Radius (miles)",
            min_value=1,
            max_value=250,
            value=int(st.session_state.get("pin_radius_miles", 25)),
            step=5,
            key="radius_input",
        )
        st.session_state.pin_radius_miles = radius
        pin = st.session_state.get("pin_location")
        if pin:
            lat, lon = pin
            st.caption(f"Pin: {lat:.4f}, {lon:.4f} · {radius} mi")
        else:
            st.caption("Click the map to drop a pin.")
    else:
        # Hint when nothing is selected
        clat = st.session_state.get("clicked_lat")
        if clat is None:
            st.markdown(
                '<div style="margin-top:20px;text-align:center;color:#374151;'
                'font-size:11px;padding:16px 0;'
                'border:1px dashed rgba(255,255,255,.06);border-radius:8px;">'
                "Click a storm marker<br>to view zone intelligence."
                "</div>",
                unsafe_allow_html=True,
            )


def render_zone_panel(event: pd.Series, all_df: pd.DataFrame, radius_miles: float = 25) -> None:
    """Zone Intelligence panel for a single clicked storm marker."""
    sev = max(1, min(4, int(event["severity"])))
    color = SEVERITY_COLORS[sev]
    sev_label = SEVERITY_LABELS[sev]
    leads = int(event["homes_affected"] * _LEAD_RATE)
    revenue = leads * _AVG_JOB
    date_str = (
        event["date"].strftime("%b %d, %Y")
        if hasattr(event["date"], "strftime")
        else str(event["date"])
    )

    st.markdown(
        f'<div style="background:#111827;border-top:3px solid {color};'
        f'border-radius:8px;padding:12px 14px 10px;margin:8px 0 6px;">'
        f'<div style="font-size:13px;font-weight:700;color:#E5E7EB;">'
        f"{event['city']}, {event['state']}"
        f"</div>"
        f'<div style="font-size:10px;color:#9CA3AF;letter-spacing:.05em;'
        f'text-transform:uppercase;margin:2px 0 8px;">'
        f"{date_str} &middot; {event['event_type']} &middot; {event['county']} Co."
        f"</div>"
        f'<span style="display:inline-block;padding:2px 10px;border-radius:12px;'
        f"font-size:10px;font-weight:700;"
        f"background:{color}22;color:{color};border:1px solid {color}55;\">"
        f"{sev_label}"
        f"</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

    _row("Homes Affected", f"{event['homes_affected']:,}")
    _row("Est. Leads (40%)", f"{leads:,}")
    _row("Revenue Potential", f"${revenue:,.0f}")

    if event["event_type"] == "Hail" and pd.notna(event.get("hail_size")):
        _row("Hail Size", f'{event["hail_size"]:.2f}"')
    elif pd.notna(event.get("wind_speed")):
        _row("Wind Speed", f'{int(event["wind_speed"])} mph')

    _row("Avg Roof Age", f"{event['avg_roof_age']} yrs")
    _row("Owner-Occupied", f"{int(event['owner_pct'] * 100)}%")

    nearby = events_within_radius(all_df, event["lat"], event["lon"], radius_miles)
    _severity_chart(nearby, radius_miles)

    ca, cb = st.columns(2)
    with ca:
        st.button("📤 Export", use_container_width=True, disabled=True, key="exp_event_btn")
    with cb:
        if st.button("✕ Clear", use_container_width=True, key="clear_event_btn"):
            st.session_state.clicked_lat = None
            st.session_state.clicked_lon = None
            st.session_state._last_obj_click = None
            st.rerun()


def render_radius_panel(
    events_df: pd.DataFrame, lat: float, lon: float, radius_miles: float
) -> None:
    """Zone Intelligence panel for a pin + radius selection."""
    n = len(events_df)
    total_homes = int(events_df["homes_affected"].sum()) if n else 0
    leads = int(total_homes * _LEAD_RATE)
    revenue = leads * _AVG_JOB

    st.markdown(
        '<div style="background:#111827;border-top:3px solid #FF6B35;'
        "border-radius:8px;padding:12px 14px 10px;margin:8px 0 6px;\">"
        '<div style="font-size:13px;font-weight:700;color:#E5E7EB;">Pin + Radius Zone</div>'
        '<div style="font-size:10px;color:#9CA3AF;letter-spacing:.05em;'
        'text-transform:uppercase;margin:2px 0;">'
        f"{lat:.4f}, {lon:.4f} &middot; {radius_miles} mi radius"
        "</div>"
        "</div>",
        unsafe_allow_html=True,
    )

    _row("Storm Events", f"{n:,}")
    _row("Homes Affected", f"{total_homes:,}")
    _row("Est. Leads (40%)", f"{leads:,}")
    _row("Revenue Potential", f"${revenue:,.0f}")

    _severity_chart(events_df, radius_miles)

    ca, cb = st.columns(2)
    with ca:
        st.button("📤 Export", use_container_width=True, disabled=True, key="exp_radius_btn")
    with cb:
        if st.button("✕ Clear Pin", use_container_width=True, key="clear_pin_btn"):
            st.session_state.pin_location = None
            st.session_state._last_map_click = None
            st.rerun()


# ── Private helpers ─────────────────────────────────────────────────────────────

def _row(label: str, value: str) -> None:
    st.markdown(
        f'<div style="display:flex;justify-content:space-between;'
        f'font-size:12px;padding:4px 0;border-bottom:1px solid rgba(255,255,255,.05);">'
        f'<span style="color:#9CA3AF;">{label}</span>'
        f'<span style="color:#E5E7EB;font-weight:600;">{value}</span>'
        f"</div>",
        unsafe_allow_html=True,
    )


def _severity_chart(df: pd.DataFrame, radius_miles: float) -> None:
    if df.empty:
        st.caption("No events in range.")
        return

    counts = {s: 0 for s in [1, 2, 3, 4]}
    for sev in df["severity"]:
        counts[max(1, min(4, int(sev)))] += 1

    fig = go.Figure(
        go.Bar(
            x=[SEVERITY_LABELS[s] for s in [1, 2, 3, 4]],
            y=[counts[s] for s in [1, 2, 3, 4]],
            marker_color=[SEVERITY_COLORS[s] for s in [1, 2, 3, 4]],
            marker_line_width=0,
        )
    )
    fig.update_layout(
        margin=dict(l=0, r=0, t=28, b=0),
        height=130,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#9CA3AF", size=10),
        title=dict(
            text=f"Severity · {radius_miles} mi · {len(df)} events",
            font=dict(size=9, color="#6B7280"),
            x=0,
        ),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        xaxis=dict(showgrid=False, zeroline=False),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
