"""
MaajiKids — Servicio de PDFs (ReportLab)
Genera reportes PDF con logo institucional.
"""
import os
import io
import logging
from datetime import date, datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, HRFlowable,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from flask import current_app

logger = logging.getLogger(__name__)

# Colores corporativos MaajiKids
COLOR_PINK = colors.HexColor("#E91E8C")
COLOR_TEAL = colors.HexColor("#4DB6AC")
COLOR_LIGHT = colors.HexColor("#FFF0F8")
COLOR_GRAY = colors.HexColor("#666666")
COLOR_DARK = colors.HexColor("#333333")


def _get_logo_path() -> str | None:
    logo = current_app.config.get("LOGO_PATH", "static/logo/maajikids_logo.png")
    # Prueba ruta absoluta y relativa
    if os.path.isabs(logo) and os.path.exists(logo):
        return logo
    base = current_app.root_path
    full = os.path.join(base, "..", logo)
    if os.path.exists(full):
        return os.path.abspath(full)
    return None


def _build_header(story: list, title: str, subtitle: str = "") -> None:
    """Header con logo + título + línea decorativa."""
    styles = getSampleStyleSheet()

    logo_path = _get_logo_path()
    header_data = []

    if logo_path:
        try:
            logo_img = Image(logo_path, width=3*cm, height=3*cm, kind="proportional")
            header_data = [[logo_img, ""]]
        except Exception:
            logo_img = None

    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontSize=18,
        textColor=COLOR_PINK,
        spaceAfter=4,
        alignment=TA_LEFT,
    )
    sub_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontSize=10,
        textColor=COLOR_GRAY,
        alignment=TA_LEFT,
    )
    center_style = ParagraphStyle(
        "CenterText",
        parent=styles["Normal"],
        fontSize=8,
        textColor=COLOR_GRAY,
        alignment=TA_RIGHT,
    )

    title_para = Paragraph(title, title_style)
    sub_para = Paragraph(subtitle or "Centro de Estimulación Temprana y Psicoprofilaxis", sub_style)
    date_para = Paragraph(f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}", center_style)

    if logo_path:
        try:
            logo_img = Image(logo_path, width=2.5*cm, height=2.5*cm)
            t = Table(
                [[logo_img, [title_para, sub_para], date_para]],
                colWidths=[3*cm, 11*cm, 4*cm],
            )
            t.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]))
            story.append(t)
        except Exception:
            story.append(title_para)
            story.append(sub_para)
    else:
        story.append(title_para)
        story.append(sub_para)

    story.append(Spacer(1, 0.3*cm))
    story.append(HRFlowable(width="100%", thickness=2, color=COLOR_PINK))
    story.append(Spacer(1, 0.5*cm))


def _section_title(text: str) -> Paragraph:
    style = ParagraphStyle(
        "SectionTitle",
        fontSize=12,
        textColor=COLOR_PINK,
        fontName="Helvetica-Bold",
        spaceAfter=6,
        spaceBefore=12,
    )
    return Paragraph(text, style)


def _body_text(text: str, bold: bool = False) -> Paragraph:
    style = ParagraphStyle(
        "Body",
        fontSize=10,
        textColor=COLOR_DARK,
        fontName="Helvetica-Bold" if bold else "Helvetica",
        spaceAfter=4,
        leading=14,
    )
    return Paragraph(text, style)


def _table_style_default() -> TableStyle:
    return TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), COLOR_PINK),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_LIGHT]),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROWHEIGHT", (0, 0), (-1, -1), 20),
    ])


# ── Reporte de evaluaciones de un niño ────────────────────────────────────────
def generate_child_evaluations_pdf(child: dict, evaluations: list[dict]) -> bytes:
    """PDF con todas las evaluaciones de un niño."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm,
    )
    story = []

    _build_header(story, "REPORTE DE EVALUACIONES", child.get("full_name", ""))

    # Info del niño
    story.append(_section_title("Datos del Niño/a"))
    info = [
        ["Nombre completo:", child.get("full_name", "")],
        ["Fecha de nacimiento:", child.get("date_of_birth", "")],
        ["Edad:", f"{child.get('age_months', 0)} meses ({child.get('age_years', 0)} años)"],
        ["Género:", child.get("gender", "")],
    ]
    info_table = Table(info, colWidths=[5*cm, 12*cm])
    info_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (0, -1), COLOR_PINK),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.5*cm))

    if not evaluations:
        story.append(_body_text("No hay evaluaciones registradas para este niño/a."))
    else:
        story.append(_section_title(f"Evaluaciones ({len(evaluations)} registros)"))
        headers = ["Fecha", "Taller", "Cognitivo", "Motor", "Lenguaje", "Socioemoc.", "Promedio"]
        rows = [headers]
        for ev in evaluations:
            scores = ev.get("scores", {})
            rows.append([
                ev.get("eval_date", ""),
                ev.get("workshop_title", ""),
                f"{scores.get('cognitive', 0):.1f}",
                f"{scores.get('motor', 0):.1f}",
                f"{scores.get('language', 0):.1f}",
                f"{scores.get('social', 0):.1f}",
                f"{scores.get('average', 0):.2f}",
            ])
        tbl = Table(rows, colWidths=[2.5*cm, 4.5*cm, 2*cm, 2*cm, 2*cm, 2.5*cm, 2.5*cm])
        tbl.setStyle(_table_style_default())
        story.append(tbl)

        # Observaciones
        for ev in evaluations:
            if ev.get("observations"):
                story.append(Spacer(1, 0.3*cm))
                story.append(_body_text(f"Observación ({ev.get('eval_date', '')}):", bold=True))
                story.append(_body_text(ev["observations"]))

    doc.build(story)
    return buffer.getvalue()


# ── Reporte de recomendaciones de un niño ─────────────────────────────────────
def generate_child_recommendations_pdf(child: dict, recommendations: list[dict]) -> bytes:
    """PDF con todas las recomendaciones IA del niño."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm,
    )
    story = []
    _build_header(story, "RECOMENDACIONES IA", child.get("full_name", ""))

    story.append(_section_title("Datos del Niño/a"))
    story.append(_body_text(f"<b>Nombre:</b> {child.get('full_name', '')}"))
    story.append(_body_text(f"<b>Edad:</b> {child.get('age_months', 0)} meses"))
    story.append(Spacer(1, 0.5*cm))

    if not recommendations:
        story.append(_body_text("No hay recomendaciones disponibles para este niño/a."))
    else:
        for i, rec in enumerate(recommendations, 1):
            story.append(_section_title(f"Recomendación #{i} — {rec.get('generated_at', '')[:10]}"))
            text = rec.get("recommendations_text", "")
            for line in text.split("\n"):
                if line.strip():
                    story.append(_body_text(line))
            story.append(HRFlowable(width="100%", thickness=0.5, color=COLOR_TEAL))

    doc.build(story)
    return buffer.getvalue()


