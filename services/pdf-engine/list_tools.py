#!/usr/bin/env python3
"""
List available tools in mcp-pdf.
"""

import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def list_tools():
    params = StdioServerParameters(command="uvx", args=["mcp-pdf"])
    
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # List available tools
            tools = await session.list_tools()
            print("Available tools:")
            for tool in tools.tools:
                print(f"  - {tool.name}: {tool.description}")
                print(f"    Input schema: {tool.inputSchema}")


if __name__ == "__main__":
    asyncio.run(list_tools())