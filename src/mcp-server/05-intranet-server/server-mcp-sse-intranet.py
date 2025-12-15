import asyncio
import logging
from datetime import datetime
import os
import pytz
import uvicorn
from dotenv import load_dotenv
from fastmcp import FastMCP
from mcp.server.fastmcp.prompts import base

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("Intranet")

mcp = FastMCP("Intranet")

# Use Streamable HTTP transport (recommended for web deployments)
streamable_http_app = mcp.http_app(path="/mcp", transport="streamable-http")

@mcp.resource("config://version")
def get_version() -> dict:
    return {
        "version": "1.0.0",
        "features": ["tools", "resources"],
    }


LOCATIONS = {
    "St. Louis": "America/USA",
    "London": "Europe/UK",
    "Berlin": "Europe/Germany",
    "Leverkusen": "Europe/Germany",
}

@mcp.tool()
def list_office_locations() -> list[str]:
    """List the six popular locations that this server supports."""
    logger.info("Tool called: list_office   _locations")
    result = list(LOCATIONS.keys())
    logger.info(f"Returning {len(result)} supported locations")
    return result


NEWS_BY_LOCATION = {
    "St. Louis": ["New cafeteria opening next month.", "Annual company picnic scheduled for July."],
    "London":
    [
        "Office renovation completed.",
        "New parking facilities available for employees."
    ],
    "Berlin": ["Launch of new employee wellness program.", "Quarterly town hall meeting next week."],
    "Leverkusen": ["Introduction of flexible working hours.", "New bike-to-work scheme launched."],
}


@mcp.tool()
def get_news_for_office_locations(locations: list[str]) -> list[str]:
    """Get static weather for multiple supported locations at their current local times."""
    logger.info(f"Tool called: get_weather_for_multiple_locations(locations={locations})")
    results: list[str] = []
    for loc in locations:
        results.append(NEWS_BY_LOCATION.get(loc, []))
    logger.info(f"Returning news for {len(results)} locations")
    return results



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
        port = int(os.getenv("PORT", "8080"))
        uvicorn.run(streamable_http_app, host="0.0.0.0", port=port)
    except KeyboardInterrupt:
        print("\nProgram interrupted by user. Cleaning up...")
    except Exception as e:
        print(f"An error occurred: {e}")
