#!/usr/bin/env python3
"""
pdf_extractor.py — PyMuPDF Primary Engine

Replaces MCP-PDF as the primary data source. MCP-PDF becomes an
augmentation layer called only for semantic layout analysis on complex pages.

Core capabilities:
- Text + coordinates via get_text("dict") 
- Tables via find_tables()
- Vectors via get_drawings() + get_svg_image()
- Complexity scoring (column detection, block overlap)
- Native coordinate system matching PDF points
"""

import fitz
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import Counter
import math


@dataclass
class TextSpan:
    text: str
    bbox: Tuple[float, float, float, float]
    font: str
    size: float
    color: int
    flags: int


@dataclass
class TextLine:
    spans: List[TextSpan]
    bbox: Tuple[float, float, float, float]


@dataclass
class TextBlock:
    lines: List[TextLine]
    bbox: Tuple[float, float, float, float]
    block_type: str = "text"


@dataclass
class ExtractedTable:
    page: int
    bbox: Tuple[float, float, float, float]
    rows: int
    cols: int
    data: List[List[str]]


@dataclass
class VectorDrawing:
    page: int
    paths: List[Dict]
    fill: Optional[str]
    stroke: Optional[str]
    bbox: Tuple[float, float, float, float]


@dataclass
class PageExtraction:
    page_num: int
    blocks: List[TextBlock]
    tables: List[ExtractedTable]
    vectors: List[VectorDrawing]
    svg_path: Optional[str] = None
    page_size: Tuple[float, float] = (612, 792)


@dataclass
class DocumentExtraction:
    pdf_path: str
    pages: List[PageExtraction]
    font_size_map: Dict[float, int] = field(default_factory=dict)
    body_font_size: float = 12.0


