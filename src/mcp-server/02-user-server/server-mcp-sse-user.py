import logging
import uvicorn
import os
import asyncio
import pytz
from datetime import datetime
from dotenv import load_dotenv
from typing import Any

from typing import List
from fastmcp import FastMCP
from mcp.server.fastmcp.prompts import base

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("UserTimeLocation")

mcp = FastMCP("UserTimeLocation")

# Use Streamable HTTP transport (recommended for web deployments)
streamable_http_app = mcp.http_app(path="/mcp", transport="streamable-http")

users = {
    "Dennis": {
        "name": "Dennis",
        "location": "Europe/Berlin",
    },
    "John": {
        "name": "John",
        "location": "America/New_York",
    },
}

@mcp.resource("config://version")
def get_version() -> dict: 
    return {
        "version": "1.2.0",
        "features": ["tools", "resources"],
    }

@mcp.tool()
async def get_current_user() -> str:
    """Get the username of the current user."""
    logger.info("Tool called: get_current_user")
    result = "Dennis"
    logger.info(f"Tool completed: get_current_user | result={result}")
    return result

@mcp.tool()
def get_current_location(username: str) -> str:
    """Get the current timezone location of the user for a given username."""
    logger.info(f"Tool called: get_current_location | username={username}")
    if username in users:
        result = users[username]["location"]
    else:
        result = "Europe/London"
    logger.info(f"Tool completed: get_current_location | username={username}, result={result}")
    return result

@mcp.tool()
def get_current_time(location: str) -> str:
    """Get the current time in the given location. The pytz is used to get the timezone for that location. Location names should be in a format like America/Seattle, Asia/Bangkok, Europe/London. Anything in Germany should be Europe/Berlin"""
    logger.info(f"Tool called: get_current_time | location={location}")
    try:
        location = str.replace(location, " ", "")
        location = str.replace(location, "\"", "")
        location = str.replace(location, "\n", "")
        # Get the timezone for the city
        timezone = pytz.timezone(location)

        # Get the current time in the timezone
        now = datetime.now(timezone)
        current_time = now.strftime("%I:%M:%S %p")

        logger.info(f"Tool completed: get_current_time | location={location}, result={current_time}")
        return current_time
    except Exception as e:
        logger.error(f"Tool error: get_current_time | location={location}, error={str(e)}")
        return "Sorry, I couldn't find the timezone for that location."
    

@mcp.tool()
async def move(username: str, newlocation: str) -> bool:
    """Move the user to a new location. Returns true if the user was moved successfully, false otherwise."""
    logger.info(f"Tool called: move | username={username}, newlocation={newlocation}")
    if username in users:
        users[username]["location"] = newlocation
        result = True
    else:
        result = False
    logger.info(f"Tool completed: move | username={username}, newlocation={newlocation}, success={result}")
    return result

@mcp.prompt()
def get_user_time(username: str) -> list[base.Message]:
    """Find out the current time for a user. This prompt is used to get the current time for a user in their location.
    Args:
        username: The username of the user
    """

    return [
        base.Message(
            role="user",
            content=[
                base.TextContent(
                    text=f"I'm trying to find the local time for the user'{username}. "
                    f"How can I find this out? Please provide step-by-step troubleshooting advice."
                )
            ]
        )
    ]

async def check_mcp(mcp: FastMCP):
    # List the components that were created
    tools = await mcp.get_tools()
    resources = await mcp.get_resources()
    templates = await mcp.get_resource_templates()
    
    print(
        f"{len(tools)} Tool(s): {', '.join([t.name for t in tools.values()])}"
    )
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
        uvicorn.run(streamable_http_app, host="0.0.0.0", port=8002)
    except KeyboardInterrupt:
        print("\nProgram interrupted by user. Cleaning up...")
    except Exception as e:
        print(f"An error occurred: {e}")