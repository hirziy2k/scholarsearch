#!/usr/bin/env python3
"""
Extract entropy metrics from messy_test.pdf using mcp-pdf with correct tool parameters.
"""

import asyncio
import json
import sys
import re
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def extract_entropy_metrics():
    pdf_path = Path("messy_test.pdf").resolve()
    
    # Start mcp-pdf server
    params = StdioServerParameters(command="uvx", args=["mcp-pdf"])
    
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            print("=" * 70)
            print("ENTROPY MEASUREMENT: mcp-pdf extraction on messy_test.pdf")
            print("=" * 70)
            
            # 1. Text extraction
            print("\n[1] Text extraction (textextraction__extract_text)...")
            text_result = await session.call_tool("textextraction__extract_text", {
                "pdf_path": str(pdf_path),
                "inline": True
            })
            text_content = str(text_result)
            print(f"    Result length: {len(text_content)} chars")
            print(f"    Preview: {text_content[:500]}...")
            
            # 2. pdf_to_markdown equivalent
            print("\n[2] Markdown extraction (imageprocessing__pdf_to_markdown)...")
            md_result = await session.call_tool("imageprocessing__pdf_to_markdown", {
                "pdf_path": str(pdf_path),
                "extract_images": True,
                "image_format": "png"
            })
            md_content = str(md_result)
            print(f"    Result length: {len(md_content)} chars")
            
            with open("extraction_raw.json", "w") as f:
                json.dump({"markdown": md_content}, f, indent=2)
            print("    Full output saved to extraction_raw.json")
            
            # 3. Table extraction
            print("\n[3] Table extraction (tableextraction__extract_tables)...")
            tables_result = await session.call_tool("tableextraction__extract_tables", {
                "pdf_path": str(pdf_path)
            })
            tables_content = str(tables_result)
            print(f"    Result length: {len(tables_content)} chars")
            print(f"    Preview: {tables_content[:2000]}...")
            
            with open("tables_raw.json", "w") as f:
                json.dump({"tables": tables_content}, f, indent=2)
            
            # 4. Document structure
            print("\n[4] Document structure (documentanalysis__get_document_structure)...")
            struct_result = await session.call_tool("documentanalysis__get_document_structure", {
                "pdf_path": str(pdf_path)
            })
            struct_content = str(struct_result)
            print(f"    Result length: {len(struct_content)} chars")
            print(f"    Preview: {struct_content[:1000]}...")
            
            # 5. Layout analysis
            print("\n[5] Layout analysis (contentanalysis__analyze_layout)...")
            layout_result = await session.call_tool("contentanalysis__analyze_layout", {
                "pdf_path": str(pdf_path)
            })
            layout_content = str(layout_result)
            print(f"    Result length: {len(layout_content)} chars")
            print(f"    Preview: {layout_content[:1000]}...")
            
            # 6. Image extraction
            print("\n[6] Image extraction (imageprocessing__extract_images)...")
            images_result = await session.call_tool("imageprocessing__extract_images", {
                "pdf_path": str(pdf_path),
                "output_format": "png"
            })
            images_content = str(images_result)
            print(f"    Result length: {len(images_content)} chars")
            print(f"    Preview: {images_content[:1000]}...")
            
            # 7. Vector graphics extraction
            print("\n[7] Vector graphics (imageprocessing__extract_vector_graphics)...")
            vectors_result = await session.call_tool("imageprocessing__extract_vector_graphics", {
                "pdf_path": str(pdf_path)
            })
            vectors_content = str(vectors_result)
            print(f"    Result length: {len(vectors_content)} chars")
            print(f"    Preview: {vectors_content[:1000]}...")
            
            # 8. PDF health/analysis
            print("\n[8] PDF Health (documentanalysis__analyze_pdf_health)...")
            health_result = await session.call_tool("documentanalysis__analyze_pdf_health", {
                "pdf_path": str(pdf_path)
            })
            health_content = str(health_result)
            print(f"    Result length: {len(health_content)} chars")
            print(f"    Preview: {health_content[:1000]}...")
            
            return {
                "text": text_content,
                "markdown": md_content,
                "tables": tables_content,
                "structure": struct_content,
                "layout": layout_content,
                "images": images_content,
                "vectors": vectors_content,
                "health": health_content
            }


if __name__ == "__main__":
    result = asyncio.run(extract_entropy_metrics())
    
    # Summary metrics
    print("\n" + "=" * 70)
    print("ENTROPY SUMMARY")
    print("=" * 70)
    
    md = result["markdown"]
    
    # Count coordinate patterns
    coord_pattern = r'\[(\d+\.?\d*),\s*(\d+\.?\d*),\s*(\d+\.?\d*),\s*(\d+\.?\d*)\]'
    coords = re.findall(coord_pattern, md)
    print(f"Coordinate tuples found: {len(coords)}")
    
    # Count potential text spans
    lines = md.split('\n')
    text_lines = [l for l in lines if l.strip() and not l.strip().startswith('#') and not l.strip().startswith('![')]
    print(f"Non-empty content lines: {len(text_lines)}")
    
    # Print full markdown for analysis
    print(f"\n--- FULL MARKDOWN OUTPUT ---")
    print(md[:5000] if len(md) > 5000 else md)
    
    # Analyze tables
    tables = result["tables"]
    print(f"\n--- TABLE EXTRACTION OUTPUT ---")
    print(tables[:5000] if len(tables) > 5000 else tables)
    
    # Analyze structure
    struct = result["structure"]
    print(f"\n--- DOCUMENT STRUCTURE OUTPUT ---")
    print(struct[:5000] if len(struct) > 5000 else struct)
    
    # Analyze layout
    layout = result["layout"]
    print(f"\n--- LAYOUT ANALYSIS OUTPUT ---")
    print(layout[:5000] if len(layout) > 5000 else layout)