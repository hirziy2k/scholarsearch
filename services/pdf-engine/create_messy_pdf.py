#!/usr/bin/env python3
"""
Generate a deliberately chaotic test PDF for entropy measurement.
Contains:
- Multi-column layout with aggressive text wrapping
- Complex borderless table with asymmetrical merged cells
- Floating annotations/headers positioned irregularly
- Embedded vector graphics overlapping with text
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch, mm, cm
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, Color
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

def create_messy_pdf(output_path: str):
    page_width, page_height = letter  # 612 x 792 pt
    c = canvas.Canvas(output_path, pagesize=letter)
    
    # ============================================================
    # PAGE 1: Multi-column chaos + overlapping vector + annotations
    # ============================================================
    
    # Background pattern (vector)
    c.setStrokeColor(HexColor("#E0E0E0"))
    c.setLineWidth(0.3)
    for x in range(0, int(page_width), 20):
        c.line(x, 0, x, page_height)
    for y in range(0, int(page_height), 20):
        c.line(0, y, page_width, y)
    
    # Floating header (irregular position)
    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(HexColor("#1A1A2E"))
    c.drawString(80, page_height - 50, "QUARTERLY REPORT — CONFIDENTIAL")
    
    # Annotation box (floating, overlapping)
    c.setFillColor(Color(1, 1, 0.8, alpha=0.7))
    c.setStrokeColor(HexColor("#FFD700"))
    c.setLineWidth(1.5)
    c.roundRect(400, page_height - 120, 150, 80, 5, stroke=1, fill=1)
    c.setFillColor(HexColor("#8B0000"))
    c.setFont("Helvetica-Bold", 9)
    c.drawString(410, page_height - 60, "DRAFT")
    c.drawString(410, page_height - 75, "v0.3-alpha")
    c.drawString(410, page_height - 90, "INTERNAL ONLY")
    
    # Multi-column text (2 columns, aggressive wrapping)
    left_col_x = 50
    right_col_x = 330
    col_width = 250
    y_start = page_height - 100
    
    # Left column - fragmented spans to simulate kerning
    lorem = ("Lorem ipsum dolor sit amet, consectetur adipiscing elit. " 
             "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. "
             "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris. "
             "Duis aute irure dolor in reprehenderit in voluptate velit esse cillum. "
             "Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia.")
    
    # Write as INDIVIDUAL CHARACTERS to simulate PDF kerning fragmentation
    c.setFont("Helvetica", 10)
    c.setFillColor(HexColor("#000000"))
    x = left_col_x
    y = y_start
    char_width = 5.5  # approximate
    for i, char in enumerate(lorem):
        if char == ' ':
            x += char_width
            continue
        if x > left_col_x + col_width - 10:
            x = left_col_x
            y -= 13
        c.drawString(x, y, char)
        x += char_width + 0.3  # slight random kerning
    
    # Right column - different font, size, color
    c.setFont("Times-Roman", 11)
    c.setFillColor(HexColor("#2C3E50"))
    x = right_col_x
    y = y_start
    lorem2 = ("Curabitur pretium tincidunt lacus. Nulla gravida orci a odio. "
              "Nullam varius, turpis et commodo pharetra, est eros bibendum elit, "
              "nec luctus magna felis sollicitudin mauris. Integer in mauris eu nibh.")
    for i, char in enumerate(lorem2):
        if char == ' ':
            x += 6
            continue
        if x > right_col_x + col_width - 10:
            x = right_col_x
            y -= 14
        c.drawString(x, y, char)
        x += 6.2
    
    # ============================================================
    # COMPLEX BORDERLESS TABLE with ASYMMETRICAL MERGED CELLS
    # ============================================================
    table_top = y_start - 220
    table_left = 50
    
    # Table data with merged cells (simulated by drawing)
    headers = ["Metric", "Q1", "Q2", "Q3", "Q4", "YoY Δ"]
    rows = [
        ["Revenue ($M)", "12.4", "14.2", "13.8", "16.1", "+12.3%"],
        ["Users (K)", "45", "52", "48", "61", "+35.6%"],
        ["Churn %", "3.2", "2.8", "3.1", "2.5", "-0.7pp"],
        ["NPS", "42", "45", "44", "48", "+6"],
    ]
    
    col_widths = [120, 70, 70, 70, 70, 70]
    row_height = 28
    
    # Draw table WITHOUT borders (borderless)
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(HexColor("#1A1A2E"))
    x = table_left
    for i, h in enumerate(headers):
        c.drawString(x + 3, table_top + row_height - 14, h)
        x += col_widths[i]
    
    c.setFont("Helvetica", 9)
    c.setFillColor(HexColor("#333333"))
    for r_idx, row in enumerate(rows):
        y = table_top - (r_idx + 1) * row_height
        x = table_left
        for c_idx, cell in enumerate(row):
            # Simulate merged cell: "Revenue ($M)" spans visually but not structurally
            if r_idx == 0 and c_idx == 0:
                c.setFillColor(HexColor("#E74C3C"))  # Red for "merged" indicator
            c.drawString(x + 3, y + row_height - 13, cell)
            x += col_widths[c_idx]
        c.setFillColor(HexColor("#333333"))
    
    # Add subtle separator lines (not full borders)
    c.setStrokeColor(HexColor("#BDC3C7"))
    c.setLineWidth(0.4)
    c.line(table_left, table_top, table_left + sum(col_widths), table_top)
    c.line(table_left, table_top - len(rows) * row_height, 
           table_left + sum(col_widths), table_top - len(rows) * row_height)
    
    # ============================================================
    # OVERLAPPING VECTOR GRAPHIC (circle overlapping text)
    # ============================================================
    c.setStrokeColor(HexColor("#E74C3C"))
    c.setFillColor(Color(0.9, 0.2, 0.2, alpha=0.15))
    c.setLineWidth(2)
    # Circle centered at (200, 400) radius 80 - overlaps left column text
    c.circle(200, 400, 80, stroke=1, fill=1)
    c.setFillColor(HexColor("#E74C3C"))
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(200, 400, "OVERLAP")
    c.drawCentredString(200, 385, "ZONE")
    
    # Arrow vector overlapping table
    c.setStrokeColor(HexColor("#27AE60"))
    c.setLineWidth(3)
    c.line(350, 380, 450, 320)  # diagonal arrow
    c.line(450, 320, 440, 330)
    c.line(450, 320, 440, 310)
    
    # Floating footer annotation
    c.setFont("Helvetica-Oblique", 8)
    c.setFillColor(HexColor("#7F8C8D"))
    c.drawString(50, 40, "Page 1 — Generated for entropy testing — Not for distribution")
    
    c.showPage()
    
    # ============================================================
    # PAGE 2: Rotated content + Type3 font simulation + more chaos
    # ============================================================
    
    # Rotated text block (90 degrees)
    c.saveState()
    c.translate(100, 400)
    c.rotate(90)
    c.setFont("Courier-Bold", 14)
    c.setFillColor(HexColor("#8E44AD"))
    c.drawString(0, 0, "ROTATED TEXT BLOCK — 90° CW")
    c.restoreState()
    
    # Type3 font simulation: draw each glyph as vector path
    c.setStrokeColor(HexColor("#2C3E50"))
    c.setFillColor(HexColor("#2C3E50"))
    c.setLineWidth(1)
    # Simulate "TYPE3" as vector outlines
    type3_text = "TYPE3"
    x_start = 150
    y_start = 500
    for i, char in enumerate(type3_text):
        # Draw each character as rectangle + lines (vector simulation)
        cx = x_start + i * 25
        c.rect(cx, y_start, 20, 25, stroke=1, fill=0)
        c.line(cx + 2, y_start + 2, cx + 18, y_start + 23)
        c.line(cx + 18, y_start + 2, cx + 2, y_start + 23)
    
    # Another multi-column section with different widths
    c.setFont("Helvetica", 9)
    c.setFillColor(HexColor("#000000"))
    
    # Three narrow columns
    col_starts = [50, 230, 410]
    col_w = 150
    texts = [
        "Column A: Narrow text block with tight leading and irregular spacing. "
        "This simulates newspaper-style layout.",
        "Column B: Middle column with different font metrics. "
        "Helvetica at 9pt but tighter tracking.",
        "Column C: Right column with justification issues. "
        "Words may break oddly at line ends."
    ]
    
    for col_idx, (cx, text) in enumerate(zip(col_starts, texts)):
        if col_idx == 1:
            c.setFont("Times-Roman", 9)
        elif col_idx == 2:
            c.setFont("Courier", 8.5)
        else:
            c.setFont("Helvetica", 9)
        
        # Write word by word with random spacing
        words = text.split()
        x = cx
        y = 350
        for word in words:
            word_w = c.stringWidth(word + " ", c._fontname, c._fontsize)
            if x + word_w > cx + col_w:
                x = cx
                y -= 12
            c.drawString(x, y, word + " ")
            x += word_w + (0.5 if col_idx == 1 else 0)
    
    # Footer with page number
    c.setFont("Helvetica", 9)
    c.setFillColor(HexColor("#555555"))
    c.drawCentredString(page_width / 2, 30, "— 2 —")
    
    c.showPage()
    
    # ============================================================
    # PAGE 3: Form fields + annotations + watermark
    # ============================================================
    
    # Watermark (large diagonal text)
    c.saveState()
    c.setFont("Helvetica-Bold", 80)
    c.setFillColor(Color(0.9, 0.9, 0.9, alpha=0.3))
    c.translate(page_width/2, page_height/2)
    c.rotate(45)
    c.drawCentredString(0, 0, "CONFIDENTIAL")
    c.restoreState()
    
    # Form-like fields (rectangles with labels)
    fields = [
        ("Name:", 50, 650, 200),
        ("Date:", 300, 650, 150),
        ("Department:", 50, 600, 200),
        ("Signature:", 300, 600, 200),
    ]
    c.setStrokeColor(HexColor("#999999"))
    c.setLineWidth(0.8)
    c.setFont("Helvetica", 10)
    c.setFillColor(HexColor("#333333"))
    for label, x, y, w in fields:
        c.drawString(x, y + 15, label)
        c.rect(x, y, w, 25, stroke=1, fill=0)
    
    # Checkbox simulation
    c.rect(50, 550, 15, 15, stroke=1, fill=0)
    c.drawString(70, 552, "Agree to terms")
    c.rect(200, 550, 15, 15, stroke=1, fill=1)  # checked
    c.drawString(220, 552, "Receive updates")
    
    # Radio buttons
    c.setFillColor(HexColor("#333333"))
    c.circle(50 + 7.5, 515 + 7.5, 7.5, stroke=1, fill=0)
    c.circle(50 + 7.5, 515 + 7.5, 3, stroke=1, fill=1)  # selected
    c.drawString(70, 517, "Option A")
    c.circle(200 + 7.5, 515 + 7.5, 7.5, stroke=1, fill=0)
    c.drawString(220, 517, "Option B")
    
    c.save()
    print(f"Created messy PDF: {output_path}")
    print(f"Pages: 3")
    print(f"Size: {os.path.getsize(output_path)} bytes")

if __name__ == "__main__":
    create_messy_pdf("messy_test.pdf")