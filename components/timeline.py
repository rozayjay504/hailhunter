"""
Phase 4: Time Slider + Animated Storm Playback
components/timeline.py

Public API:
    init_timeline_state(date_start, date_end)  — initialise session state
    render_timeline(date_start, date_end, all_df)  — render full section;
        auto-advances via time.sleep + st.rerun when playing.
"""

import time
from datetime import date, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# seconds per day for each speed preset
_SPEEDS: dict[str, float] = {
    "Slow":   1.0,
    "Normal": 0.5,
    "Fast":   0.1,
}


# ── Public ──────────────────────────────────────────────────────────────────────

def init_timeline_state(date_start: date, date_end: date) -> None:
    """Initialise timeline session-state keys; clamp date to valid range."""
    tl = st.session_state.get("timeline_date")
    if tl is None or not (date_start <= tl <= date_end):
        st.session_state.timeline_date = date_end
    st.session_state.setdefault("timeline_playing", False)
    st.session_state.setdefault("timeline_speed",  "Normal")


def render_timeline(
    date_start: date,
    date_end:   date,
    all_df:     pd.DataFrame,
) -> date:
    """
    Render the density chart, date slider, and play controls.

    Returns the current slider date so the caller can use it to
    filter the map (the same value is in st.session_state.timeline_date).
    Triggers auto-advance via time.sleep + st.rerun when playing.
    """
    init_timeline_state(date_start, date_end)

    total_days  = max(1, (date_end - date_start).days)
    cur_offset  = (st.session_state.timeline_date - date_start).days
    cur_offset  = max(0, min(total_days, cur_offset))

    # ── Density chart ─────────────────────────────────────────────────────────
    _density_chart(all_df, date_start, date_end, st.session_state.timeline_date)

    # ── Controls row ──────────────────────────────────────────────────────────
    c_play, c_slider, c_speed = st.columns([1, 8, 1])

    with c_play:
        playing = st.session_state.timeline_playing
        if st.button(
            "⏸" if playing else "▶",
            key="tl_play_btn",
            use_container_width=True,
            help="Pause" if playing else "Play",
        ):
            st.session_state.timeline_playing = not playing
            st.rerun()

    with c_slider:
        cur_date_label = (date_start + timedelta(days=cur_offset)).strftime("%B %d, %Y")
        st.markdown(
            f'<div style="text-align:center;font-size:11px;font-weight:700;'
            f'color:#FF6B35;letter-spacing:.06em;margin-bottom:-4px;">'
            f"{cur_date_label}</div>",
            unsafe_allow_html=True,
        )
        new_offset = st.slider(
            "tl_slider_label",
            min_value=0,
            max_value=total_days,
            value=cur_offset,
            key="tl_slider",
            label_visibility="collapsed",
        )
        if new_offset != cur_offset:
            st.session_state.timeline_date   = date_start + timedelta(days=new_offset)
            st.session_state.timeline_playing = False   # stop on manual drag
            st.rerun()

    with c_speed:
        speed_keys = list(_SPEEDS.keys())
        speed = st.selectbox(
            "tl_speed_label",
            options=speed_keys,
            index=speed_keys.index(st.session_state.timeline_speed),
            key="tl_speed_select",
            label_visibility="collapsed",
        )
        st.session_state.timeline_speed = speed

    # ── Auto-advance ──────────────────────────────────────────────────────────
    if st.session_state.timeline_playing:
        next_offset = cur_offset + 1
        if next_offset > total_days:
            st.session_state.timeline_playing = False
        else:
            time.sleep(_SPEEDS[st.session_state.timeline_speed])
            st.session_state.timeline_date = date_start + timedelta(days=next_offset)
            st.rerun()

    return st.session_state.timeline_date


# ── Private ──────────────────────────────────────────────────────────────────────

def _density_chart(
    df:         pd.DataFrame,
    date_start: date,
    date_end:   date,
    cur_date:   date,
) -> None:
    """Compact weekly event-density bar chart with a cursor line at cur_date."""
    if df.empty:
        return

    df2 = df.copy()
    df2["_ts"] = pd.to_datetime(
        df2["date"].apply(lambda d: d.date() if hasattr(d, "date") else d)
    )
    df2["_week"] = df2["_ts"].dt.to_period("W").apply(lambda p: p.start_time)
    weekly = df2.groupby("_week").size().reset_index(name="n")

    ts_start = pd.Timestamp(date_start)
    ts_end   = pd.Timestamp(date_end)
    ts_cur   = pd.Timestamp(cur_date)

    fig = go.Figure(
        go.Bar(
            x=weekly["_week"],
            y=weekly["n"],
            marker_color="#FF6B35",
            marker_line_width=0,
            opacity=0.65,
        )
    )
    fig.update_layout(
        height=52,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            range=[ts_start, ts_end],
        ),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        showlegend=False,
        shapes=[
            dict(
                type="line",
                x0=ts_cur, x1=ts_cur,
                y0=0,      y1=1,
                yref="paper",
                line=dict(color="rgba(255,255,255,0.75)", width=1.5, dash="dot"),
            )
        ],
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
