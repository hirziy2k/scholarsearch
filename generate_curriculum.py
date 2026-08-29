"""
Generate 50 diverse test PDFs for stress-testing a PDF->PPTX converter.

Each PDF targets a specific challenge category:
  01-05   Simple text (fonts, sizes, encoding)
  06-10   Multi-column layouts
  11-15   Tables with merged cells
  16-20   Image-heavy (shapes as stand-ins)
  21-25   RTL languages
  26-30   Large documents (10-50 pages)
  31-35   Edge cases (tiny text, overlapping, rotated)
  36-40   Mixed content
  41-45   Corrupted / tricky pages
  46-50   Enterprise documents (invoices, reports, forms)

All PDFs are saved to a ``curriculum/`` subdirectory relative to this script.
"""

import os
import math
import random
import string

from pathlib import Path

from reportlab.lib.pagesizes import A4, LETTER
from reportlab.lib.units import inch, mm
from reportlab.lib.colors import (
    HexColor, Color, black, white, red, blue, green, grey, lightgrey,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.graphics.shapes import Drawing, Rect, Circle, Line, String

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR / "curriculum"
OUTPUT_DIR.mkdir(exist_ok=True)

PAGE_W, PAGE_H = A4

STYLES = getSampleStyleSheet()
STYLE_H1 = ParagraphStyle(
    "H1C", parent=STYLES["Heading1"], fontSize=24,
    spaceAfter=12, textColor=HexColor("#1a1a2e"),
)
STYLE_H2 = ParagraphStyle(
    "H2C", parent=STYLES["Heading2"], fontSize=18,
    spaceAfter=8, textColor=HexColor("#16213e"),
)
STYLE_BODY = ParagraphStyle(
    "BodyC", parent=STYLES["Normal"], fontSize=11,
    leading=14, alignment=TA_JUSTIFY,
)
STYLE_SMALL = ParagraphStyle(
    "Small", parent=STYLES["Normal"], fontSize=7, leading=9,
)
STYLE_LARGE = ParagraphStyle(
    "Large", parent=STYLES["Normal"], fontSize=36,
    leading=40, alignment=TA_CENTER,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _p(name: str) -> Path:
    return OUTPUT_DIR / name


def _lorem(n: int = 5) -> str:
    words = [
        "lorem", "ipsum", "dolor", "sit", "amet", "consectetur",
        "adipiscing", "elit", "sed", "do", "eiusmod", "tempor",
        "incididunt", "ut", "labore", "et", "dolore", "magna",
        "aliqua", "enim", "ad", "minim", "veniam", "quis",
        "nostrud", "exercitation", "ullamco", "laboris", "nisi",
        "aliquip", "ex", "ea", "commodo", "consequat", "duis",
        "aute", "irure", "in", "reprehenderit", "voluptate",
        "velit", "esse", "cillum", "fugiat", "nulla", "pariatur",
        "excepteur", "sint", "occaecat", "cupidatat", "non",
        "proident", "sunt", "culpa", "qui", "officia", "deserunt",
        "mollit", "anim", "id", "est", "laborum", "intelligentia",
        "sapientia", "philosophia", "veritas", "universitas",
        "scientia", "humanitas", "cultura", "ars", "historia",
    ]
    rng = random.Random(42)
    out = []
    for _ in range(n):
        length = rng.randint(6, 14)
        sent = " ".join(rng.choice(words) for _ in range(length))
        out.append(sent.capitalize() + ".")
    return " ".join(out)


def _arabic(n: int = 4) -> str:
    frags = [
        "\u0628\u0633\u0645 \u0627\u0644\u0644\u0647 \u0627\u0644\u0631\u062d\u0645\u0646 \u0627\u0644\u0631\u062d\u064a\u0645",
        "\u0627\u0644\u062d\u0645\u062f \u0644\u0644\u0647 \u0631\u0628 \u0627\u0644\u0639\u0627\u0644\u0645\u064a\u0646",
        "\u0627\u0644\u0631\u062d\u0645\u0646 \u0627\u0644\u0631\u062d\u064a\u0645",
        "\u0645\u0627\u0644\u0643 \u064a\u0648\u0645 \u0627\u0644\u062f\u064a\u0646",
        "\u0625\u064a\u0627\u0643 \u0646\u0639\u0628\u062f \u0648\u0625\u064a\u0627\u0643 \u0646\u0633\u062a\u0639\u064a\u0646",
        "\u0627\u0647\u062f\u0646\u0627 \u0627\u0644\u0635\u0631\u0627\u0637 \u0627\u0644\u0645\u0633\u062a\u0642\u064a\u0645",
        "\u0635\u0631\u0627\u0637 \u0627\u0644\u0630\u064a\u0646 \u0623\u0646\u0639\u0645\u062a \u0639\u0644\u064a\u0647\u0645 \u063a\u064a\u0631 \u0627\u0644\u0645\u063a\u0636\u0648\u0628 \u0639\u0644\u064a\u0647\u0645",
        "\u0625\u0646 \u0641\u064a \u062e\u0644\u0642 \u0627\u0644\u0633\u0645\u0627\u0648\u0627\u062a \u0648\u0627\u0644\u0623\u0631\u0636 \u0648\u0627\u062e\u062a\u0644\u0627\u0641 \u0627\u0644\u0644\u064a\u0644 \u0648\u0627\u0644\u0646\u0647\u0627\u0631 \u0644\u0622\u064a\u0627\u062a",
    ]
    rng = random.Random(7)
    return " \u200b ".join(rng.choice(frags) for _ in range(n))


def _hebrew(n: int = 4) -> str:
    frags = [
        "\u05d1\u05e8\u05d0\u05e9\u05d9\u05ea \u05d1\u05e8\u05d0 \u05d0\u05dc\u05d4\u05d9\u05dd \u05d0\u05ea \u05d4\u05e9\u05de\u05d9\u05dd \u05d5\u05d0\u05ea \u05d4\u05d0\u05e8\u05e5",
        "\u05d5\u05d4\u05d0\u05e8\u05e5 \u05d4\u05d9\u05ea\u05d4 \u05ea\u05d4\u05d5 \u05d5\u05d1\u05d4\u05d5 \u05d5\u05d7\u05e9\u05da \u05e2\u05dc \u05e4\u05e0\u05d9 \u05ea\u05d4\u05d5\u05dd",
        "\u05d5\u05d9\u05d0\u05de\u05e8 \u05d0\u05dc\u05d4\u05d9\u05dd \u05d9\u05d4\u05d9 \u05d0\u05d5\u05e8 \u05d5\u05d9\u05d4\u05d9 \u05d0\u05d5\u05e8",
        "\u05d5\u05d9\u05e8\u05d0 \u05d0\u05dc\u05d4\u05d9\u05dd \u05d0\u05ea \u05d4\u05d0\u05d5\u05e8 \u05db\u05d9 \u05d8\u05d5\u05d1",
        "\u05d5\u05d9\u05d1\u05d3\u05dc \u05d0\u05dc\u05d4\u05d9\u05dd \u05d1\u05d9\u05df \u05d4\u05d0\u05d5\u05e8 \u05d5\u05d1\u05d9\u05df \u05d4\u05d7\u05e9\u05da",
        "\u05d5\u05d9\u05e7\u05e8\u05d0 \u05d0\u05dc\u05d4\u05d9\u05dd \u05dc\u05d0\u05d5\u05e8 \u05d5\u05dc\u05d7\u05e9\u05da \u05e7\u05e8\u05d0 \u05dc\u05d9\u05dc\u05d4",
        "\u05d5\u05d9\u05d4\u05d9 \u05e2\u05e8\u05d1 \u05d5\u05d9\u05d4\u05d9 \u05d1\u05e7\u05e8 \u05d9\u05d5\u05dd \u05d0\u05d7\u05d3",
    ]
    rng = random.Random(13)
    return " ".join(rng.choice(frags) for _ in range(n))


def _hf(c, title: str, pg: int):
    c.saveState()
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(HexColor("#333333"))
    c.drawString(50, PAGE_H - 35, title)
    c.line(50, PAGE_H - 40, PAGE_W - 50, PAGE_H - 40)
    c.setFont("Helvetica", 8)
    c.drawCentredString(PAGE_W / 2, 25, f"Page {pg}")
    c.line(50, 40, PAGE_W - 50, 40)
    c.restoreState()


def _rc(seed=None, light=False):
    r = random.Random(seed)
    cr = 0.5 + r.random() * 0.5 if light else r.random()
    cg = 0.5 + r.random() * 0.5 if light else r.random()
    cb = 0.5 + r.random() * 0.5 if light else r.random()
    return Color(cr, cg, cb)


# ===================================================================
# Category 1: Simple Text (01-05)
# ===================================================================

def gen_01():
    c = canvas.Canvas(str(_p("01_simple_text_helvetica.pdf")), pagesize=A4)
    _hf(c, "Simple Text - Helvetica", 1)
    c.setFont("Helvetica", 12)
    y = PAGE_H - 70
    for s in _lorem(30).split(". "):
        c.drawString(60, y, s.strip() + ".")
        y -= 18
        if y < 60:
            break
    c.save()


def gen_02():
    c = canvas.Canvas(str(_p("02_simple_text_times.pdf")), pagesize=A4)
    _hf(c, "Simple Text - Times", 1)
    c.setFont("Times-Roman", 12)
    y = PAGE_H - 70
    for s in _lorem(30).split(". "):
        c.drawString(60, y, s.strip() + ".")
        y -= 16
        if y < 60:
            break
    c.save()


def gen_03():
    c = canvas.Canvas(str(_p("03_simple_text_courier.pdf")), pagesize=A4)
    _hf(c, "Simple Text - Courier", 1)
    c.setFont("Courier", 11)
    y = PAGE_H - 70
    code = (
        "def fibonacci(n):\n"
        "    if n <= 1:\n"
        "        return n\n"
        "    return fibonacci(n-1) + fibonacci(n-2)\n"
        "\n"
        "# Compute first 20\n"
        "for i in range(20):\n"
        "    print(f'F({i}) = {fibonacci(i)}')\n"
    )
    for line in code.split("\n"):
        c.drawString(60, y, line)
        y -= 14
    c.save()


def gen_04():
    c = canvas.Canvas(str(_p("04_simple_mixed_sizes.pdf")), pagesize=A4)
    _hf(c, "Mixed Font Sizes", 1)
    y = PAGE_H - 80
    for sz in [32, 24, 18, 14, 12, 10, 8, 6]:
        c.setFont("Helvetica", sz)
        c.drawString(60, y, f"Size {sz}pt - The quick brown fox jumps over the lazy dog")
        y -= sz + 14
    c.save()


def gen_05():
    c = canvas.Canvas(str(_p("05_simple_colored_text.pdf")), pagesize=A4)
    _hf(c, "Colored Text", 1)
    palette = [
        ("#e63946", "Red section"), ("#457b9d", "Blue section"),
        ("#2a9d8f", "Teal section"), ("#e9c46a", "Gold section"),
        ("#264653", "Dark section"), ("#f4a261", "Orange section"),
    ]
    y = PAGE_H - 80
    for hx, lbl in palette:
        c.setFillColor(HexColor(hx))
        c.setFont("Helvetica-Bold", 14)
        c.drawString(60, y, lbl)
        c.setFont("Helvetica", 11)
        c.drawString(60, y - 18, _lorem(2))
        y -= 50
    c.save()


# ===================================================================
# Category 2: Multi-column layouts (06-10)
# ===================================================================

def _cols(c, texts, title, pages=1):
    margin, gap = 40, 20
    n = len(texts)
    cw = (PAGE_W - 2 * margin - (n - 1) * gap) / n
    for pg in range(pages):
        if pg > 0:
            c.showPage()
        _hf(c, title, pg + 1)
        y0 = PAGE_H - 70
        for ci in range(n):
            txt = texts[ci % len(texts)]
            x = margin + ci * (cw + gap)
            c.setFont("Helvetica", 10)
            y = y0
            for ln in txt.split("\n"):
                c.drawString(x, y, ln)
                y -= 13
                if y < 60:
                    break


def gen_06():
    c = canvas.Canvas(str(_p("06_two_columns.pdf")), pagesize=A4)
    _cols(c, [_lorem(20).replace(". ", ".\n"),
             _lorem(20).replace(". ", ".\n")], "Two Column Layout")
    c.showPage()
    c.save()


def gen_07():
    c = canvas.Canvas(str(_p("07_three_columns.pdf")), pagesize=A4)
    _cols(c, [_lorem(15).replace(". ", ".\n") for _ in range(3)],
          "Three Column Layout")
    c.showPage()
    c.save()


def gen_08():
    c = canvas.Canvas(str(_p("08_two_columns_multipage.pdf")), pagesize=A4)
    _cols(c, [_lorem(60).replace(". ", ".\n"),
             _lorem(60).replace(". ", ".\n")],
          "Two Column Multi-page", pages=3)
    c.showPage()
    c.save()


def gen_09():
    c = canvas.Canvas(str(_p("09_asymmetric_columns.pdf")), pagesize=A4)
    margin = 40
    sw = 120
    _hf(c, "Asymmetric Columns", 1)
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(HexColor("#457b9d"))
    y = PAGE_H - 70
    for item in ["Introduction", "Chapter 1", "Chapter 2",
                 "Chapter 3", "Chapter 4", "References", "Appendix"]:
        c.drawString(margin, y, f"  > {item}")
        y -= 16
    c.setFillColor(black)
    c.setFont("Helvetica", 11)
    y = PAGE_H - 70
    for ln in _lorem(35).replace(". ", ".\n").split("\n"):
        c.drawString(margin + sw + 20, y, ln)
        y -= 15
        if y < 60:
            break
    c.save()


def gen_10():
    c = canvas.Canvas(str(_p("10_column_dividers.pdf")), pagesize=A4)
    _hf(c, "Columns with Dividers", 1)
    margin, gap, n = 40, 30, 3
    cw = (PAGE_W - 2 * margin - (n - 1) * gap) / n
    for ci in range(n):
        x = margin + ci * (cw + gap)
        if ci > 0:
            c.setStrokeColor(lightgrey)
            c.setLineWidth(0.5)
            c.line(x - gap / 2, 50, x - gap / 2, PAGE_H - 50)
        c.setFont("Helvetica", 10)
        y = PAGE_H - 70
        for ln in _lorem(18).replace(". ", ".\n").split("\n"):
            c.drawString(x, y, ln)
            y -= 13
            if y < 60:
                break
    c.showPage()
    c.save()


# ===================================================================
# Category 3: Tables with merged cells (11-15)
# ===================================================================

def _make_table(data, col_widths=None):
    t = Table(data, colWidths=col_widths, repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), HexColor("#2c3e50")),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, HexColor("#ecf0f1")]),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]
    t.setStyle(TableStyle(style))
    return t


