#!/usr/bin/env python3
"""
mcp_augment.py — MCP-PDF Augmentation Layer

Called ONLY for semantically complex pages where PyMuPDF geometry
is insufficient (multi-column, overlapping blocks, mixed content).

MCP-PDF provides:
- Reading order determination
- Header/footer classification
- Caption/figure association
- Logical structure detection
"""

import asyncio
from typing import Dict, List, Any, Optional
# MCPSession defined in pdf_to_pptx - import at runtime to avoid circular import


class MCPAugmentor:
    """Selective MCP-PDF calls for pages that need semantic intelligence."""
    
    def __init__(self, session):
        self.session = session
    
    async def analyze_page(self, pdf_path: str, page_num: int) -> Dict[str, Any]:
        """Get semantic layout for a single complex page."""
        try:
            result = await asyncio.wait_for(
                self.session.call_tool(
                    "contentanalysis__analyze_layout",
                    {"pdf_path": pdf_path, "pages": str(page_num)}
                ),
                timeout=15
            )
            return self._parse_result(result)
        except Exception as e:
            return {"error": str(e), "page": page_num}
    
    async def get_structure(self, pdf_path: str) -> Dict[str, Any]:
        """Get full document structure for reference."""
        try:
            result = await asyncio.wait_for(
                self.session.call_tool(
                    "documentanalysis__get_document_structure",
                    {"pdf_path": pdf_path}
                ),
                timeout=15
            )
            return self._parse_result(result)
        except Exception:
            return {}
    
    def _parse_result(self, result: Dict) -> Dict:
        content = result.get("content", [])
        for item in content:
            if item.get("type") == "text":
                text = item.get("text", "")
                if "structured_content=" in text:
                    try:
                        json_str = text.split("structured_content=")[1].split(" is_error")[0]
                        return eval(json_str) if isinstance(json_str, str) else json_str
                    except Exception:
                        pass
                try:
                    import json
                    return json.loads(text)
                except Exception:
                    pass
        return {}
    
    def sort_blocks_by_reading_order(self, blocks: List[Dict], mcp_layout: Dict) -> List[Dict]:
        """Re-sort PyMuPDF blocks using MCP's reading order if available."""
        page_layouts = mcp_layout.get("page_layouts", [])
        if not page_layouts:
            return blocks
        
        for pl in page_layouts:
            mcp_blocks = pl.get("text_blocks", [])
            if not mcp_blocks:
                continue
            
            block_map = {}
            for i, mcp_block in enumerate(mcp_blocks):
                coords = mcp_block.get("coordinates", {})
                key = (round(coords.get("x1", 0), 1), round(coords.get("y1", 0), 1))
                block_map[key] = i
            
            sorted_blocks = []
            for block in blocks:
                bbox = block.get("bbox", (0, 0, 0, 0))
                key = (round(bbox[0], 1), round(bbox[1], 1))
                if key in block_map:
                    block["_mcp_order"] = block_map[key]
                    sorted_blocks.append(block)
                else:
                    block["_mcp_order"] = len(mcp_blocks)
                    sorted_blocks.append(block)
            
            sorted_blocks.sort(key=lambda b: b.get("_mcp_order", 999))
            for b in sorted_blocks:
                b.pop("_mcp_order", None)
            return sorted_blocks
        
        return blocks


def should_augment(complexity: Dict) -> bool:
    """Decision function: should we call MCP for this page?"""
    if complexity.get("complex"):
        return True
    if complexity.get("multi_column"):
        return True
    if complexity.get("overlap_pairs", 0) > 2:
        return True
    return False


async def augment_document(pdf_path: str, page_complexities: List[Dict]) -> Dict[int, Dict]:
    """Run MCP augmentation only on pages that need it."""
    session = MCPSession("uvx", ["mcp-pdf"])
    await session.start()
    
    augmentor = MCPAugmentor(session)
    results = {}
    
    try:
        for i, complexity in enumerate(page_complexities):
            if should_augment(complexity):
                result = await augmentor.analyze_page(pdf_path, i + 1)
                results[i + 1] = result
        
        return results
    finally:
        session.close()


if __name__ == "__main__":
    import sys
    asyncio.run(augment_document(sys.argv[1] if len(sys.argv) > 1 else "messy_test.pdf", []))