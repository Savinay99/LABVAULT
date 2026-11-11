"""Accessible, flowing PDF layout for academic laboratory manuals."""

from __future__ import annotations

from io import BytesIO
import re
from xml.sax.saxutils import escape as xml_escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


NAVY = colors.HexColor("#17345C")
BLUE = colors.HexColor("#2C5E91")
PURPLE = colors.HexColor("#7656C9")
INK = colors.HexColor("#263244")
MUTED = colors.HexColor("#5F6F82")
PALE_BLUE = colors.HexColor("#F2F6FB")
PALE_PURPLE = colors.HexColor("#F5F1FC")
RULE = colors.HexColor("#D9E1EA")


def _styles():
    return {
        "department": ParagraphStyle(
            "Department",
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
            textColor=BLUE,
            spaceAfter=6,
            uppercase=True,
        ),
        "title": ParagraphStyle(
            "ManualTitle",
            fontName="Helvetica-Bold",
            fontSize=23,
            leading=28,
            textColor=NAVY,
            spaceAfter=10,
            splitLongWords=1,
        ),
        "body": ParagraphStyle(
            "ManualBody",
            fontName="Helvetica",
            fontSize=10,
            leading=15,
            textColor=INK,
            spaceAfter=6,
            splitLongWords=1,
            allowWidows=0,
            allowOrphans=0,
        ),
        "section": ParagraphStyle(
            "ManualSection",
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            textColor=NAVY,
            spaceBefore=11,
            spaceAfter=7,
            keepWithNext=True,
        ),
        "meta_label": ParagraphStyle(
            "MetaLabel",
            fontName="Helvetica-Bold",
            fontSize=7,
            leading=9,
            textColor=MUTED,
        ),
        "meta_value": ParagraphStyle(
            "MetaValue",
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
            textColor=NAVY,
            splitLongWords=1,
        ),
        "bullet": ParagraphStyle(
            "ManualBullet",
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=INK,
            spaceAfter=3,
            splitLongWords=1,
        ),
        "equation": ParagraphStyle(
            "Equation",
            fontName="Courier",
            fontSize=9,
            leading=13,
            textColor=NAVY,
            spaceAfter=2,
            splitLongWords=1,
        ),
        "table_header": ParagraphStyle(
            "ObservationHeader",
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=11,
            textColor=colors.white,
            splitLongWords=1,
        ),
        "table_cell": ParagraphStyle(
            "ObservationCell",
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=INK,
            splitLongWords=1,
        ),
        "footer": ParagraphStyle(
            "Footer",
            fontName="Helvetica",
            fontSize=7,
            leading=9,
            textColor=MUTED,
        ),
    }


def _text(value):
    """Escape source text before passing it through ReportLab paragraph markup."""
    return xml_escape(str(value or ""), {"'": "&#39;", '"': "&quot;"})


def _formula_markup(value):
    """Format common plain-text sub/superscript notation without changing values."""
    formatted = _text(value)
    formatted = re.sub(
        r"\b([A-Za-z][A-Za-z0-9]*)_([A-Za-z0-9]+)\b",
        r"\1<sub>\2</sub>",
        formatted,
    )
    formatted = re.sub(
        r"\^\(([^)]+)\)|\^([A-Za-z0-9]+)",
        lambda match: f"<super>{match.group(1) or match.group(2)}</super>",
        formatted,
    )
    return formatted


def _split_procedure(procedure):
    """Split only explicitly numbered source steps; preserve other prose as-is."""
    parts = re.split(r"(?i)(?:^|\s)Step\s+(\d+)\s*:\s*", str(procedure or "").strip())
    if len(parts) < 3:
        return []
    steps = []
    for index in range(1, len(parts), 2):
        number = parts[index]
        text = parts[index + 1].strip() if index + 1 < len(parts) else ""
        if text:
            steps.append((number, text))
    return steps


def _draw_page(canvas, doc, course_code, experiment_number):
    canvas.saveState()
    page_width, page_height = letter
    left = doc.leftMargin
    right = page_width - doc.rightMargin

    canvas.setFillColor(NAVY)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(left, page_height - 0.43 * inch, "LABVAULT")
    canvas.setFillColor(PURPLE)
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(right, page_height - 0.43 * inch, "LABORATORY MANUAL")
    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.7)
    canvas.line(left, page_height - 0.54 * inch, right, page_height - 0.54 * inch)

    footer_y = 0.42 * inch
    canvas.setStrokeColor(RULE)
    canvas.line(left, footer_y + 0.17 * inch, right, footer_y + 0.17 * inch)
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 7)
    document_id = f"{course_code} | EXP {experiment_number} | LABVAULT"
    canvas.drawString(left, footer_y, document_id[:100])
    canvas.drawRightString(right, footer_y, f"Page {doc.page}")
    canvas.restoreState()


