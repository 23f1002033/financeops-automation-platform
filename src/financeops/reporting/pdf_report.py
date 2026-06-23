"""PDF executive report — headline KPIs, revenue chart, region table, anomalies."""
from __future__ import annotations

import datetime as dt
from io import BytesIO
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  
from reportlab.lib import colors  
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle  # noqa: E402
from reportlab.lib.units import cm  # noqa: E402
from reportlab.platypus import (  # noqa: E402
    Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from financeops.config import get_settings  # noqa: E402
from financeops.kpi.engine import region_performance, revenue_trend  # noqa: E402
from financeops.reporting.executive_summary import build_summary  # noqa: E402

settings = get_settings()

_NAVY = colors.HexColor("#0B2447")
_ACCENT = colors.HexColor("#19A7CE")
_GREY = colors.HexColor("#5C677D")


def _trend_chart_png() -> BytesIO | None:
    trend = revenue_trend("D")
    if trend.empty:
        return None
    fig, ax = plt.subplots(figsize=(7.2, 2.8))
    ax.plot(trend["period"], trend["revenue"], color="#19A7CE", linewidth=2)
    ax.fill_between(trend["period"], trend["revenue"], color="#19A7CE", alpha=0.12)
    ax.set_title("Daily Net Revenue", loc="left", fontsize=11, color="#0B2447", weight="bold")
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(labelsize=8)
    fig.autofmt_xdate()
    fig.tight_layout()
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    buf.seek(0)
    return buf


def generate_pdf_report(out_path: Path | None = None) -> Path:
    summary = build_summary()
    kpis = summary["kpis"]
    out_path = out_path or (settings.reports_dir / f"executive_report_{dt.date.today().isoformat()}.pdf")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("t", parent=styles["Title"], textColor=_NAVY, fontSize=20)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], textColor=_NAVY, fontSize=12)
    body = ParagraphStyle("b", parent=styles["BodyText"], fontSize=9.5, textColor=_GREY, leading=14)

    doc = SimpleDocTemplate(
        str(out_path), pagesize=A4,
        leftMargin=1.6 * cm, rightMargin=1.6 * cm, topMargin=1.4 * cm, bottomMargin=1.4 * cm,
    )
    story: list = []

    story.append(Paragraph("FinanceOps - Executive Summary", title_style))
    story.append(Paragraph(
        f"Period {summary['period']['start']} to {summary['period']['end']} "
        f"&nbsp;|&nbsp; generated {summary['generated_at']}", body))
    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph(summary["headline"], h2))
    story.append(Paragraph(summary["growth"], body))
    story.append(Spacer(1, 0.3 * cm))

    kpi_rows = [
        ["Revenue", f"Rs {kpis['revenue']:,.0f}", "Gross Margin", f"{kpis['gross_margin_pct']:.1f}%"],
        ["Orders", f"{kpis['orders']:,}", "Unique Customers", f"{kpis['unique_customers']:,}"],
        ["Return Rate", f"{kpis['return_rate_pct']:.1f}%", "Refund Rate", f"{kpis['refund_rate_pct']:.1f}%"],
        ["Retention", f"{kpis['retention_pct']:.1f}%", "Order Growth", f"{kpis['order_growth_pct']:.1f}%"],
    ]
    t = Table(kpi_rows, colWidths=[3.6 * cm, 4.0 * cm, 3.6 * cm, 4.0 * cm])
    t.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("TEXTCOLOR", (0, 0), (0, -1), _GREY),
        ("TEXTCOLOR", (2, 0), (2, -1), _GREY),
        ("TEXTCOLOR", (1, 0), (1, -1), _NAVY),
        ("TEXTCOLOR", (3, 0), (3, -1), _NAVY),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"),
        ("FONTNAME", (3, 0), (3, -1), "Helvetica-Bold"),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.whitesmoke, colors.white]),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.4 * cm))

    chart = _trend_chart_png()
    if chart:
        story.append(Image(chart, width=17 * cm, height=6.6 * cm))
        story.append(Spacer(1, 0.3 * cm))

    regions = region_performance()
    if not regions.empty:
        story.append(Paragraph("Region Performance", h2))
        data = [["Zone", "Revenue", "Orders", "Margin %"]] + [
            [r.zone, f"Rs {r.revenue:,.0f}", f"{int(r.orders):,}", f"{r.gross_margin_pct:.1f}%"]
            for r in regions.itertuples()
        ]
        rt = Table(data, colWidths=[4 * cm, 5 * cm, 4 * cm, 4 * cm])
        rt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), _NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(rt)
        story.append(Spacer(1, 0.4 * cm))

    story.append(Paragraph("Risks &amp; Anomalies", h2))
    for line in summary["risks"]:
        story.append(Paragraph(f"• {line}", body))
    for a in summary["anomalies_top"]:
        story.append(Paragraph(f"• [{a['severity'].upper()}] {a['message']}", body))

    doc.build(story)
    return out_path