def _run_table(story, title, data, col_widths=None):
    story.append(Paragraph(title, STYLE_H2))
    story.append(Spacer(1, 8))
    story.append(_make_table(data, col_widths))
    story.append(Spacer(1, 20))


def gen_11():
    doc = SimpleDocTemplate(str(_p("11_table_simple.pdf")), pagesize=A4,
                            leftMargin=50, rightMargin=50)
    story = []
    header = ["ID", "Name", "Department", "Salary", "Start Date"]
    rows = [[str(i), f"Employee {i}", random.choice(["Engineering", "Sales", "HR", "Finance"]),
             f"${random.randint(40, 120)}k", f"202{random.randint(0,5)}-0{random.randint(1,9)}-15"]
            for i in range(1, 21)]
    _run_table(story, "Simple Employee Table", [header] + rows,
               col_widths=[40, 120, 100, 80, 100])
    doc.build(story)


def gen_12():
    doc = SimpleDocTemplate(str(_p("12_table_merged_header.pdf")), pagesize=A4,
                            leftMargin=50, rightMargin=50)
    story = []
    data = [
        ["", "Q1", "Q2", "Q3", "Q4"],
        ["Revenue", "$1.2M", "$1.5M", "$1.8M", "$2.1M"],
        ["Expenses", "$800K", "$900K", "$1.1M", "$1.0M"],
        ["Profit", "$400K", "$600K", "$700K", "$1.1M"],
    ]
    t = Table(data, colWidths=[100, 90, 90, 90, 90])
    t.setStyle(TableStyle([
        ("BACKGROUND", (1, 0), (-1, 0), HexColor("#2980b9")),
        ("TEXTCOLOR", (1, 0), (-1, 0), white),
        ("SPAN", (0, 0), (0, 0)),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, grey),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("BACKGROUND", (0, 1), (0, -1), HexColor("#d5e8d4")),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(Paragraph("Financial Summary", STYLE_H2))
    story.append(Spacer(1, 10))
    story.append(t)
    doc.build(story)


def gen_13():
    doc = SimpleDocTemplate(str(_p("13_table_spanning.pdf")), pagesize=A4,
                            leftMargin=40, rightMargin=40)
    story = []
    data = [
        ["Category", "Item", "Qty", "Unit Price", "Total"],
        ["Electronics", "Laptop", "5", "$999", "$4,995"],
        ["", "Mouse", "20", "$25", "$500"],
        ["", "Keyboard", "20", "$75", "$1,500"],
        ["Furniture", "Desk", "5", "$400", "$2,000"],
        ["", "Chair", "5", "$200", "$1,000"],
        ["", "", "", "Grand Total", "$9,995"],
    ]
    t = Table(data, colWidths=[80, 100, 50, 90, 90])
    t.setStyle(TableStyle([
        ("SPAN", (0, 1), (0, 3)),
        ("SPAN", (0, 4), (0, 6)),
        ("BACKGROUND", (0, 0), (-1, 0), HexColor("#8e44ad")),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (2, 0), (-1, -1), "CENTER"),
        ("LINEABOVE", (3, 6), (4, 6), 1.5, black),
        ("FONTNAME", (3, 6), (4, 6), "Helvetica-Bold"),
        ("BACKGROUND", (0, 1), (0, 3), HexColor("#fadbd8")),
        ("BACKGROUND", (0, 4), (0, 6), HexColor("#d5f5e3")),
    ]))
    story.append(Paragraph("Purchase Order with Spanned Cells", STYLE_H2))
    story.append(Spacer(1, 10))
    story.append(t)
    doc.build(story)


def gen_14():
    doc = SimpleDocTemplate(str(_p("14_table_colorful.pdf")), pagesize=A4,
                            leftMargin=50, rightMargin=50)
    story = []
    header = ["#", "Project", "Lead", "Status", "% Done"]
    statuses = ["Active", "On Hold", "Complete", "Planning"]
    rows = []
    for i in range(1, 31):
        rows.append([str(i), f"Project-{i:03d}",
                     f"Person {random.randint(1, 15)}",
                     random.choice(statuses),
                     f"{random.randint(0, 100)}%"])
    t = Table([header] + rows, colWidths=[30, 120, 90, 80, 60], repeatRows=1)
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), HexColor("#1abc9c")),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.3, grey),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (4, 0), (4, -1), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, HexColor("#e8f8f5")]),
    ]
    for ri, row in enumerate(rows, start=1):
        if row[3] == "Complete":
            style_cmds.append(("TEXTCOLOR", (3, ri), (3, ri), green))
        elif row[3] == "On Hold":
            style_cmds.append(("TEXTCOLOR", (3, ri), (3, ri), red))
    t.setStyle(TableStyle(style_cmds))
    story.append(Paragraph("Project Tracker (30 rows)", STYLE_H2))
    story.append(Spacer(1, 8))
    story.append(t)
    doc.build(story)


