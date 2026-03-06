"""
Lead Export + CRM Integration — Phase 5

Public API:
    build_leads_df(events_df)   build export-schema DataFrame
    csv_bytes(leads_df)         return UTF-8 CSV bytes
    pdf_bytes(zone_label, events_df)  return reportlab PDF bytes
    push_to_ghl(webhook_url, api_key, events_df)  POST to GHL webhook
"""

from __future__ import annotations

import io
from datetime import date
from typing import Tuple

import pandas as pd
import requests

# reportlab imports
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable,
)


# ── Lead economics (mirrors zone_panel constants) ───────────────────────────────

_LEAD_RATE = 0.40
_AVG_JOB   = 8_500

# ── Colours ─────────────────────────────────────────────────────────────────────

_ORANGE    = colors.HexColor("#FF6B35")
_DARK_BG   = colors.HexColor("#111827")
_DARK_GRAY = colors.HexColor("#1F2937")
_LIGHT_TXT = colors.HexColor("#E5E7EB")
_MID_GRAY  = colors.HexColor("#9CA3AF")


# ── Public ──────────────────────────────────────────────────────────────────────

def build_leads_df(events_df: pd.DataFrame) -> pd.DataFrame:
    """
    Return a tidy export DataFrame from *events_df*.

    Columns: date, event_type, severity, city, state, county,
             hail_size, wind_speed, homes_affected,
             estimated_leads, revenue_potential, lat, lon
    """
    if events_df.empty:
        return pd.DataFrame(columns=[
            "date", "event_type", "severity", "city", "state", "county",
            "hail_size", "wind_speed", "homes_affected",
            "estimated_leads", "revenue_potential", "lat", "lon",
        ])

    df = events_df.copy()

    # Compute lead economics
    df["estimated_leads"]    = (df["homes_affected"] * _LEAD_RATE).astype(int)
    df["revenue_potential"]  = df["estimated_leads"] * _AVG_JOB

    # Select and order columns (safe — use .get with None fallback)
    cols = [
        "date", "event_type", "severity", "city", "state", "county",
        "hail_size", "wind_speed", "homes_affected",
        "estimated_leads", "revenue_potential", "lat", "lon",
    ]
    for c in cols:
        if c not in df.columns:
            df[c] = None

    return df[cols].reset_index(drop=True)


def csv_bytes(leads_df: pd.DataFrame) -> bytes:
    """Return UTF-8 CSV bytes for *leads_df*."""
    return leads_df.to_csv(index=False).encode("utf-8")


