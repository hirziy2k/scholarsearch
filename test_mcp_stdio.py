import warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
import sys
from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters
import asyncio

async def test():
    params = StdioServerParameters(command='uvx', args=['mcp-pdf'])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print(f'Tools: {len(tools.tools)}')
            for t in tools.tools[:5]:
                print(f'  {t.name}')

asyncio.run(test())