def gen_15():
    doc = SimpleDocTemplate(str(_p("15_table_nested_style.pdf")), pagesize=LETTER,
                            leftMargin=50, rightMargin=50)
    story = []
    data = [
        ["Name", "Math", "Science", "English", "History", "Art"],
        ["Alice", "95", "88", "92", "85", "90"],
        ["Bob", "78", "82", "88", "91", "75"],
        ["Carol", "92", "95", "85", "88", "96"],
        ["Dave", "65", "72", "78", "80", "70"],
        ["Eve", "88", "91", "95", "92", "88"],
    ]
    from reportlab.lib.units import inch
    t = Table(data, colWidths=[1.2*inch] + [0.9*inch]*5)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HexColor("#34495e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 1, grey),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 1), (0, -1), HexColor("#f0f0f0")),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(Paragraph("Student Grades", STYLE_H2))
    story.append(Spacer(1, 10))
    story.append(t)
    doc.build(story)


# ===================================================================
# Category 4: Image-heavy (shapes as stand-ins) (16-20)
# ===================================================================

def _draw_shapes_page(c, title, pg):
    _hf(c, title, pg)
    y = PAGE_H - 70
    colors = [_rc(i) for i in range(8)]
    for i in range(8):
        x = 60 + (i % 4) * 130
        row_y = y - (i // 4) * 130
        c.setFillColor(colors[i])
        c.rect(x, row_y - 100, 110, 100, fill=1, stroke=1)
        c.setFillColor(black)
        c.setFont("Helvetica", 8)
        c.drawCentredString(x + 55, row_y - 115, f"Shape {i + 1}")
    c.setFillColor(HexColor("#2c3e50"))
    c.setFont("Helvetica-Bold", 10)
    c.drawString(60, PAGE_H - 80, f"Page {pg} - 8 colored rectangles")


def gen_16():
    c = canvas.Canvas(str(_p("16_shapes_grid.pdf")), pagesize=A4)
    _draw_shapes_page(c, "Shape Grid - Rectangles", 1)
    c.showPage()
    c.save()


def gen_17():
    c = canvas.Canvas(str(_p("17_shapes_circles.pdf")), pagesize=A4)
    _hf(c, "Circles and Overlapping Shapes", 1)
    for i in range(12):
        x = 80 + (i % 4) * 130
        y = PAGE_H - 120 - (i // 4) * 160
        c.setFillColor(_rc(i * 3))
        c.setStrokeColor(_rc(i * 3 + 1))
        c.setLineWidth(2)
        c.circle(x + 50, y, 45, fill=1, stroke=1)
        c.setFillColor(black)
        c.setFont("Helvetica", 8)
        c.drawCentredString(x + 50, y - 60, f"Circle {i + 1}")
    c.showPage()
    c.save()


def gen_18():
    c = canvas.Canvas(str(_p("18_shapes_overlapping.pdf")), pagesize=A4)
    _hf(c, "Overlapping Semi-Transparent Shapes", 1)
    base_x, base_y = 150, PAGE_H / 2
    for i in range(6):
        c.saveState()
        c.setFillColor(Color(0.2 + i * 0.1, 0.3, 0.8 - i * 0.1, 0.4))
        angle = i * 60
        dx = 80 * math.cos(math.radians(angle))
        dy = 80 * math.sin(math.radians(angle))
        c.circle(base_x + dx, base_y + dy, 60, fill=1, stroke=0)
        c.restoreState()
    c.setFillColor(black)
    c.setFont("Helvetica", 9)
    c.drawCentredString(base_x, base_y - 110, "6 overlapping circles")
    c.showPage()
    c.save()


def gen_19():
    c = canvas.Canvas(str(_p("19_shapes_lines_arrows.pdf")), pagesize=A4)
    _hf(c, "Lines and Connectors", 1)
    nodes = [(100, 600), (250, 500), (400, 600), (200, 400),
             (350, 400), (100, 300), (300, 250), (450, 300)]
    c.setStrokeColor(HexColor("#2c3e50"))
    c.setLineWidth(1.5)
    for i in range(len(nodes) - 1):
        c.line(*nodes[i], *nodes[i + 1])
    for i, (x, y) in enumerate(nodes):
        c.setFillColor(_rc(i * 5))
        c.circle(x, y, 12, fill=1, stroke=1)
        c.setFillColor(black)
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(x, y - 3, str(i + 1))
    c.showPage()
    c.save()


def gen_20():
    c = canvas.Canvas(str(_p("20_shapes_bar_chart.pdf")), pagesize=A4)
    _hf(c, "Simulated Bar Chart", 1)
    data = [35, 65, 45, 80, 55, 70, 90, 40, 75, 60]
    labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct"]
    bar_w = 40
    gap = 10
    start_x = 60
    base_y = 100
    max_val = max(data)
    for i, (val, lbl) in enumerate(zip(data, labels)):
        x = start_x + i * (bar_w + gap)
        h = (val / max_val) * 350
        c.setFillColor(_rc(i * 7))
        c.rect(x, base_y, bar_w, h, fill=1, stroke=0)
        c.setFillColor(black)
        c.setFont("Helvetica", 8)
        c.drawCentredString(x + bar_w / 2, base_y - 14, lbl)
        c.drawCentredString(x + bar_w / 2, base_y + h + 8, str(val))
    c.setStrokeColor(grey)
    c.setLineWidth(0.5)
    c.line(start_x - 5, base_y, start_x + len(data) * (bar_w + gap), base_y)
    c.showPage()
    c.save()


# ===================================================================
# Category 5: RTL languages (21-25)
# ===================================================================

def gen_21():
    c = canvas.Canvas(str(_p("21_rtl_arabic.pdf")), pagesize=A4)
    _hf(c, "RTL - Arabic Text", 1)
    c.setFont("Helvetica", 14)
    y = PAGE_H - 80
    txt = _arabic(8)
    for fragment in txt.split(" \u200b "):
        c.drawRightString(PAGE_W - 60, y, fragment)
        y -= 24
    c.setFillColor(grey)
    c.setFont("Helvetica", 8)
    c.drawString(60, 80, "[Note: Arabic text rendered right-to-left as placeholder]")
    c.showPage()
    c.save()


def gen_22():
    c = canvas.Canvas(str(_p("22_rtl_hebrew.pdf")), pagesize=A4)
    _hf(c, "RTL - Hebrew Text", 1)
    c.setFont("Helvetica", 14)
    y = PAGE_H - 80
    txt = _hebrew(7)
    for fragment in txt.split(" "):
        c.drawRightString(PAGE_W - 60, y, fragment)
        y -= 24
    c.setFillColor(grey)
    c.setFont("Helvetica", 8)
    c.drawString(60, 80, "[Note: Hebrew text rendered RTL as placeholder]")
    c.showPage()
    c.save()


def gen_23():
    c = canvas.Canvas(str(_p("23_rtl_mixed_ltr_rtl.pdf")), pagesize=A4)
    _hf(c, "Mixed LTR + RTL Content", 1)
    y = PAGE_H - 80
    c.setFont("Helvetica", 11)
    c.setFillColor(black)
    c.drawString(60, y, "This is a left-to-right English paragraph.")
    y -= 20
    c.drawRightString(PAGE_W - 60, y, "\u0628\u0633\u0645 \u0627\u0644\u0644\u0647 \u0627\u0644\u0631\u062d\u0645\u0646 \u0627\u0644\u0631\u062d\u064a\u0645 - Arabic text here")
    y -= 20
    c.drawString(60, y, "Back to English text with numbers: 12345, $99.99")
    y -= 20
    c.drawRightString(PAGE_W - 60, y, "\u05d1\u05e8\u05d0\u05e9\u05d9\u05ea \u05d1\u05e8\u05d0 \u05d0\u05dc\u05d4\u05d9\u05dd - Hebrew text")
    y -= 20
    c.drawString(60, y, "Final English line with special chars: @#$%^&*()")
    c.showPage()
    c.save()


def gen_24():
    doc = SimpleDocTemplate(str(_p("24_rtl_table.pdf")), pagesize=A4,
                            leftMargin=50, rightMargin=50)
    story = []
    data = [
        ["\u0627\u0644\u0627\u0633\u0645", "\u0627\u0644\u0642\u0627\u0639\u062f\u0629", "\u0627\u0644\u0639\u062f\u062f"],
        ["\u0623\u062d\u0645\u062f", "\u0627\u0644\u0647\u0646\u062f\u0633\u0629", "5"],
        ["\u0645\u062d\u0645\u062f", "\u0627\u0644\u0643\u0647\u0631\u0628\u0627\u0621", "3"],
        ["\u0639\u0644\u064a", "\u0627\u0644\u0639\u0644\u0648\u0645", "8"],
    ]
    t = Table(data, colWidths=[120, 120, 80])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HexColor("#154360")),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, grey),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    story.append(Paragraph("\u062c\u062f\u0648\u0644 \u0627\u0644\u0645\u0648\u0627\u0631\u062f", STYLE_H2))
    story.append(Spacer(1, 10))
    story.append(t)
    doc.build(story)


def gen_25():
    c = canvas.Canvas(str(_p("25_rtl_multilingual_page.pdf")), pagesize=A4)
    _hf(c, "Multilingual Page", 1)
    y = PAGE_H - 80
    sections = [
        ("English", "The quick brown fox jumps over the lazy dog.", "Helvetica"),
        ("Arabic", "\u0628\u0633\u0645 \u0627\u0644\u0644\u0647 \u0627\u0644\u0631\u062d\u0645\u0646 \u0627\u0644\u0631\u062d\u064a\u0645", "Helvetica"),
        ("Hebrew", "\u05d1\u05e8\u05d0\u05e9\u05d9\u05ea \u05d1\u05e8\u05d0 \u05d0\u05dc\u05d4\u05d9\u05dd", "Helvetica"),
        ("English", "Multiple languages on one page for testing conversion.", "Helvetica"),
    ]
    c.setFont("Helvetica-Bold", 10)
    for lang, text, font in sections:
        c.setFillColor(HexColor("#2c3e50"))
        c.drawString(60, y, f"[{lang}]")
        c.setFont(font, 12)
        c.setFillColor(black)
        if lang in ("Arabic", "Hebrew"):
            c.drawRightString(PAGE_W - 60, y - 18, text)
        else:
            c.drawString(80, y - 18, text)
        y -= 50
    c.showPage()
    c.save()


# ===================================================================
# Category 6: Large documents (26-30)
# ===================================================================

def gen_26():
    c = canvas.Canvas(str(_p("26_large_10pages.pdf")), pagesize=A4)
    for pg in range(1, 11):
        _hf(c, f"Document - Page {pg} of 10", pg)
        c.setFont("Helvetica", 11)
        y = PAGE_H - 70
        for _ in range(30):
            c.drawString(60, y, _lorem(1))
            y -= 16
        if pg < 10:
            c.showPage()
    c.save()


def gen_27():
    c = canvas.Canvas(str(_p("27_large_25pages.pdf")), pagesize=A4)
    for pg in range(1, 26):
        _hf(c, f"Report Section {pg}", pg)
        c.setFont("Helvetica", 11)
        y = PAGE_H - 70
        c.setFont("Helvetica-Bold", 16)
        c.drawString(60, y, f"Chapter {pg}")
        y -= 30
        c.setFont("Helvetica", 11)
        for _ in range(25):
            c.drawString(60, y, _lorem(1))
            y -= 16
        c.setFont("Helvetica", 9)
        c.setFillColor(grey)
        c.drawString(60, 70, f"[Page {pg} - generated content for large document testing]")
        c.setFillColor(black)
        if pg < 25:
            c.showPage()
    c.save()


def gen_28():
    c = canvas.Canvas(str(_p("28_large_50pages.pdf")), pagesize=A4)
    rng = random.Random(99)
    for pg in range(1, 51):
        _hf(c, f"Manual Page {pg}", pg)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(60, PAGE_H - 70, f"Section {pg}: {rng.choice(['Overview', 'Details', 'Analysis', 'Summary', 'Appendix'])}")
        c.setFont("Helvetica", 10)
        y = PAGE_H - 100
        for _ in range(rng.randint(20, 30)):
            c.drawString(60, y, _lorem(1))
            y -= 14
        if pg < 50:
            c.showPage()
    c.save()


def gen_29():
    c = canvas.Canvas(str(_p("29_large_table_heavy.pdf")), pagesize=A4)
    for pg in range(1, 12):
        _hf(c, f"Data Table Page {pg}", pg)
        y = PAGE_H - 70
        c.setFont("Helvetica-Bold", 12)
        c.drawString(60, y, f"Table Set {pg}")
        y -= 20
        col_w = 70
        row_h = 14
        cols = 7
        for row in range(15):
            x = 60
            for ci in range(cols):
                c.setStrokeColor(lightgrey)
                c.setLineWidth(0.3)
                c.rect(x, y - row_h, col_w, row_h, fill=0, stroke=1)
                c.setFont("Helvetica", 7)
                c.drawCentredString(x + col_w / 2, y - row_h + 4,
                                    f"R{row}C{ci}")
                x += col_w
            y -= row_h
        if pg < 11:
            c.showPage()
    c.save()


def gen_30():
    c = canvas.Canvas(str(_p("30_large_chapter_book.pdf")), pagesize=LETTER)
    toc_pages = []
    random.seed(101)
    chapter_starts = {}
    ch_num = 0
    for pg in range(1, 21):
        _hf(c, f"Book - Page {pg}", pg)
        y = PAGE_H - 70
        if pg <= 3:
            c.setFont("Helvetica-Bold", 14)
            c.drawString(60, y, f"Table of Contents - Page {pg}")
            y -= 25
            c.setFont("Helvetica", 11)
            for i in range(1, 20):
                c.drawString(80, y, f"Chapter {i}: {''.join(random.choices(string.ascii_lowercase, k=random.randint(10,20)))} ... {random.randint(5,30)}")
                y -= 16
        else:
            if (pg - 4) % 2 == 0:
                ch_num += 1
                chapter_starts[ch_num] = pg
                c.setFont("Helvetica-Bold", 18)
                c.drawString(60, y, f"Chapter {ch_num}")
                y -= 30
                c.setFont("Helvetica", 10)
                for _ in range(random.randint(20, 30)):
                    c.drawString(60, y, _lorem(1))
                    y -= 14
            else:
                c.setFont("Helvetica", 10)
                for _ in range(random.randint(20, 30)):
                    c.drawString(60, y, _lorem(1))
                    y -= 14
        if pg < 20:
            c.showPage()
    c.save()


# ===================================================================
# Category 7: Edge cases (31-35)
# ===================================================================

def gen_31():
    c = canvas.Canvas(str(_p("31_edge_tiny_text.pdf")), pagesize=A4)
    _hf(c, "Edge Case: Tiny Text", 1)
    y = PAGE_H - 80
    for sz in [4, 3, 2.5, 2, 1.5, 1]:
        c.setFont("Helvetica", sz)
        c.drawString(60, y, f"Font {sz}pt: Lorem ipsum dolor sit amet consectetur adipiscing elit")
        y -= sz + 8
    c.setFont("Helvetica", 6)
    c.drawString(60, y - 20, "[Text above ranges from 4pt down to 1pt]")
    c.showPage()
    c.save()


def gen_32():
    c = canvas.Canvas(str(_p("32_edge_huge_text.pdf")), pagesize=A4)
    _hf(c, "Edge Case: Huge Text", 1)
    c.setFont("Helvetica-Bold", 72)
    c.drawCentredString(PAGE_W / 2, PAGE_H / 2 + 60, "HUGE")
    c.setFont("Helvetica-Bold", 48)
    c.drawCentredString(PAGE_W / 2, PAGE_H / 2 - 20, "TEXT")
    c.setFont("Helvetica", 14)
    c.drawCentredString(PAGE_W / 2, PAGE_H / 2 - 70, "72pt and 48pt on one page")
    c.showPage()
    c.save()


def gen_33():
    c = canvas.Canvas(str(_p("33_edge_overlapping.pdf")), pagesize=A4)
    _hf(c, "Edge Case: Overlapping Elements", 1)
    colors = [_rc(i) for i in range(10)]
    for i in range(10):
        c.saveState()
        c.setFillColor(Color(colors[i].red, colors[i].green, colors[i].blue, 0.5))
        x = 60 + i * 40
        y = 200 + (i % 3) * 80
        c.rect(x, y, 120, 60, fill=1, stroke=1)
        c.restoreState()
    c.setFillColor(black)
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(PAGE_W / 2, PAGE_H / 2, "OVERLAPPING")
    c.setFont("Helvetica", 12)
    for i in range(15):
        c.drawString(random.randint(50, 450), random.randint(100, 700),
                     _lorem(1))
    c.showPage()
    c.save()


def gen_34():
    c = canvas.Canvas(str(_p("34_edge_rotated_text.pdf")), pagesize=A4)
    _hf(c, "Edge Case: Rotated Text", 1)
    for angle in range(0, 360, 45):
        c.saveState()
        c.translate(PAGE_W / 2, PAGE_H / 2)
        c.rotate(angle)
        c.setFont("Helvetica-Bold", 14)
        c.setFillColor(_rc(angle))
        c.drawCentredString(0, 0, f"{angle} degrees")
        c.restoreState()
    c.showPage()
    c.save()


def gen_35():
    c = canvas.Canvas(str(_p("35_edge_zero_width_chars.pdf")), pagesize=A4)
    _hf(c, "Edge Case: Whitespace and Special Chars", 1)
    y = PAGE_H - 80
    c.setFont("Courier", 10)
    specials = [
        ("Spaces:", "    indented    with    spaces    "),
        ("Tabs:", "\t\tindented\twith\ttabs"),
        ("Mixed WS:", " \t \t mixed \t spaces \t and \t tabs \t "),
        ("Empty lines:", ""),
        ("Null chars:", "\x00\x01\x02\x03 visible text"),
        ("Backslashes:", "path\\to\\file\\\\double"),
        ("Quotes:", "'single' \"double\" \\\"escaped\\\""),
        ("Brackets:", "[{()}] <tag> &amp; entity"),
    ]
    for label, text in specials:
        c.setFont("Helvetica-Bold", 10)
        c.drawString(60, y, label)
        c.setFont("Courier", 10)
        c.drawString(180, y, text if text else "[EMPTY]")
        y -= 20
    c.showPage()
    c.save()


# ===================================================================
# Category 8: Mixed content (36-40)
# ===================================================================

def gen_36():
    doc = SimpleDocTemplate(str(_p("36_mixed_text_table.pdf")), pagesize=A4,
                            leftMargin=50, rightMargin=50)
    story = []
    story.append(Paragraph("Mixed Text and Tables", STYLE_H1))
    story.append(Paragraph(_lorem(5), STYLE_BODY))
    story.append(Spacer(1, 12))
    data = [["Item", "Qty", "Price"], ["Widget", "10", "$5.00"],
            ["Gadget", "5", "$12.00"], ["Doohickey", "3", "$8.50"]]
    story.append(_make_table(data, col_widths=[150, 80, 100]))
    story.append(Spacer(1, 12))
    story.append(Paragraph(_lorem(5), STYLE_BODY))
    doc.build(story)


def gen_37():
    c = canvas.Canvas(str(_p("37_mixed_text_shapes.pdf")), pagesize=A4)
    _hf(c, "Text and Shapes Mixed", 1)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(60, PAGE_H - 80, "Report with Graphics")
    c.setFont("Helvetica", 10)
    y = PAGE_H - 110
    for _ in range(8):
        c.drawString(60, y, _lorem(1))
        y -= 16
    c.setFillColor(_rc(42))
    c.rect(60, y - 150, 200, 150, fill=1, stroke=0)
    c.setFillColor(_rc(43))
    c.circle(400, y - 75, 60, fill=1, stroke=0)
    c.setFillColor(black)
    c.setFont("Helvetica", 9)
    c.drawString(60, y - 170, "Figure 1: Blue rectangle and green circle")
    c.showPage()
    c.save()


def gen_38():
    doc = SimpleDocTemplate(str(_p("38_mixed_full_page.pdf")), pagesize=A4,
                            leftMargin=50, rightMargin=50)
    story = []
    story.append(Paragraph("Comprehensive Mixed Document", STYLE_H1))
    story.append(Paragraph(_lorem(3), STYLE_BODY))
    story.append(Spacer(1, 10))
    data = [["Metric", "Q1", "Q2", "Q3"],
            ["Revenue", "$1M", "$1.5M", "$2M"],
            ["Users", "10K", "15K", "25K"]]
    story.append(_make_table(data, col_widths=[100, 80, 80, 80]))
    story.append(Spacer(1, 10))
    story.append(Paragraph(_lorem(4), STYLE_BODY))
    story.append(Spacer(1, 8))
    d = Drawing(400, 150)
    d.add(Rect(10, 10, 80, 130, fillColor=HexColor("#3498db")))
    d.add(Rect(110, 40, 80, 100, fillColor=HexColor("#e74c3c")))
    d.add(Rect(210, 70, 80, 70, fillColor=HexColor("#2ecc71")))
    d.add(Rect(310, 20, 80, 120, fillColor=HexColor("#f39c12")))
    story.append(d)
    story.append(Spacer(1, 10))
    story.append(Paragraph(_lorem(3), STYLE_BODY))
    doc.build(story)


def gen_39():
    c = canvas.Canvas(str(_p("39_mixed_headers_footers.pdf")), pagesize=A4)
    for pg in range(1, 4):
        _hf(c, f"Styled Document Page {pg}", pg)
        if pg == 1:
            c.setFont("Helvetica-Bold", 28)
            c.setFillColor(HexColor("#2c3e50"))
            c.drawCentredString(PAGE_W / 2, PAGE_H - 120, "Annual Report 2024")
            c.setFont("Helvetica", 14)
            c.setFillColor(HexColor("#7f8c8d"))
            c.drawCentredString(PAGE_W / 2, PAGE_H - 150, "Department of Testing")
            c.setFont("Helvetica", 11)
            c.setFillColor(black)
            y = PAGE_H - 200
            for _ in range(15):
                c.drawString(80, y, _lorem(1))
                y -= 16
        else:
            c.setFont("Helvetica", 11)
            y = PAGE_H - 70
            c.setFont("Helvetica-Bold", 14)
            c.drawString(60, y, f"Section {pg}")
            y -= 25
            c.setFont("Helvetica", 11)
            for _ in range(25):
                c.drawString(60, y, _lorem(1))
                y -= 16
        if pg < 3:
            c.showPage()
    c.save()


def gen_40():
    doc = SimpleDocTemplate(str(_p("40_mixed_bullet_lists.pdf")), pagesize=A4,
                            leftMargin=50, rightMargin=50)
    story = []
    story.append(Paragraph("Document with Lists", STYLE_H1))
    story.append(Paragraph("Key Features", STYLE_H2))
    bullets = [
        "First item with some description text",
        "Second item with more details",
        "Third item covering edge cases",
        "Fourth item for completeness",
        "Fifth item to round out the list",
    ]
    for b in bullets:
        story.append(Paragraph(f"&bull;&nbsp;&nbsp;{b}", STYLE_BODY))
        story.append(Spacer(1, 4))
    story.append(Spacer(1, 12))
    story.append(Paragraph("Summary Table", STYLE_H2))
    data = [["#", "Feature", "Status"], ["1", "Text extraction", "Done"],
            ["2", "Table detection", "In progress"], ["3", "Image handling", "Planned"]]
    story.append(_make_table(data, col_widths=[40, 180, 100]))
    story.append(Spacer(1, 12))
    story.append(Paragraph(_lorem(4), STYLE_BODY))
    doc.build(story)


# ===================================================================
# Category 9: Corrupted / tricky (41-45)
# ===================================================================

def gen_41():
    c = canvas.Canvas(str(_p("41_tricky_empty_pages.pdf")), pagesize=A4)
    c.setFont("Helvetica", 11)
    c.drawString(60, PAGE_H - 70, "This page has content.")
    c.showPage()
    c.showPage()
    c.showPage()
    c.setFont("Helvetica", 11)
    c.drawString(60, PAGE_H / 2, "Only this page has content after empty pages.")
    c.showPage()
    c.save()


def gen_42():
    c = canvas.Canvas(str(_p("42_tricky_whitespace_only.pdf")), pagesize=A4)
    c.setFont("Helvetica", 0.5)
    c.drawString(60, PAGE_H - 70, " ")
    c.showPage()
    c.setFont("Helvetica", 0.5)
    c.drawString(60, PAGE_H - 70, " ")
    c.showPage()
    c.save()


def gen_43():
    c = canvas.Canvas(str(_p("43_tricky_shapes_only.pdf")), pagesize=A4)
    for i in range(6):
        x = random.randint(50, 500)
        y = random.randint(50, 750)
        c.setFillColor(_rc(i * 11))
        c.circle(x, y, random.randint(20, 80), fill=1, stroke=0)
    for i in range(4):
        c.setStrokeColor(_rc(i * 7 + 3))
        c.setLineWidth(random.uniform(1, 5))
        c.line(random.randint(50, 500), random.randint(50, 750),
               random.randint(50, 500), random.randint(50, 750))
    c.showPage()
    c.save()


def gen_44():
    doc = SimpleDocTemplate(str(_p("44_tricky_long_words.pdf")), pagesize=A4,
                            leftMargin=50, rightMargin=50)
    story = []
    long_word = "pneumonoultramicroscopicsilicovolcanoconiosis"
    story.append(Paragraph("Long Word Test", STYLE_H1))
    story.append(Paragraph(
        f"This document tests handling of very long words like "
        f"<b>{long_word}</b> which is 45 characters. "
        f"Also: floccinaucinihilipilification, "
        f"antidisestablishmentarianism, and "
        f"supercalifragilisticexpialidocious.",
        STYLE_BODY))
    story.append(Spacer(1, 12))
    data = [["Word", "Length"],
            [long_word, "45"],
            ["floccinaucinihilipilification", "29"],
            ["antidisestablishmentarianism", "28"],
            ["supercalifragilisticexpialidocious", "34"]]
    story.append(_make_table(data, col_widths=[250, 80]))
    doc.build(story)


def gen_45():
    c = canvas.Canvas(str(_p("45_tricky_font_encoding.pdf")), pagesize=A4)
    _hf(c, "Font and Encoding Edge Cases", 1)
    y = PAGE_H - 80
    c.setFont("Helvetica", 11)
    samples = [
        ("ASCII printable:", string.printable[:60]),
        ("Latin-1 range:", "".join(chr(i) for i in range(192, 256))),
        ("Math symbols:", "\u2211\u220f\u222b\u2248\u2260\u2264\u2265\u221e\u221a\u03c0"),
        ("Currency:", "$\u00a3\u00a5\u20ac\u00a2\u00a4"),
        ("Emojis:", "\u2764\u2605\u2666\u2663\u2660\u2192\u2190\u2191\u2193"),
    ]
    for label, text in samples:
        c.setFont("Helvetica-Bold", 10)
        c.drawString(60, y, label)
        c.setFont("Helvetica", 10)
        c.drawString(200, y, text[:80])
        y -= 22
    c.showPage()
    c.save()


# ===================================================================
# Category 10: Enterprise documents (46-50)
# ===================================================================

def gen_46():
    doc = SimpleDocTemplate(str(_p("46_enterprise_invoice.pdf")), pagesize=LETTER,
                            leftMargin=50, rightMargin=50)
    story = []
    story.append(Paragraph("INVOICE", ParagraphStyle(
        "InvoiceTitle", parent=STYLE_H1, fontSize=28,
        alignment=TA_RIGHT, textColor=HexColor("#2c3e50"))))
    story.append(Spacer(1, 8))

    info_data = [
        ["Invoice #:", "INV-2024-0042", "", "Bill To:"],
        ["Date:", "2024-11-15", "", "Acme Corp"],
        ["Due Date:", "2024-12-15", "", "123 Business Rd"],
        ["From:", "Test Corp Inc.", "", "Suite 100, City"],
    ]
    info_t = Table(info_data, colWidths=[80, 120, 20, 160])
    info_t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (3, 0), (3, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(info_t)
    story.append(Spacer(1, 16))

    items = [
        ["#", "Description", "Qty", "Rate", "Amount"],
        ["1", "Web Development", "40 hrs", "$150/hr", "$6,000"],
        ["2", "UI/UX Design", "20 hrs", "$120/hr", "$2,400"],
        ["3", "Project Management", "10 hrs", "$100/hr", "$1,000"],
        ["4", "Testing & QA", "15 hrs", "$110/hr", "$1,650"],
        ["", "", "", "Subtotal", "$11,050"],
        ["", "", "", "Tax (8%)", "$884"],
        ["", "", "", "TOTAL", "$11,934"],
    ]
    t = Table(items, colWidths=[30, 170, 70, 80, 90])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HexColor("#2c3e50")),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, grey),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ("FONTNAME", (3, -3), (-1, -1), "Helvetica-Bold"),
        ("LINEABOVE", (3, -3), (4, -3), 1, black),
        ("LINEABOVE", (3, -1), (4, -1), 2, black),
    ]))
    story.append(t)
    doc.build(story)