def pdf_bytes(zone_label: str, events_df: pd.DataFrame) -> bytes:
    """
    Build and return a reportlab PDF report for *events_df*.

    *zone_label* is a short string like "Miami, FL" or "Pin + 25 mi Radius".
    """
    leads_df = build_leads_df(events_df)
    buf = io.BytesIO()

    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        rightMargin=0.6 * inch,
        leftMargin=0.6 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
    )

    styles = getSampleStyleSheet()
    story = []

    # ── Header ────────────────────────────────────────────────────────────────
    title_style = ParagraphStyle(
        "HHTitle",
        parent=styles["Normal"],
        fontSize=22,
        leading=26,
        textColor=_ORANGE,
        fontName="Helvetica-Bold",
        spaceAfter=2,
    )
    sub_style = ParagraphStyle(
        "HHSub",
        parent=styles["Normal"],
        fontSize=9,
        textColor=_MID_GRAY,
        fontName="Helvetica",
        spaceAfter=0,
    )
    zone_style = ParagraphStyle(
        "HHZone",
        parent=styles["Normal"],
        fontSize=13,
        leading=16,
        textColor=_LIGHT_TXT,
        fontName="Helvetica-Bold",
        spaceBefore=8,
        spaceAfter=2,
    )
    label_style = ParagraphStyle(
        "HHLabel",
        parent=styles["Normal"],
        fontSize=8,
        textColor=_MID_GRAY,
        fontName="Helvetica",
        spaceAfter=10,
    )

    story.append(Paragraph("⚡ HAILHUNTER", title_style))
    story.append(Paragraph("Storm Intelligence Platform", sub_style))
    story.append(HRFlowable(width="100%", thickness=1, color=_ORANGE, spaceAfter=6))
    story.append(Paragraph(zone_label, zone_style))
    story.append(Paragraph(f"Generated {date.today().strftime('%B %d, %Y')}", label_style))

    # ── Summary stats ─────────────────────────────────────────────────────────
    n            = len(leads_df)
    total_homes  = int(leads_df["homes_affected"].sum()) if n else 0
    total_leads  = int(leads_df["estimated_leads"].sum()) if n else 0
    total_rev    = total_leads * _AVG_JOB

    summary_data = [
        ["Storm Events", "Homes Affected", "Est. Leads", "Revenue Potential"],
        [
            f"{n:,}",
            f"{total_homes:,}",
            f"{total_leads:,}",
            f"${total_rev:,.0f}",
        ],
    ]
    story.append(_pdf_table(
        summary_data,
        col_widths=None,
        hdr_color=_ORANGE,
        font_size=9,
    ))
    story.append(Spacer(1, 10))

    # ── Severity breakdown ────────────────────────────────────────────────────
    from utils.constants import SEVERITY_LABELS
    sev_counts = {1: 0, 2: 0, 3: 0, 4: 0}
    for s in leads_df["severity"].dropna():
        sev_counts[max(1, min(4, int(s)))] += 1

    sev_data = [["Severity", "Label", "Count"]] + [
        [str(s), SEVERITY_LABELS[s], str(sev_counts[s])]
        for s in [1, 2, 3, 4]
    ]
    story.append(Paragraph("Severity Breakdown", ParagraphStyle(
        "SevHdr", parent=styles["Normal"],
        fontSize=9, fontName="Helvetica-Bold",
        textColor=_MID_GRAY, spaceAfter=4,
    )))
    story.append(_pdf_table(sev_data, col_widths=None, hdr_color=_DARK_GRAY, font_size=8))
    story.append(Spacer(1, 12))

    # ── Events table (top 50) ─────────────────────────────────────────────────
    show = leads_df.head(50).copy()

    def _fmt_date(v):
        if hasattr(v, "strftime"):
            return v.strftime("%m/%d/%Y")
        return str(v) if pd.notna(v) else ""

    def _fmt_hail(row):
        if pd.notna(row.get("hail_size")) and row.get("hail_size"):
            return f'{row["hail_size"]:.2f}"'
        if pd.notna(row.get("wind_speed")) and row.get("wind_speed"):
            return f'{int(row["wind_speed"])} mph'
        return ""

    rows = [["Date", "Type", "City", "State", "Homes", "Leads", "Revenue", "Notes"]]
    for _, r in show.iterrows():
        rows.append([
            _fmt_date(r["date"]),
            str(r["event_type"]) if pd.notna(r.get("event_type")) else "",
            str(r["city"]) if pd.notna(r.get("city")) else "",
            str(r["state"]) if pd.notna(r.get("state")) else "",
            f"{int(r['homes_affected']):,}" if pd.notna(r.get("homes_affected")) else "",
            f"{int(r['estimated_leads']):,}" if pd.notna(r.get("estimated_leads")) else "",
            f"${int(r['revenue_potential']):,}" if pd.notna(r.get("revenue_potential")) else "",
            _fmt_hail(r),
        ])

    story.append(Paragraph("Event Details", ParagraphStyle(
        "EvtHdr", parent=styles["Normal"],
        fontSize=9, fontName="Helvetica-Bold",
        textColor=_MID_GRAY, spaceAfter=4,
    )))
    story.append(_pdf_table(
        rows,
        col_widths=[0.8, 0.65, 1.1, 0.45, 0.65, 0.55, 0.85, 0.8],
        hdr_color=_DARK_GRAY,
        font_size=7,
    ))

    if n > 50:
        story.append(Paragraph(
            f"… {n - 50} additional events not shown. Export CSV for full dataset.",
            ParagraphStyle("Footnote", parent=styles["Normal"],
                           fontSize=7, textColor=_MID_GRAY, spaceBefore=4),
        ))

    doc.build(story)
    return buf.getvalue()


