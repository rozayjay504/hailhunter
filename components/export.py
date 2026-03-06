"""
Lead Export + CRM Integration

Public API:
    build_leads_df(homeowner_df)              select export columns
    csv_bytes(homeowner_df)                   UTF-8 CSV bytes
    pdf_bytes(zone_label, homeowner_df,
              zone_summary)                   reportlab PDF bytes
    push_to_ghl(webhook_url, api_key,
                homeowner_df)                 POST contacts to GHL webhook
"""

from __future__ import annotations

import io
from datetime import date
from typing import Tuple

import pandas as pd
import requests

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable,
)


# ── Colours ─────────────────────────────────────────────────────────────────────

_ORANGE    = colors.HexColor("#FF6B35")
_DARK_GRAY = colors.HexColor("#1F2937")
_LIGHT_TXT = colors.HexColor("#E5E7EB")
_MID_GRAY  = colors.HexColor("#9CA3AF")

# Export column order for CSV
_EXPORT_COLS = [
    "first_name", "last_name", "address", "city", "state", "zip_code",
    "phone", "email", "roof_age_years", "home_value", "owner_occupied",
    "storm_date", "storm_type", "storm_severity", "hail_size", "wind_speed",
]


# ── Public ──────────────────────────────────────────────────────────────────────

def build_leads_df(homeowner_df: pd.DataFrame) -> pd.DataFrame:
    """Return a clean export DataFrame from a homeowner DataFrame."""
    if homeowner_df.empty:
        return pd.DataFrame(columns=_EXPORT_COLS)
    df = homeowner_df.copy()
    for c in _EXPORT_COLS:
        if c not in df.columns:
            df[c] = None
    return df[_EXPORT_COLS].reset_index(drop=True)


def csv_bytes(homeowner_df: pd.DataFrame) -> bytes:
    """Return UTF-8 CSV bytes for a homeowner DataFrame."""
    return build_leads_df(homeowner_df).to_csv(index=False).encode("utf-8")