def gen_47():
    c = canvas.Canvas(str(_p("47_enterprise_report.pdf")), pagesize=A4)
    sections = [
        ("Executive Summary", 2),
        ("Market Analysis", 4),
        ("Financial Projections", 3),
        ("Risk Assessment", 3),
        ("Conclusion", 2),
    ]
    pg = 1
    for title, pgs in sections:
        for sp in range(pgs):
            _hf(c, f"Enterprise Report: {title}", pg)
            if sp == 0:
                c.setFont("Helvetica-Bold", 16)
                c.drawString(60, PAGE_H - 80, title)
                c.line(60, PAGE_H - 85, PAGE_W - 60, PAGE_H - 85)
            y = PAGE_H - 110 if sp == 0 else PAGE_H - 70
            c.setFont("Helvetica", 11)
            for _ in range(25):
                c.drawString(60, y, _lorem(1))
                y -= 16
            pg += 1
            if pg <= sum(sects[1] for sects in sections[:sections.index((title, pgs)) + 1]):
                c.showPage()
    c.save()


def gen_48():
    c = canvas.Canvas(str(_p("48_enterprise_presentation.pdf")), pagesize=LETTER)
    slides = [
        "Company Overview", "Mission & Vision", "Products & Services",
        "Market Opportunity", "Financial Highlights", "Team",
        "Roadmap", "Thank You",
    ]
    for i, title in enumerate(slides):
        bg_colors = ["#1a1a2e", "#16213e", "#0f3460", "#533483",
                     "#2c3e50", "#1b262c", "#0a1628", "#1a1a2e"]
        c.setFillColor(HexColor(bg_colors[i % len(bg_colors)]))
        c.rect(0, 0, LETTER[0], LETTER[1], fill=1, stroke=0)
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 32)
        c.drawCentredString(LETTER[0] / 2, LETTER[1] / 2 + 20, title)
        c.setFont("Helvetica", 16)
        c.drawCentredString(LETTER[0] / 2, LETTER[1] / 2 - 20,
                            f"Slide {i + 1} of {len(slides)}")
        c.setFont("Helvetica", 12)
        c.setFillColor(HexColor("#a0a0a0"))
        c.drawCentredString(LETTER[0] / 2, 40, _lorem(2))
        if i < len(slides) - 1:
            c.showPage()
    c.save()


