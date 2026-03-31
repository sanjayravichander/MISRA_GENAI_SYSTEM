#!/usr/bin/env python3
"""
export_pdf.py  —  Milestone 2: PDF report exporter.
Generates a professional PDF from evaluated_fixes.json + run_001_audit.json.

Usage:
    python export_pdf.py <evaluated_fixes.json> <audit.json> <output.pdf>

Example:
    python export_pdf.py data/output/run_001/evaluated_fixes.json \\
                         data/output/run_001/run_001_audit.json   \\
                         data/output/run_001/misra_report.pdf
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable, NextPageTemplate, PageBreak, PageTemplate,
    Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)
from reportlab.platypus.frames import Frame
from reportlab.platypus.doctemplate import BaseDocTemplate

# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------

BRAND_BLUE   = colors.HexColor("#1F497D")
BRAND_MID    = colors.HexColor("#2E75B6")
BRAND_LIGHT  = colors.HexColor("#D9E2F3")
GREY_HEAD    = colors.HexColor("#404040")
GREY_BODY    = colors.HexColor("#222222")
GREY_LIGHT   = colors.HexColor("#F5F5F5")
CODE_BG      = colors.HexColor("#F2F2F2")
GREEN        = colors.HexColor("#1E7B34")
AMBER        = colors.HexColor("#D07800")
RED          = colors.HexColor("#C0392B")
WHITE        = colors.white
RULE_COLOR   = BRAND_MID


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_json(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def fmt_duration(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m}m {s}s" if m else f"{s}s"


def fmt_ts(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso)
        return dt.strftime("%d %b %Y  %H:%M:%S")
    except Exception:
        return iso


def conf_color(conf: str) -> colors.Color:
    return {"High": GREEN, "Medium": AMBER, "Low": RED}.get(conf, GREY_HEAD)


def risk_color(risk: str) -> colors.Color:
    return {"Low": GREEN, "Medium": AMBER, "High": RED,
            "Critical": RED}.get(risk, GREY_HEAD)


def clean_code(snippet: str) -> str:
    s = snippet.strip()
    for fence in ("```c", "```cpp", "```", "~~~"):
        s = s.replace(fence, "")
    return s.strip()


def safe_xml(text: str) -> str:
    """Escape characters that break reportlab XML parser in Paragraph."""
    return (str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;"))


# ---------------------------------------------------------------------------
# Style sheet
# ---------------------------------------------------------------------------

def make_styles() -> dict:
    base = getSampleStyleSheet()

    def s(name, **kw) -> ParagraphStyle:
        return ParagraphStyle(name, **kw)

    return {
        "cover_title": s("cover_title",
            fontName="Helvetica-Bold", fontSize=28, textColor=BRAND_BLUE,
            alignment=TA_CENTER, leading=36, spaceAfter=10),

        "cover_sub": s("cover_sub",
            fontName="Helvetica", fontSize=14, textColor=BRAND_MID,
            alignment=TA_CENTER, leading=20, spaceAfter=6),

        "cover_meta": s("cover_meta",
            fontName="Helvetica", fontSize=11, textColor=GREY_HEAD,
            alignment=TA_CENTER, leading=18, spaceAfter=4),

        "cover_small": s("cover_small",
            fontName="Helvetica-Oblique", fontSize=9, textColor=colors.grey,
            alignment=TA_CENTER, leading=14),

        "h1": s("h1",
            fontName="Helvetica-Bold", fontSize=16, textColor=BRAND_BLUE,
            leading=20, spaceBefore=18, spaceAfter=8),

        "h2": s("h2",
            fontName="Helvetica-Bold", fontSize=13, textColor=BRAND_MID,
            leading=17, spaceBefore=14, spaceAfter=6),

        "h3": s("h3",
            fontName="Helvetica-Bold", fontSize=11, textColor=GREY_HEAD,
            leading=15, spaceBefore=10, spaceAfter=4),

        "body": s("body",
            fontName="Helvetica", fontSize=10, textColor=GREY_BODY,
            leading=14, spaceAfter=6),

        "body_italic": s("body_italic",
            fontName="Helvetica-Oblique", fontSize=9, textColor=GREY_HEAD,
            leading=13, spaceAfter=4),

        "label": s("label",
            fontName="Helvetica-Bold", fontSize=10, textColor=GREY_HEAD,
            leading=14, spaceAfter=2),

        "code": s("code",
            fontName="Courier", fontSize=8, textColor=colors.HexColor("#1A1A1A"),
            leading=11, spaceAfter=4, backColor=CODE_BG,
            leftIndent=8, rightIndent=8),

        "table_header": s("table_header",
            fontName="Helvetica-Bold", fontSize=10, textColor=WHITE,
            alignment=TA_LEFT, leading=13),

        "table_cell": s("table_cell",
            fontName="Helvetica", fontSize=9, textColor=GREY_BODY,
            leading=12),

        "table_cell_bold": s("table_cell_bold",
            fontName="Helvetica-Bold", fontSize=9, textColor=GREY_HEAD,
            leading=12),

        "note": s("note",
            fontName="Helvetica-Oblique", fontSize=9, textColor=colors.HexColor("#444444"),
            leading=13, leftIndent=12, spaceAfter=4),

        "corrected_badge": s("corrected_badge",
            fontName="Helvetica-Bold", fontSize=9, textColor=GREEN,
            leading=13, spaceAfter=4),

        "manual_badge": s("manual_badge",
            fontName="Helvetica-Bold", fontSize=10, textColor=RED,
            leading=14, spaceAfter=4),
    }


# ---------------------------------------------------------------------------
# Page template with header + footer
# ---------------------------------------------------------------------------

class MisraDocTemplate(BaseDocTemplate):
    def __init__(self, filename, run_id, **kwargs):
        self.run_id = run_id
        BaseDocTemplate.__init__(self, filename, **kwargs)
        W, H = letter
        margin = 0.75 * inch

        # Cover page — no header/footer
        cover_frame = Frame(margin, margin, W - 2*margin, H - 2*margin,
                            id="cover_frame")
        cover_tpl = PageTemplate(id="Cover", frames=[cover_frame],
                                 onPage=self._cover_page)

        # Normal pages — with header + footer
        body_frame = Frame(margin, margin + 0.4*inch,
                           W - 2*margin, H - 2*margin - 0.7*inch,
                           id="body_frame")
        body_tpl = PageTemplate(id="Body", frames=[body_frame],
                                onPage=self._body_page)

        self.addPageTemplates([cover_tpl, body_tpl])

    def _cover_page(self, canvas, doc):
        pass  # no header/footer on cover

    def _body_page(self, canvas, doc):
        W, H = letter
        margin = 0.75 * inch
        canvas.saveState()

        # Header line
        canvas.setStrokeColor(BRAND_MID)
        canvas.setLineWidth(1.2)
        canvas.line(margin, H - margin + 4, W - margin, H - margin + 4)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(GREY_HEAD)
        canvas.drawString(margin, H - margin + 8,
                          f"MISRA C Compliance Report  |  Run: {self.run_id}")

        # Footer line
        canvas.setStrokeColor(BRAND_MID)
        canvas.line(margin, margin - 4, W - margin, margin - 4)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.grey)
        canvas.drawString(margin, margin - 16,
                          "MISRA GenAI System  —  Confidential")
        canvas.drawRightString(W - margin, margin - 16,
                               f"Page {doc.page}")

        canvas.restoreState()


# ---------------------------------------------------------------------------
# Cover page
# ---------------------------------------------------------------------------

def build_cover(styles, run_id, started_at, completed_at, total_dur, excel_src) -> List:
    story = []
    story.append(Spacer(1, 1.8 * inch))
    story.append(Paragraph("MISRA C Compliance Report", styles["cover_title"]))
    story.append(Paragraph("Automated Static Analysis &amp; Fix Suggestions",
                            styles["cover_sub"]))
    story.append(HRFlowable(width="80%", thickness=1.5, color=BRAND_MID,
                             spaceAfter=16, spaceBefore=8))
    story.append(Paragraph(f"Run ID: {safe_xml(run_id)}", styles["cover_meta"]))
    story.append(Paragraph(f"Started:&nbsp;&nbsp; {safe_xml(started_at)}", styles["cover_meta"]))
    story.append(Paragraph(f"Completed: {safe_xml(completed_at)}", styles["cover_meta"]))
    story.append(Paragraph(f"Duration: {safe_xml(total_dur)}", styles["cover_meta"]))
    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph(f"Source: {safe_xml(excel_src)}", styles["cover_small"]))
    story.append(Spacer(1, 2.5 * inch))
    story.append(Paragraph("Generated by MISRA GenAI System",
                            styles["cover_small"]))
    story.append(NextPageTemplate("Body"))
    story.append(PageBreak())
    return story


# ---------------------------------------------------------------------------
# Executive summary
# ---------------------------------------------------------------------------

def build_summary(styles, fixes_data, audit) -> List:
    story = []
    story.append(Paragraph("Executive Summary", styles["h1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=RULE_COLOR,
                             spaceAfter=10))

    w_count   = fixes_data.get("warning_count", 0)
    c_high    = fixes_data.get("confidence_high", 0)
    c_medium  = fixes_data.get("confidence_medium", 0)
    c_low     = fixes_data.get("confidence_low", 0)
    manual    = fixes_data.get("needs_manual_review", 0)
    corrected = fixes_data.get("fixes_corrected", 0)

    # Quality metrics table
    def metric_row(label, value, val_color=None):
        v_style = ParagraphStyle("v", fontName="Helvetica-Bold", fontSize=10,
                                  textColor=val_color or GREY_BODY, leading=13)
        return [
            Paragraph(label, styles["table_cell_bold"]),
            Paragraph(str(value), v_style),
        ]

    quality_data = [
        [Paragraph("Metric", styles["table_header"]),
         Paragraph("Value",  styles["table_header"])],
        metric_row("Total Warnings", w_count),
        metric_row("High Confidence",   c_high,   GREEN),
        metric_row("Medium Confidence", c_medium, AMBER),
        metric_row("Low Confidence",    c_low,    RED),
        metric_row("Needs Manual Review", manual, RED if manual > 0 else GREEN),
        metric_row("Fixes Auto-corrected by Evaluator", corrected),
    ]

    col_w = [3.5 * inch, 3.0 * inch]
    q_table = Table(quality_data, colWidths=col_w)
    q_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_BLUE),
        ("BACKGROUND", (0, 1), (-1, -1), WHITE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, GREY_LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CCCCCC")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
    ]))
    story.append(q_table)
    story.append(Spacer(1, 0.25 * inch))

    # Pipeline timing table
    story.append(Paragraph("Pipeline Timing", styles["h2"]))
    phases = audit.get("phases", {})
    p6a = phases.get("6a", {})
    p6b = phases.get("6b", {})
    p7  = phases.get("7",  {})
    p8  = phases.get("8",  {})
    total_dur = fmt_duration(audit.get("total_duration_s", 0))

    def phase_row(phase, desc, dur, notes):
        return [
            Paragraph(phase, styles["table_cell_bold"]),
            Paragraph(desc,  styles["table_cell"]),
            Paragraph(dur,   styles["table_cell"]),
            Paragraph(notes, styles["table_cell"]),
        ]

    timing_data = [
        [Paragraph(h, styles["table_header"]) for h in
         ["Phase", "Description", "Duration", "Notes"]],
        phase_row("6a", "Parse Polyspace Excel report",
                  fmt_duration(p6a.get("duration_s", 0)),
                  f"{p6a.get('warnings', '—')} warnings"),
        phase_row("6b", "FAISS retrieval — MISRA context",
                  fmt_duration(p6b.get("duration_s", 0)), "—"),
        phase_row("7",  "Generate fix suggestions (LLM)",
                  fmt_duration(p7.get("duration_s", 0)),
                  f"{p7.get('fixes_generated','—')} generated, "
                  f"{p7.get('parse_errors','—')} errors"),
        phase_row("8",  "Evaluate & self-critique (LLM)",
                  fmt_duration(p8.get("duration_s", 0)),
                  f"{p8.get('fixes_corrected','—')} corrected, "
                  f"{p8.get('needs_manual_review','—')} flagged"),
        [Paragraph("Total", styles["table_cell_bold"]),
         Paragraph("End-to-end pipeline", styles["table_cell"]),
         Paragraph(total_dur, ParagraphStyle("tb", fontName="Helvetica-Bold",
                                              fontSize=9, textColor=GREY_HEAD, leading=12)),
         Paragraph("—", styles["table_cell"])],
    ]

    t_col_w = [0.7*inch, 2.5*inch, 1.1*inch, 2.2*inch]
    t_table = Table(timing_data, colWidths=t_col_w)
    t_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_BLUE),
        ("BACKGROUND", (0, -1), (-1, -1), BRAND_LIGHT),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [WHITE, GREY_LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CCCCCC")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
    ]))
    story.append(t_table)
    story.append(PageBreak())
    return story


# ---------------------------------------------------------------------------
# Warning detail section
# ---------------------------------------------------------------------------

def build_warning_section(w: Dict[str, Any], styles: dict) -> List:
    story = []

    conf   = w.get("overall_confidence") or \
             (w.get("evaluation") or {}).get("overall_confidence", "—")
    manual = w.get("needs_manual_review") or \
             (w.get("evaluation") or {}).get("needs_manual_review", False)

    # Warning heading
    story.append(Paragraph(
        f"{safe_xml(w.get('warning_id',''))}  —  {safe_xml(w.get('rule_id',''))}",
        styles["h2"]))

    # Confidence + manual review badge
    c_col = conf_color(conf)
    badge_style = ParagraphStyle("badge", fontName="Helvetica-Bold", fontSize=10,
                                  textColor=c_col, leading=13, spaceAfter=6)
    badge_text = f"Overall confidence: {safe_xml(conf)}"
    if manual:
        badge_text += '  <font color="#C0392B">  ⚠ MANUAL REVIEW REQUIRED</font>'
    story.append(Paragraph(badge_text, badge_style))

    # Explanation
    if w.get("explanation"):
        story.append(Paragraph("Explanation", styles["label"]))
        story.append(Paragraph(safe_xml(w["explanation"]), styles["body"]))

    # Risk analysis
    if w.get("risk_analysis"):
        story.append(Paragraph("Risk Analysis", styles["label"]))
        story.append(Paragraph(safe_xml(w["risk_analysis"]), styles["body"]))

    # Ranked fixes
    story.append(Paragraph("Ranked Fixes", styles["label"]))
    for fix in w.get("ranked_fixes", []):
        rank  = fix.get("rank", "?")
        desc  = fix.get("description", "")
        code  = clean_code(fix.get("code_change", ""))
        rat   = fix.get("rationale", "")
        risk  = fix.get("risk_level", "")
        fconf = fix.get("confidence", "")
        issues= fix.get("issues_found", [])
        was_corrected = fix.get("was_corrected", False)

        # Fix sub-heading
        rc = risk_color(risk)
        cc = conf_color(fconf)
        fix_head = ParagraphStyle(
            "fh", fontName="Helvetica-Bold", fontSize=10,
            textColor=BRAND_MID, leading=14, spaceBefore=8, spaceAfter=3)
        conf_part = (f'  <font color="#{_hex(cc)}">Conf: {safe_xml(fconf)}</font>'
                     if fconf else "")
        risk_part = (f'  <font color="#{_hex(rc)}">Risk: {safe_xml(risk)}</font>'
                     if risk else "")
        story.append(Paragraph(
            f"Fix {rank}{conf_part}{risk_part}", fix_head))

        if desc:
            story.append(Paragraph(safe_xml(desc), styles["body_italic"]))

        if code:
            story.append(Paragraph("Code change:", styles["label"]))
            for line in code.splitlines():
                story.append(Paragraph(safe_xml(line) or " ", styles["code"]))

        if rat:
            story.append(Paragraph(
                f"Rationale: {safe_xml(rat)}", styles["note"]))

        if issues:
            story.append(Paragraph("Issues found:", ParagraphStyle(
                "iss_lbl", fontName="Helvetica-Bold", fontSize=9,
                textColor=RED, leading=12, spaceAfter=2)))
            for iss in issues:
                story.append(Paragraph(
                    f"• {safe_xml(iss)}",
                    ParagraphStyle("iss", fontName="Helvetica", fontSize=9,
                                   textColor=RED, leading=12, leftIndent=10)))

        if was_corrected:
            story.append(Paragraph(
                "✔ Evaluator corrected this fix", styles["corrected_badge"]))

    # Evaluator notes
    notes = w.get("evaluator_notes") or \
            (w.get("evaluation") or {}).get("evaluator_notes", "")
    if notes:
        story.append(Paragraph("Evaluator Notes", styles["label"]))
        story.append(Paragraph(safe_xml(notes), styles["note"]))

    # Deviation advice
    if w.get("deviation_advice"):
        story.append(Paragraph("Deviation Advice", styles["label"]))
        story.append(Paragraph(safe_xml(w["deviation_advice"]), styles["body"]))

    story.append(HRFlowable(width="100%", thickness=0.5,
                             color=colors.HexColor("#CCCCCC"),
                             spaceAfter=10, spaceBefore=6))
    return story


def _hex(c: colors.Color) -> str:
    """Return 6-char hex string for a reportlab color (no leading #)."""
    try:
        r, g, b = int(c.red * 255), int(c.green * 255), int(c.blue * 255)
        return f"{r:02X}{g:02X}{b:02X}"
    except Exception:
        return "444444"


# ---------------------------------------------------------------------------
# Appendix
# ---------------------------------------------------------------------------

def build_appendix(styles, results: List[Dict]) -> List:
    story = []
    story.append(PageBreak())
    story.append(Paragraph("Appendix — Warnings Requiring Manual Review",
                            styles["h1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=RULE_COLOR,
                             spaceAfter=10))

    manual_warnings = [
        w for w in results
        if w.get("needs_manual_review") or
           (w.get("evaluation") or {}).get("needs_manual_review", False)
    ]

    if not manual_warnings:
        story.append(Paragraph(
            "No warnings require manual review.", styles["body_italic"]))
    else:
        for w in manual_warnings:
            notes = w.get("evaluator_notes") or \
                    (w.get("evaluation") or {}).get("evaluator_notes", "")
            story.append(Paragraph(
                f"{safe_xml(w.get('warning_id',''))}  —  "
                f"{safe_xml(w.get('rule_id',''))}",
                styles["h3"]))
            if notes:
                story.append(Paragraph(safe_xml(notes), styles["note"]))
            story.append(HRFlowable(width="100%", thickness=0.4,
                                     color=colors.HexColor("#CCCCCC"),
                                     spaceAfter=8, spaceBefore=4))
    return story


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 4:
        print("Usage: python export_pdf.py <evaluated_fixes.json> "
              "<audit.json> <output.pdf>")
        sys.exit(1)

    fixes_path = sys.argv[1]
    audit_path = sys.argv[2]
    out_path   = os.path.abspath(sys.argv[3])

    fixes_data = load_json(fixes_path)
    audit      = load_json(audit_path)

    run_id      = audit.get("run_id", "—")
    started_at  = fmt_ts(audit.get("started_at", ""))
    completed_at= fmt_ts(audit.get("completed_at", ""))
    total_dur   = fmt_duration(audit.get("total_duration_s", 0))
    excel_src   = audit.get("excel_report", "—")
    results     = fixes_data.get("results", [])

    styles = make_styles()

    doc = MisraDocTemplate(
        out_path,
        run_id=run_id,
        pagesize=letter,
        leftMargin=0.75*inch, rightMargin=0.75*inch,
        topMargin=0.75*inch,  bottomMargin=0.75*inch,
    )

    story = []

    # 1. Cover
    story += build_cover(styles, run_id, started_at, completed_at,
                         total_dur, excel_src)

    # 2. Executive summary
    story += build_summary(styles, fixes_data, audit)

    # 3. Warning details
    story.append(Paragraph("Warning Details", styles["h1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=RULE_COLOR,
                             spaceAfter=10))
    for w in results:
        story += build_warning_section(w, styles)

    # 4. Appendix
    story += build_appendix(styles, results)

    doc.build(story)

    size_kb = os.path.getsize(out_path) // 1024
    print(f"[OK] PDF report written → {out_path}  ({size_kb} KB)")


if __name__ == "__main__":
    main()