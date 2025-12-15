import asyncio
import logging
from datetime import datetime

import pytz
import uvicorn
from dotenv import load_dotenv
from fastmcp import FastMCP
from mcp.server.fastmcp.prompts import base
from policy_search_tool import PolicySearchTool

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("Policy")

mcp = FastMCP("Policy")

# Use Streamable HTTP transport (recommended for web deployments)
streamable_http_app = mcp.http_app(path="/mcp", transport="streamable-http")

@mcp.resource("config://version")
def get_version() -> dict:
    return {
        "version": "1.0.0",
        "features": ["tools", "resources"],
    }




@mcp.prompt()
def describe_intranet_capabilities() -> list[base.Message]:
    """Explain how to use this MCP server to retrieve knowledge from the Intranet."""

    return [
        base.Message(
            role="user",
            content=[
                base.TextContent(
                    text=(
                        "You are connected to a Intranet MCP server that provides "
                        "knowledge and information from the company Intranet. "
                        "Explain how to: (1) list news and knowledge specific to office locations, ",
                        "(2) get documentation around the personell policies, regulations and documentation for benefits, payments and vacation, ",
                        "(3) find specifc information about teams and departments within the company from the Intranet"
                    )
                )
            ],
        )
    ]


async def check_mcp(mcp: FastMCP):
    tools = await mcp.get_tools()
    resources = await mcp.get_resources()
    templates = await mcp.get_resource_templates()

    print(f"{len(tools)} Tool(s): {', '.join([t.name for t in tools.values()])}")
    print(
        f"{len(resources)} Resource(s): {', '.join([r.name for r in resources.values()])}"
    )
    print(
        f"{len(templates)} Resource Template(s): {', '.join([t.name for t in templates.values()])}"
    )

    return mcp


if __name__ == "__main__":
    try:
        asyncio.run(check_mcp(mcp))
        uvicorn.run(streamable_http_app, host="0.0.0.0", port=8001)
    except KeyboardInterrupt:
        print("\nProgram interrupted by user. Cleaning up...")
    except Exception as e:
        print(f"An error occurred: {e}")