def gen_49():
    doc = SimpleDocTemplate(str(_p("49_enterprise_form.pdf")), pagesize=LETTER,
                            leftMargin=60, rightMargin=60)
    story = []
    story.append(Paragraph("Employee Information Form", STYLE_H1))
    story.append(Spacer(1, 20))
    fields = [
        ("Full Name:", "_" * 50),
        ("Employee ID:", "_" * 50),
        ("Department:", "_" * 50),
        ("Position:", "_" * 50),
        ("Start Date:", "_" * 50),
        ("Email:", "_" * 50),
        ("Phone:", "_" * 50),
        ("Address:", "_" * 50),
    ]
    for label, blank in fields:
        story.append(Paragraph(
            f"<b>{label}</b>&nbsp;&nbsp;{blank}", STYLE_BODY))
        story.append(Spacer(1, 10))
    story.append(Spacer(1, 12))
    story.append(Paragraph("Emergency Contact", STYLE_H2))
    story.append(Spacer(1, 8))
    for label in ["Name:", "Relationship:", "Phone:"]:
        story.append(Paragraph(f"<b>{label}</b>&nbsp;&nbsp;{'_' * 50}", STYLE_BODY))
        story.append(Spacer(1, 8))
    story.append(Spacer(1, 20))
    sig_data = [
        ["Employee Signature:", "_" * 30, "Date:", "_" * 15],
        ["Manager Signature:", "_" * 30, "Date:", "_" * 15],
    ]
    sig_t = Table(sig_data, colWidths=[120, 180, 40, 100])
    story.append(sig_t)
    doc.build(story)


