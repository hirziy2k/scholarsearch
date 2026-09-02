#!/usr/bin/env python3
"""
Test Phase 2 extraction on messy_test.pdf - clustering + table validation.
"""

import asyncio
import json
from pathlib import Path
from typing import Dict, Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Import our clustering functions
import sys
sys.path.insert(0, str(Path(__file__).parent))
from pdf_to_pptx import cluster_spans, span_in_bbox, merge_cluster, validate_table_structure, extract_and_validate_tables


def parse_result(result) -> Dict[str, Any]:
        """Extract structured_content from MCP tool result."""
        if hasattr(result, 'structured_content') and result.structured_content:
            return result.structured_content
        # Fallback: parse from text content
        text = str(result)
        if "structured_content=" in text:
            try:
                json_str = text.split("structured_content=")[1].split(" is_error")[0]
                return json.loads(json_str)
            except:
                pass
        return {}


async def test_phase2_extraction():
    pdf_path = Path("messy_test.pdf").resolve()
    
    params = StdioServerParameters(command="uvx", args=["mcp-pdf"])
    
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            print("=" * 70)
            print("PHASE 2 TEST: Clustering + Table Validation on messy_test.pdf")
            print("=" * 70)
            
            # 1. Get layout analysis (text blocks with coordinates)
            print("\n[1] Getting layout analysis...")
            layout_result = await session.call_tool("contentanalysis__analyze_layout", {
                "pdf_path": str(pdf_path)
            })
            layout_data = parse_result(layout_result)
            
            # 2. Get raw text spans (simulate from text extraction)
            print("\n[2] Getting raw text extraction...")
            text_result = await session.call_tool("textextraction__extract_text", {
                "pdf_path": str(pdf_path),
                "inline": True
            })
            text_data = parse_result(text_result)
            raw_text = text_data.get("text", "")
            
            # For clustering test, we need character-level spans
            # The mcp-pdf doesn't expose raw spans directly, so we'll simulate from layout blocks
            # In real implementation, we'd need a different tool or parse the PDF directly
            
            print(f"\nLayout blocks found:")
            for page in layout_data.get("page_layouts", []):
                print(f"  Page {page['page']}: {len(page.get('text_blocks', []))} text blocks")
                for block in page.get("text_blocks", [])[:3]:  # Show first 3
                    coords = block.get("coordinates", {})
                    print(f"    Block: ({coords.get('x1',0):.1f}, {coords.get('y1',0):.1f}) "
                          f"to ({coords.get('x2',0):.1f}, {coords.get('y2',0):.1f}) "
                          f"size: {block.get('width',0):.1f}x{block.get('height',0):.1f} "
                          f"lines: {block.get('line_count',0)}")
            
            # 3. Test table extraction + validation
            print("\n[3] Testing table validation...")
            tables = await extract_and_validate_tables(session, pdf_path, layout_data)
            
            print(f"\nValidated tables: {len(tables)}")
            for i, table in enumerate(tables):
                if table.get("type") == "fallback_image":
                    print(f"  Table {i+1}: FALLBACK - {table.get('reason')}")
                else:
                    bbox = table.get("bbox", {})
                    print(f"  Table {i+1}: VALID - {table.get('total_rows', '?')} rows x {table.get('columns', '?')} cols")
                    print(f"    Bbox: {bbox}")
                    print(f"    Method: {table.get('method_used', '?')}")
                    data = table.get("data", [])
                    if data:
                        print(f"    Sample data (first 3 rows): {data[:3]}")
            
            # 4. Test clustering simulation
            print("\n[4] Testing span clustering (simulated)...")
            # Create synthetic spans from layout blocks to test clustering
            for page in layout_data.get("page_layouts", []):
                page_num = page["page"]
                blocks = page.get("text_blocks", [])
                if not blocks:
                    continue
                
                # Simulate character spans within first block
                first_block = blocks[0]
                coords = first_block.get("coordinates", {})
                print(f"\n  Page {page_num} - First block simulation:")
                print(f"    Layout bbox: x1={coords.get('x1',0):.1f}, y1={coords.get('y1',0):.1f}, "
                      f"x2={coords.get('x2',0):.1f}, y2={coords.get('y2',0):.1f}")
                
                # Create fake spans for testing
                fake_spans = []
                text = "Lorem ipsum dolor sit amet consectetur"
                x_start = coords.get("x1", 50)
                y_start = coords.get("y1", 80)
                for i, char in enumerate(text):
                    if char == " ":
                        continue
                    fake_spans.append({
                        "text": char,
                        "x": x_start + i * 6,
                        "y": y_start,
                        "width": 5.5,
                        "height": 12,
                        "font_size": 12,
                        "font_name": "Helvetica"
                    })
                
                clustered = cluster_spans(fake_spans, [first_block])
                print(f"    Input spans: {len(fake_spans)}")
                print(f"    Output clusters: {len(clustered)}")
                for c in clustered:
                    print(f"      Cluster: '{c['text'][:50]}' at ({c['left']:.1f},{c['top']:.1f}) "
                          f"size {c['width']:.1f}×{c['height']:.1f} font={c['font_name']} {c['font_size']}pt")
            
            return layout_data, tables


if __name__ == "__main__":
    asyncio.run(test_phase2_extraction())