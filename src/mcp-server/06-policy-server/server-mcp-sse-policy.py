import asyncio
import logging
from datetime import datetime
import os
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

policy_search_tool = PolicySearchTool()

POLICY_PROMPT_TEMPLATE = (
    "You are connected to a Policy MCP server that holds HR, compensation and company policy knowledge. "
    "Use the search_policies tool to vector search policy content and narrow by category if needed. "
    "Always reference the intent, category, content, and description from the tool output and mention the retrieved_at timestamp."
)

@mcp.resource("config://version")
def get_version() -> dict:
    return {
        "version": "1.0.0",
        "features": ["tools", "resources"],
    }


@mcp.resource("policy://prompt-guidance")
def get_policy_prompt_guidance() -> dict:
    return {
        "title": "Policy answer guidance",
        "description": "Guidance for framing policy responses using the search_policies tool.",
        "prompt": POLICY_PROMPT_TEMPLATE,
        "required_fields": ["intent", "category", "content", "description", "retrieved_at"],
        "updated_at": datetime.now(pytz.utc).isoformat(),
    }


@mcp.tool()
def search_policies(query: str, top_k: int = 5, category: str | None = None) -> list[dict]:
    """Vector-search policy knowledge and return the structured results the frontend expects."""
    logger.info("Tool called: search_policies(query=%s, category=%s, top_k=%s)", query, category, top_k)
    retrieved_at = datetime.now(pytz.utc).isoformat()
    query_examples = policy_search_tool.run(query=query, top_k=top_k, category=category)

    payload: list[dict] = []
    for example in query_examples:
        payload.append(
            {
                "id": example.id,
                "intent": example.intent,
                "category": example.category,
                "content": example.content,
                "description": example.description,
                "score": example.score,
                "retrieved_at": retrieved_at,
            }
        )

    logger.info("Returning %s policy entries", len(payload))
    return payload


@mcp.prompt()
def describe_policy_capabilities() -> list[base.Message]:
    """Explain how to use this MCP server to retrieve the latest company policy knowledge."""

    return [
        base.Message(
            role="user",
            content=[
                base.TextContent(
                    text=(
                        "You are connected to a Policy MCP server that curates HR, compensation, and company policy knowledge. "
                        "Explain how to use the search_policies tool to: (1) run a vector search for policy content and optionally narrow by category, "
                        "(2) consult the policy://prompt-guidance resource so answers include intent, category, content, description, and the retrieved_at timestamp, "
                        "(3) surface structured policy context such as the relevant intent, category, and description when summarizing the response"
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