def gen_50():
    c = canvas.Canvas(str(_p("50_enterprise_dashboard.pdf")), pagesize=LETTER)
    _hf(c, "Executive Dashboard", 1)
    widgets = [
        ("Revenue", "$4.2M", "+12%", "#27ae60"),
        ("Users", "25,340", "+8%", "#2980b9"),
        ("Tickets", "142", "-5%", "#e74c3c"),
        ("Uptime", "99.9%", "+0.1%", "#8e44ad"),
    ]
    wx, wy = 50, PAGE_H - 130
    ww, wh = 120, 80
    for i, (label, value, change, color) in enumerate(widgets):
        x = wx + i * (ww + 15)
        c.setFillColor(HexColor(color))
        c.roundRect(x, wy, ww, wh, 5, fill=1, stroke=0)
        c.setFillColor(white)
        c.setFont("Helvetica", 9)
        c.drawString(x + 8, wy + wh - 18, label)
        c.setFont("Helvetica-Bold", 18)
        c.drawString(x + 8, wy + 30, value)
        c.setFont("Helvetica", 10)
        c.drawString(x + 8, wy + 12, change)
    chart_y = wy - 120
    c.setStrokeColor(grey)
    c.setLineWidth(0.5)
    c.line(50, chart_y, PAGE_W - 50, chart_y)
    c.setFont("Helvetica", 8)
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    vals = [30, 45, 38, 52, 48, 60, 55, 70, 65, 80, 75, 90]
    bw = 30
    for i, (m, v) in enumerate(zip(months, vals)):
        x = 60 + i * (bw + 10)
        h = v * 1.5
        c.setFillColor(_rc(i * 3, light=True))
        c.rect(x, chart_y, bw, h, fill=1, stroke=0)
        c.setFillColor(black)
        c.drawCentredString(x + bw / 2, chart_y - 14, m)
        c.drawCentredString(x + bw / 2, chart_y + h + 5, str(v))
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, chart_y + v * 1.5 + 30, "Monthly Performance")
    c.showPage()
    c.save()