def pdf_bytes(
    zone_label: str,
    homeowner_df: pd.DataFrame,
    zone_summary: dict | None = None,
) -> bytes:
    """
    Build a professional homeowner lead report PDF.

    zone_summary keys (all optional):
        storm_date, storm_type, storm_severity, hail_size, wind_speed
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=letter,
        rightMargin=0.6 * inch, leftMargin=0.6 * inch,
        topMargin=0.6 * inch,  bottomMargin=0.6 * inch,
    )
    styles = getSampleStyleSheet()
    zs = zone_summary or {}
    story = []

    # ── Header ────────────────────────────────────────────────────────────────
    story.append(Paragraph("HAILHUNTER", ParagraphStyle(
        "HHTitle", parent=styles["Normal"],
        fontSize=22, leading=26, textColor=_ORANGE,
        fontName="Helvetica-Bold", spaceAfter=2,
    )))
    story.append(Paragraph("Homeowner Lead Report", ParagraphStyle(
        "HHSub", parent=styles["Normal"],
        fontSize=9, textColor=_MID_GRAY, fontName="Helvetica", spaceAfter=0,
    )))
    story.append(HRFlowable(width="100%", thickness=1, color=_ORANGE, spaceAfter=6))
    story.append(Paragraph(zone_label, ParagraphStyle(
        "HHZone", parent=styles["Normal"],
        fontSize=13, leading=16, textColor=_LIGHT_TXT,
        fontName="Helvetica-Bold", spaceBefore=8, spaceAfter=2,
    )))
    story.append(Paragraph(
        f"Generated {date.today().strftime('%B %d, %Y')}",
        ParagraphStyle("HHDate", parent=styles["Normal"],
                       fontSize=8, textColor=_MID_GRAY, fontName="Helvetica", spaceAfter=10),
    ))

    # ── Storm summary ─────────────────────────────────────────────────────────
    storm_date_str = ""
    if zs.get("storm_date"):
        sd = zs["storm_date"]
        storm_date_str = sd.strftime("%B %d, %Y") if hasattr(sd, "strftime") else str(sd)

    notes = []
    if zs.get("hail_size"):
        notes.append(f'Hail: {zs["hail_size"]:.2f}"')
    if zs.get("wind_speed"):
        notes.append(f'Wind: {int(zs["wind_speed"])} mph')

    storm_info = [
        ["Storm Date", "Type", "Severity", "Notes"],
        [
            storm_date_str,
            str(zs.get("storm_type", "—")),
            str(zs.get("storm_severity", "—")),
            "  ".join(notes) or "—",
        ],
    ]
    story.append(_pdf_table(storm_info, col_widths=None, hdr_color=_ORANGE, font_size=9))
    story.append(Spacer(1, 10))

    # ── Lead stats ────────────────────────────────────────────────────────────
    n = len(homeowner_df)
    if n:
        avg_roof  = homeowner_df["roof_age_years"].mean() if "roof_age_years" in homeowner_df else 0
        avg_val   = homeowner_df["home_value"].mean()     if "home_value"     in homeowner_df else 0
        owner_pct = homeowner_df["owner_occupied"].mean() if "owner_occupied"  in homeowner_df else 0
    else:
        avg_roof = avg_val = owner_pct = 0

    stats_data = [
        ["Total Leads", "Avg Roof Age", "Avg Home Value", "Owner-Occupied"],
        [
            f"{n:,}",
            f"{avg_roof:.1f} yrs",
            f"${avg_val:,.0f}",
            f"{owner_pct * 100:.0f}%",
        ],
    ]
    story.append(Paragraph("Lead Summary", ParagraphStyle(
        "SecHdr", parent=styles["Normal"],
        fontSize=9, fontName="Helvetica-Bold", textColor=_MID_GRAY, spaceAfter=4,
    )))
    story.append(_pdf_table(stats_data, col_widths=None, hdr_color=_DARK_GRAY, font_size=9))
    story.append(Spacer(1, 12))

    # ── Homeowner table (up to 100 rows) ──────────────────────────────────────
    show = homeowner_df.head(100)
    rows = [["Name", "Address", "City / State", "Phone", "Email", "Roof Age"]]
    for _, r in show.iterrows():
        rows.append([
            f"{r.get('first_name', '')} {r.get('last_name', '')}".strip(),
            str(r.get("address", "")),
            f"{r.get('city', '')}, {r.get('state', '')}",
            str(r.get("phone", "")),
            str(r.get("email", "")),
            f"{int(r['roof_age_years'])} yr" if pd.notna(r.get("roof_age_years")) else "",
        ])

    story.append(Paragraph("Homeowner Leads", ParagraphStyle(
        "SecHdr2", parent=styles["Normal"],
        fontSize=9, fontName="Helvetica-Bold", textColor=_MID_GRAY, spaceAfter=4,
    )))
    story.append(_pdf_table(
        rows,
        col_widths=[1.2, 1.3, 1.0, 0.9, 1.5, 0.6],
        hdr_color=_DARK_GRAY,
        font_size=7,
    ))

    if n > 100:
        story.append(Paragraph(
            f"… {n - 100} additional leads not shown. Export CSV for full list.",
            ParagraphStyle("Footnote", parent=styles["Normal"],
                           fontSize=7, textColor=_MID_GRAY, spaceBefore=4),
        ))

    doc.build(story)
    return buf.getvalue()


def push_to_ghl(
    webhook_url: str,
    api_key: str,
    homeowner_df: pd.DataFrame,
) -> Tuple[bool, str]:
    """
    POST homeowner records as GHL contacts to *webhook_url*.

    Each row becomes one contact with tags: ["HailHunter", storm_type, severity].
    Returns (success: bool, message: str).

    # TODO: Add GHL API key and location ID in settings
    """
    if not webhook_url or not webhook_url.startswith("http"):
        return False, "Invalid webhook URL."
    if homeowner_df.empty:
        return False, "No homeowner records to push."

    def _contact(r: pd.Series) -> dict:
        storm_type = str(r.get("storm_type", "Storm"))
        sev        = int(r.get("storm_severity", 0))
        from utils.constants import SEVERITY_LABELS
        sev_label  = SEVERITY_LABELS.get(max(1, min(4, sev)), "Unknown")
        return {
            "firstName":  str(r.get("first_name", "")),
            "lastName":   str(r.get("last_name", "")),
            "phone":      str(r.get("phone", "")),
            "email":      str(r.get("email", "")),
            "address1":   str(r.get("address", "")),
            "city":       str(r.get("city", "")),
            "state":      str(r.get("state", "")),
            "postalCode": str(r.get("zip_code", "")),
            "tags":       ["HailHunter", storm_type, sev_label],
            "customField": {
                "roof_age_years": int(r["roof_age_years"]) if pd.notna(r.get("roof_age_years")) else None,
                "home_value":     int(r["home_value"])     if pd.notna(r.get("home_value"))     else None,
                "storm_date":     str(r.get("storm_date", "")),
            },
        }

    payload = {
        "source":        "HailHunter",
        "exported":      date.today().isoformat(),
        "contact_count": len(homeowner_df),
        "contacts":      [_contact(r) for _, r in homeowner_df.iterrows()],
    }

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        resp = requests.post(webhook_url, json=payload, headers=headers, timeout=10)
        if resp.status_code < 300:
            return True, f"Pushed {len(homeowner_df)} contacts (HTTP {resp.status_code})."
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
    """Build a styled reportlab Table. First row is treated as header."""
    page_w = letter[0] - 1.2 * inch

    if col_widths:
        total = sum(col_widths)
        cw = [w / total * page_w for w in col_widths]
    else:
        n_cols = len(data[0]) if data else 1
        cw = [page_w / n_cols] * n_cols

    tbl = Table(data, colWidths=cw, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), hdr_color),
        ("TEXTCOLOR",     (0, 0), (-1, 0), _LIGHT_TXT),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), font_size),
        ("TOPPADDING",    (0, 0), (-1, 0), 5),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 5),
        ("FONTNAME",      (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",      (0, 1), (-1, -1), font_size),
        ("TEXTCOLOR",     (0, 1), (-1, -1), colors.HexColor("#374151")),
        ("TOPPADDING",    (0, 1), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 3),
        ("GRID",          (0, 0), (-1, -1), 0.25, colors.HexColor("#E5E7EB")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#F9FAFB")]),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return tbl