class PyMuPDFExtractor:
    """Primary extraction engine using PyMuPDF directly."""
    
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.doc = fitz.open(pdf_path)
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.doc.close()
    
    def extract_all(self) -> DocumentExtraction:
        """Extract full document with all data types."""
        pages = []
        all_font_sizes = []
        
        for page_num in range(len(self.doc)):
            page = self.doc[page_num]
            extraction = self._extract_page(page, page_num + 1)
            pages.append(extraction)
            
            for block in extraction.blocks:
                for line in block.lines:
                    for span in line.spans:
                        all_font_sizes.append(round(span.size, 1))
        
        font_size_map = dict(Counter(all_font_sizes))
        body_size = max(font_size_map.items(), key=lambda x: x[1])[0] if font_size_map else 12.0
        
        return DocumentExtraction(
            pdf_path=self.pdf_path,
            pages=pages,
            font_size_map=font_size_map,
            body_font_size=body_size
        )
    
    def _extract_page(self, page: fitz.Page, page_num: int) -> PageExtraction:
        page_size = (page.rect.width, page.rect.height)
        
        blocks = self._extract_text_blocks(page)
        tables = self._extract_tables(page, page_num)
        vectors = self._extract_vectors(page, page_num)
        svg = self._extract_svg(page, page_num)
        
        return PageExtraction(
            page_num=page_num,
            blocks=blocks,
            tables=tables,
            vectors=vectors,
            svg_path=svg,
            page_size=page_size
        )
    
    def _extract_text_blocks(self, page: fitz.Page) -> List[TextBlock]:
        """Extract text with full coordinates using get_text('dict')."""
        blocks = []
        text_dict = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE | fitz.TEXTFLAGS_TEXT)
        
        for block in text_dict.get("blocks", []):
            if block["type"] != 0:
                continue
            
            lines = []
            for line in block.get("lines", []):
                spans = []
                for span in line.get("spans", []):
                    text = span.get("text", "")
                    if not text.strip():
                        continue
                    spans.append(TextSpan(
                        text=text,
                        bbox=tuple(span["bbox"]),
                        font=span.get("font", ""),
                        size=round(span["size"], 1),
                        color=span.get("color", 0),
                        flags=span.get("flags", 0)
                    ))
                
                if spans:
                    xs = [s.bbox[0] for s in spans] + [s.bbox[2] for s in spans]
                    ys = [s.bbox[1] for s in spans] + [s.bbox[3] for s in spans]
                    lines.append(TextLine(
                        spans=spans,
                        bbox=(min(xs), min(ys), max(xs), max(ys))
                    ))
            
            if lines:
                xs = [l.bbox[0] for l in lines] + [l.bbox[2] for l in lines]
                ys = [l.bbox[1] for l in lines] + [l.bbox[3] for l in lines]
                blocks.append(TextBlock(
                    lines=lines,
                    bbox=(min(xs), min(ys), max(xs), max(ys))
                ))
        
        return blocks
    
    def _extract_tables(self, page: fitz.Page, page_num: int) -> List[ExtractedTable]:
        """Extract tables using PyMuPDF's native table finder."""
        tables = []
        try:
            tabs = page.find_tables()
            for tab in tabs.tables:
                data = tab.extract()
                if not data:
                    continue
                bbox = tab.bbox
                tables.append(ExtractedTable(
                    page=page_num,
                    bbox=tuple(bbox),
                    rows=len(data),
                    cols=max(len(r) for r in data) if data else 0,
                    data=[[str(c) if c else "" for c in row] for row in data]
                ))
        except Exception:
            pass
        return tables
    
    def _extract_vectors(self, page: fitz.Page, page_num: int) -> List[VectorDrawing]:
        """Extract vector drawings."""
        vectors = []
        try:
            drawings = page.get_drawings()
            if drawings:
                all_x = []
                all_y = []
                for d in drawings:
                    rect = d.get("rect")
                    if rect:
                        all_x.extend([rect.x0, rect.x1])
                        all_y.extend([rect.y0, rect.y1])
                vectors.append(VectorDrawing(
                    page=page_num,
                    paths=drawings,
                    fill=None,
                    stroke=None,
                    bbox=(min(all_x), min(all_y), max(all_x), max(all_y)) if all_x else (0, 0, 0, 0)
                ))
        except Exception:
            pass
        return vectors
    
    def _extract_svg(self, page: fitz.Page, page_num: int) -> Optional[str]:
        """Extract page as SVG and save to temp."""
        try:
            svg_content = page.get_svg_image(text_as_path=False)
            import tempfile
            tmp = tempfile.NamedTemporaryFile(mode='w', suffix=f'_page{page_num}.svg', delete=False)
            tmp.write(svg_content)
            tmp.close()
            return tmp.name
        except Exception:
            return None
    
    def analyze_complexity(self, page: fitz.Page) -> Dict[str, Any]:
        """Analyze page layout complexity to decide if MCP augmentation is needed."""
        blocks = page.get_text("blocks")
        text_blocks = [b for b in blocks if b[6] == 0]
        
        if len(text_blocks) < 3:
            return {"complex": False, "reason": "insufficient_blocks"}
        
        x_positions = [b[0] for b in text_blocks]
        x_centers = [(b[0] + b[2]) / 2 for b in text_blocks]
        
        sorted_x = sorted(x_centers)
        gaps = [sorted_x[i+1] - sorted_x[i] for i in range(len(sorted_x)-1)]
        avg_gap = sum(gaps) / len(gaps) if gaps else 0
        max_gap = max(gaps) if gaps else 0
        
        median_x = sorted_x[len(sorted_x)//2]
        left_count = sum(1 for x in x_centers if x < median_x)
        right_count = sum(1 for x in x_centers if x >= median_x)
        
        overlap = 0
        for i, b1 in enumerate(text_blocks):
            for b2 in text_blocks[i+1:]:
                if not (b1[2] <= b2[0] or b2[2] <= b1[0] or b1[3] <= b2[1] or b2[3] <= b1[1]):
                    overlap += 1
        
        is_multi_column = max_gap > avg_gap * 3 and min(left_count, right_count) > 2
        is_complex = is_multi_column or overlap > len(text_blocks) * 0.3
        
        return {
            "complex": is_complex,
            "multi_column": is_multi_column,
            "block_count": len(text_blocks),
            "overlap_pairs": overlap,
            "max_x_gap": max_gap,
            "avg_x_gap": avg_gap,
            "left_blocks": left_count,
            "right_blocks": right_count
        }


def extract_with_complexity(pdf_path: str) -> Tuple[DocumentExtraction, List[Dict]]:
    """Convenience function: extract document + per-page complexity analysis."""
    with PyMuPDFExtractor(pdf_path) as extractor:
        doc = extractor.extract_all()
        complexities = []
        for i, page in enumerate(doc.pages):
            complexity = extractor.analyze_complexity(extractor.doc[i])
            complexities.append(complexity)
        return doc, complexities


if __name__ == "__main__":
    import sys
    pdf = sys.argv[1] if len(sys.argv) > 1 else "messy_test.pdf"
    doc, complexities = extract_with_complexity(pdf)
    print(f"Pages: {len(doc.pages)}")
    print(f"Body font size: {doc.body_font_size:.1f}")
    print(f"Font size map: {doc.font_size_map}")
    for i, (page, c) in enumerate(zip(doc.pages, complexities)):
        print(f"  Page {i+1}: blocks={len(page.blocks)}, tables={len(page.tables)}, vectors={len(page.vectors)}, complex={c['complex']}")