# ===================================================================
# Main
# ===================================================================

ALL_GENS = [
    gen_01, gen_02, gen_03, gen_04, gen_05,
    gen_06, gen_07, gen_08, gen_09, gen_10,
    gen_11, gen_12, gen_13, gen_14, gen_15,
    gen_16, gen_17, gen_18, gen_19, gen_20,
    gen_21, gen_22, gen_23, gen_24, gen_25,
    gen_26, gen_27, gen_28, gen_29, gen_30,
    gen_31, gen_32, gen_33, gen_34, gen_35,
    gen_36, gen_37, gen_38, gen_39, gen_40,
    gen_41, gen_42, gen_43, gen_44, gen_45,
    gen_46, gen_47, gen_48, gen_49, gen_50,
]

CATEGORIES = [
    (1, 5, "Simple text"),
    (6, 10, "Multi-column layouts"),
    (11, 15, "Tables with merged cells"),
    (16, 20, "Image-heavy (shapes)"),
    (21, 25, "RTL languages"),
    (26, 30, "Large documents"),
    (31, 35, "Edge cases"),
    (36, 40, "Mixed content"),
    (41, 45, "Corrupted / tricky"),
    (46, 50, "Enterprise documents"),
]


def main():
    print(f"Generating 50 test PDFs in: {OUTPUT_DIR}\n")
    for i, gen_fn in enumerate(ALL_GENS, start=1):
        gen_fn()
        cat_label = ""
        for lo, hi, name in CATEGORIES:
            if lo <= i <= hi:
                cat_label = name
                break
        print(f"  [{i:2d}/50] {cat_label:<30s} -> {gen_fn.__name__}")

    print(f"\nDone! {len(ALL_GENS)} PDFs created in {OUTPUT_DIR}")
    files = sorted(OUTPUT_DIR.glob("*.pdf"))
    print(f"Files on disk: {len(files)}")


if __name__ == "__main__":
    main()