# ── Reporte de pagos ───────────────────────────────────────────────────────────
def generate_payments_pdf(orders: list[dict], desde: str = "", hasta: str = "") -> bytes:
    """PDF de reporte de pagos aprobados."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm,
    )
    story = []
    periodo = f"{desde} – {hasta}" if desde or hasta else "Todos"
    _build_header(story, "REPORTE DE PAGOS", f"Período: {periodo}")

    if not orders:
        story.append(_body_text("No hay pagos registrados en el período seleccionado."))
    else:
        total = sum(float(o.get("total_amount", 0)) for o in orders)
        story.append(_body_text(f"<b>Total de órdenes:</b> {len(orders)}   |   "
                                f"<b>Monto total:</b> S/ {total:.2f}", bold=True))
        story.append(Spacer(1, 0.3*cm))

        headers = ["Orden", "Padre/Madre", "Monto (S/)", "Fecha Pago"]
        rows = [headers]
        for o in orders:
            rows.append([
                f"#{o.get('id', '')}",
                o.get("parent_name", ""),
                f"{float(o.get('total_amount', 0)):.2f}",
                o.get("paid_at", "")[:10] if o.get("paid_at") else "",
            ])
        tbl = Table(rows, colWidths=[2*cm, 9*cm, 3.5*cm, 3.5*cm])
        tbl.setStyle(_table_style_default())
        story.append(tbl)

    doc.build(story)
    return buffer.getvalue()


# ── Reporte de inscripciones activas ──────────────────────────────────────────
def generate_enrollments_pdf(enrollments: list[dict]) -> bytes:
    """PDF de inscripciones activas."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm,
    )
    story = []
    _build_header(story, "INSCRIPCIONES ACTIVAS")

    if not enrollments:
        story.append(_body_text("No hay inscripciones activas registradas."))
    else:
        story.append(_body_text(f"<b>Total inscripciones activas:</b> {len(enrollments)}", bold=True))
        story.append(Spacer(1, 0.3*cm))
        headers = ["Niño/a", "Taller", "Padre/Madre", "Fecha Inscripción"]
        rows = [headers]
        for e in enrollments:
            rows.append([
                e.get("child_name", ""),
                e.get("workshop_title", ""),
                e.get("parent_name", ""),
                e.get("enrolled_at", "")[:10] if e.get("enrolled_at") else "",
            ])
        tbl = Table(rows, colWidths=[5*cm, 5*cm, 4.5*cm, 3.5*cm])
        tbl.setStyle(_table_style_default())
        story.append(tbl)

    doc.build(story)
    return buffer.getvalue()


# ── Reporte: lista de niños de un taller ─────────────────────────────────────
def generate_workshop_children_pdf(workshop: dict, children: list[dict]) -> bytes:
    """PDF con lista de niños inscritos en un taller."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm,
    )
    story = []
    _build_header(story, workshop.get("title", "TALLER"), "LISTA DE NIÑOS INSCRITOS")

    story.append(_body_text(f"<b>Taller:</b> {workshop.get('title', '')}"))
    story.append(_body_text(f"<b>Horario:</b> {workshop.get('schedule', '')}"))
    story.append(_body_text(f"<b>Profesor:</b> {workshop.get('teacher_name', 'Sin asignar')}"))
    story.append(_body_text(f"<b>Inscritos:</b> {len(children)} / {workshop.get('max_capacity', 0)}"))
    story.append(Spacer(1, 0.5*cm))

    if not children:
        story.append(_body_text("No hay niños inscritos en este taller."))
    else:
        headers = ["#", "Nombre del Niño/a", "Edad", "DNI Verificado", "Padre/Madre"]
        rows = [headers]
        for i, c in enumerate(children, 1):
            rows.append([
                str(i),
                c.get("full_name", ""),
                f"{c.get('age_months', 0)} m",
                "✓" if c.get("dni_verified") else "✗",
                c.get("parent_name", ""),
            ])
        tbl = Table(rows, colWidths=[1*cm, 6*cm, 2.5*cm, 3*cm, 5.5*cm])
        tbl.setStyle(_table_style_default())
        story.append(tbl)

    doc.build(story)
    return buffer.getvalue()