def push_to_ghl(
    webhook_url: str,
    api_key: str,
    events_df: pd.DataFrame,
) -> Tuple[bool, str]:
    """
    POST *events_df* lead rows to a GHL webhook.

    Returns (success: bool, message: str).
    """
    if not webhook_url or not webhook_url.startswith("http"):
        return False, "Invalid webhook URL."

    leads_df = build_leads_df(events_df)

    def _row_dict(r):
        return {
            "date":              r["date"].strftime("%Y-%m-%d") if hasattr(r["date"], "strftime") else str(r["date"]),
            "event_type":        str(r["event_type"]) if pd.notna(r.get("event_type")) else "",
            "severity":          int(r["severity"]) if pd.notna(r.get("severity")) else 0,
            "city":              str(r["city"]) if pd.notna(r.get("city")) else "",
            "state":             str(r["state"]) if pd.notna(r.get("state")) else "",
            "county":            str(r["county"]) if pd.notna(r.get("county")) else "",
            "homes_affected":    int(r["homes_affected"]) if pd.notna(r.get("homes_affected")) else 0,
            "estimated_leads":   int(r["estimated_leads"]) if pd.notna(r.get("estimated_leads")) else 0,
            "revenue_potential": float(r["revenue_potential"]) if pd.notna(r.get("revenue_potential")) else 0.0,
            "lat":               float(r["lat"]) if pd.notna(r.get("lat")) else None,
            "lon":               float(r["lon"]) if pd.notna(r.get("lon")) else None,
        }

    payload = {
        "source":   "HailHunter",
        "exported": date.today().isoformat(),
        "event_count": len(leads_df),
        "leads":    [_row_dict(r) for _, r in leads_df.iterrows()],
    }

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        resp = requests.post(webhook_url, json=payload, headers=headers, timeout=10)
        if resp.status_code < 300:
            return True, f"Pushed {len(leads_df)} leads (HTTP {resp.status_code})."
        return False, f"HTTP {resp.status_code}: {resp.text[:200]}"
    except requests.exceptions.Timeout:
        return False, "Request timed out after 10 s."
    except requests.exceptions.RequestException as exc:
        return False, str(exc)


# ── Private ─────────────────────────────────────────────────────────────────────

def _pdf_table(
    data: list,
    col_widths: list | None,
    hdr_color: colors.Color,
    font_size: int,
) -> Table:
    """Build a styled reportlab Table from *data* (first row = header)."""
    page_w = letter[0] - 1.2 * inch  # usable width

    if col_widths:
        total = sum(col_widths)
        cw = [w / total * page_w for w in col_widths]
    else:
        n_cols = len(data[0]) if data else 1
        cw = [page_w / n_cols] * n_cols

    tbl = Table(data, colWidths=cw, repeatRows=1)
    n_rows = len(data)

    style = TableStyle([
        # Header row
        ("BACKGROUND",  (0, 0), (-1, 0), hdr_color),
        ("TEXTCOLOR",   (0, 0), (-1, 0), _LIGHT_TXT),
        ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, 0), font_size),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 5),
        ("TOPPADDING",  (0, 0), (-1, 0), 5),
        # Data rows — alternating
        ("FONTNAME",    (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",    (0, 1), (-1, -1), font_size),
        ("TEXTCOLOR",   (0, 1), (-1, -1), colors.HexColor("#374151")),
        ("TOPPADDING",  (0, 1), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 3),
        # Grid
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E5E7EB")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#F9FAFB")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ])
    tbl.setStyle(style)
    return tbl