def build_lab_manual_pdf(
    *,
    title,
    subject_code,
    department,
    experiment_number,
    objective,
    apparatus,
    theory,
    procedure,
    formulas,
    viva_questions=None,
    observation_table=None,
    calculations=None,
    results=None,
    conclusion=None,
    references=None,
):
    """Build a paginated academic manual PDF using only supplied experiment data.

    Optional sections are omitted when their source data is absent; this avoids
    filling in experiment observations, results, conclusions, or references.
    """
    buffer = BytesIO()
    course_code = str(subject_code or "").strip()
    experiment_number = str(experiment_number or "").strip()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.72 * inch,
        leftMargin=0.72 * inch,
        topMargin=0.78 * inch,
        bottomMargin=0.68 * inch,
        title=f"{course_code}: {title}",
        author="LabVault",
        subject=f"Experiment {experiment_number} laboratory manual",
        pageCompression=1,
    )
    styles = _styles()
    width = letter[0] - doc.leftMargin - doc.rightMargin
    story = []

    story.append(Paragraph(_text(department).upper(), styles["department"]))
    story.append(Paragraph(_text(title), styles["title"]))
    story.append(
        HRFlowable(width="100%", thickness=2, color=PURPLE, spaceBefore=1, spaceAfter=12)
    )

    metadata = [
        [
            Paragraph("COURSE", styles["meta_label"]),
            Paragraph("EXPERIMENT", styles["meta_label"]),
        ],
        [
            Paragraph(_text(course_code), styles["meta_value"]),
            Paragraph(_text(experiment_number), styles["meta_value"]),
        ],
    ]
    meta = Table(metadata, colWidths=[width * 0.64, width * 0.36])
    meta.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PALE_BLUE),
                ("LINEBEFORE", (1, 0), (1, -1), 0.6, RULE),
                ("BOX", (0, 0), (-1, -1), 0.6, RULE),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, 0), 7),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 2),
                ("TOPPADDING", (0, 1), (-1, 1), 2),
                ("BOTTOMPADDING", (0, 1), (-1, 1), 8),
            ]
        )
    )
    story.extend([meta, Spacer(1, 7)])

    def section(heading, content):
        story.append(Paragraph(_text(heading), styles["section"]))
        story.append(content)

    section("Objective and Scope", Paragraph(_text(objective), styles["body"]))

    if apparatus:
        section("Required Apparatus and Software", Paragraph(_text(apparatus), styles["body"]))

    if theory:
        section("Theoretical Principles", Paragraph(_formula_markup(theory), styles["body"]))

    formula_items = [item.strip() for item in str(formulas or "").split("|") if item.strip()]
    if formula_items:
        formula_table = Table(
            [[Paragraph(_formula_markup(item), styles["equation"])] for item in formula_items],
            colWidths=[width],
            hAlign="LEFT",
        )
        formula_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), PALE_PURPLE),
                    ("LINEBEFORE", (0, 0), (0, -1), 3, PURPLE),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ]
            )
        )
        section("Equations", formula_table)

    procedure_steps = _split_procedure(procedure)
    if procedure_steps:
        flowables = [
            ListItem(Paragraph(_text(step_text), styles["bullet"]), leftIndent=7)
            for _, step_text in procedure_steps
        ]
        section(
            "Experimental Procedure",
            ListFlowable(
                flowables,
                bulletType="1",
                start=int(procedure_steps[0][0]),
                leftIndent=23,
                bulletFontName="Helvetica-Bold",
                bulletFontSize=9,
                bulletColor=BLUE,
                spaceAfter=5,
            ),
        )
    elif procedure:
        section("Experimental Procedure", Paragraph(_text(procedure), styles["body"]))

    if observation_table:
        columns = observation_table.get("columns", [])
        rows = observation_table.get("rows", [])
        if columns:
            table_data = [[Paragraph(_text(cell), styles["table_header"]) for cell in columns]]
            table_data.extend(
                [Paragraph(_text(cell), styles["table_cell"]) for cell in row]
                for row in rows
            )
            col_widths = [width / len(columns)] * len(columns)
            observations = Table(
                table_data,
                colWidths=col_widths,
                repeatRows=1,
                hAlign="LEFT",
                splitByRow=1,
            )
            observations.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE_BLUE]),
                        ("GRID", (0, 0), (-1, -1), 0.45, RULE),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 7),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                        ("TOPPADDING", (0, 0), (-1, -1), 6),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ]
                )
            )
            section("Sample Observation Table", observations)

    if calculations:
        section("Calculations", Paragraph(_text(calculations), styles["body"]))
    if results:
        section("Results", Paragraph(_text(results), styles["body"]))

    questions = [str(question).strip() for question in (viva_questions or []) if str(question).strip()]
    if questions:
        question_items = [
            ListItem(Paragraph(_text(question), styles["bullet"]), leftIndent=7)
            for question in questions
        ]
        section(
            "Viva Questions",
            ListFlowable(
                question_items,
                bulletType="1",
                start=1,
                leftIndent=23,
                bulletFontName="Helvetica-Bold",
                bulletFontSize=9,
                bulletColor=BLUE,
                spaceAfter=5,
            ),
        )

    if conclusion:
        section("Conclusion", Paragraph(_text(conclusion), styles["body"]))
    if references:
        reference_items = [str(ref).strip() for ref in references if str(ref).strip()]
        if reference_items:
            reference_flowables = [
                ListItem(Paragraph(_text(ref), styles["bullet"]), leftIndent=7)
                for ref in reference_items
            ]
            section(
                "References",
                ListFlowable(
                    reference_flowables,
                    bulletType="bullet",
                    start="square",
                    leftIndent=16,
                    bulletFontName="Helvetica",
                    bulletFontSize=6,
                    bulletColor=PURPLE,
                ),
            )

    draw = lambda canvas, document: _draw_page(
        canvas, document, course_code, experiment_number
    )
    doc.build(story, onFirstPage=draw, onLaterPages=draw)
    return buffer.getvalue()
