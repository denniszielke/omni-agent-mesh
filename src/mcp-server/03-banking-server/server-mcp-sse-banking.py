import asyncio

from mcp.server import Server
from mcp.server.sse import run_sse_server

from run-mcp-banking import build_banking_agent


async def main() -> None:
    agent = build_banking_agent()

    server = Server("banking-mcp-server")

    # Expose the agent tools via MCP as functions
    for tool in agent.tools:
        server.function(tool)

    await run_sse_server(server)


if __name__ == "__main__":
    asyncio.run(main())
