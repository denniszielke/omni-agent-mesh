# Copyright (c) Microsoft. All rights reserved.

import asyncio
import os

import httpx
from a2a.client import A2ACardResolver
from agent_framework.a2a import A2AAgent

from dotenv import load_dotenv

load_dotenv()

"""
Agent2Agent (A2A) Protocol Integration Sample

This sample demonstrates how to connect to and communicate with the Work Environment
agent using the Agent2Agent (A2A) protocol. A2A is a standardized communication
protocol that enables interoperability between different agent systems, allowing
agents built with different frameworks and technologies to communicate seamlessly.

For more information about the A2A protocol specification, visit: https://a2a-protocol.org/latest/

Key concepts demonstrated:
- Discovering A2A-compliant agents using AgentCard resolution
- Creating A2AAgent instances to wrap external A2A endpoints
- Converting Agent Framework messages to A2A protocol format
- Handling A2A responses (Messages and Tasks) back to framework types

To run this sample:
1. Start the Work Environment agent server: `uv run python -m src.work_env_agent.main`
2. (Optional) Set the A2A_AGENT_HOST environment variable to a remote WorkEnv endpoint if you are not using the default `http://localhost:8080`
3. Ensure the target agent exposes its AgentCard at /.well-known/agent.json
4. Run: `uv run python -m src.agent_clients.work_env_agent_client`

The sample will:
- Connect to the specified A2A agent endpoint
- Retrieve and parse the agent's capabilities via its AgentCard
- Send a message using the A2A protocol
- Display the agent's response

Visit the README.md for more details on setting up and running A2A agents.
"""


async def main():
    """Demonstrates connecting to and communicating with an A2A-compliant agent."""
    # Get A2A agent host from environment, defaulting to the local WorkEnv agent

    a2a_agent_host = os.getenv("A2A_AGENT_HOST", f"http://localhost:8080")

    default_domain = os.environ.get("DEFAULT_DOMAIN", "").strip()
    if default_domain:
        a2a_agent_host = f"https://intranet-agent.{default_domain}"

    print(f"Connecting to A2A agent at: {a2a_agent_host}")

    # Initialize A2ACardResolver
    async with httpx.AsyncClient(timeout=80.0) as http_client:
        resolver = A2ACardResolver(httpx_client=http_client, base_url=a2a_agent_host)

        # Get agent card
        agent_card = await resolver.get_agent_card()
        print(f"Found agent: {agent_card.name} - {agent_card.description}")

        # Create A2A agent instance
        agent = A2AAgent(
            name=agent_card.name,
            description=agent_card.description,
            agent_card=agent_card,
            url=a2a_agent_host,
        )

        print("Found agent capabilities:")
        print(agent_card)

        # Invoke the agent and output the result
        print("\nSending message to Work Environment agent...")
        response = await agent.run(
            "Tell me the latest news for my IT department from the Intranet"
        )

        # Print the response
        print("\nAgent Response:")
        for message in response.messages:
            print(message.text)

        print("\nSending message to Work Environment agent...")
        response = await agent.run(
            "How many vacation days do I have here in Germany?"
        )

        print("\nAgent Response:")
        for message in response.messages:
            print(message.text)

if __name__ == "__main__":
    asyncio.run(main())