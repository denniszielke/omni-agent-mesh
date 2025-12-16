import os
from typing import Optional
import logging
import math
import httpx
from dotenv import load_dotenv

from a2a.types import (
    AgentCapabilities,
    AgentCard,
)
from a2a.client import A2ACardResolver
from agent_framework.a2a import A2AAgent

from src.data.agent_query_example import AgentQueryExample
from src.data.semantic_agent_card import AgentRepositoryCard
from src.intranet_agent.intranet_agent_card import intranet_agent_card as get_intranet_agent_card
from src.data.query_execution_result import QueryExecutionResult
from src.work_env_agent.work_env_agent_card import work_env_agent_card as get_work_env_agent_card
from src.workflows.model_client import create_chat_client

load_dotenv()

AZURE_OPENAI_SMALL_CHAT_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_SMALL_CHAT_DEPLOYMENT_NAME", "")
AZURE_OPENAI_BIG_CHAT_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_BIG_CHAT_DEPLOYMENT_NAME", "")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AgentRegistryTool():
    """Tool that searches for similar queries using Azure AI Search."""

    def __init__(self) -> None:
        self.AGENT_CARDS = {}

        default_domain = os.environ.get("DEFAULT_DOMAIN", "").strip()
        if default_domain:
            intranet_agent_url = f"https://intranet-agent.{default_domain}"
            get_work_env_agent_url = f"https://work-env-agent.{default_domain}"
        else:
            intranet_agent_url = "http://localhost:8081"
            get_work_env_agent_url = "http://localhost:8080"

        self.add_agent_card('intranet_agent', get_intranet_agent_card(url=intranet_agent_url))
        self.add_agent_card('work_env_agent', get_work_env_agent_card(url=get_work_env_agent_url))


    
    def add_agent_card(self, agent_id: str, agent_card: AgentCard) -> None:
        """Add an agent card to the tool's collection."""

        # description_vector = get_openai_client().embeddings.create(
        #     input=agent_card.description, model=EMBEDDING_DEPLOYMENT, dimensions=EMBEDDING_DIMENSIONS
        # ).data[0].embedding

        skill_text = ""
        example_text = ""
        for skill in agent_card.skills:
            skill_text += f"{skill.name}: {skill.description}, examples: {skill.examples}  \n"
            for example in skill.examples:
                example_text += f"{example}  \n"
        # skills_vector = get_openai_client().embeddings.create(
        #     input=skill_text, model=EMBEDDING_DEPLOYMENT, dimensions=EMBEDDING_DIMENSIONS
        # ).data[0].embedding


        
        # examples_vector = get_openai_client().embeddings.create(
        #     input=example_text, model=EMBEDDING_DEPLOYMENT, dimensions=EMBEDDING_DIMENSIONS
        # ).data[0].embedding

        new_agent_card = AgentRepositoryCard(agent_id=agent_id, name=agent_card.name, url=agent_card.url, description=agent_card.description, skills=skill_text, examples=example_text)

        self.AGENT_CARDS[agent_id] = new_agent_card

    async def generate_agent_recommendation(self, query: str) -> AgentQueryExample:
        """Execute the search and return a list of AgentQueryExample objects."""
        try:

            chat_client = create_chat_client(model_name=AZURE_OPENAI_BIG_CHAT_DEPLOYMENT_NAME, agent_name="Recommender")

            recommender = chat_client.create_agent(
                name="Recommender",
                instructions=(
                    "You are a recommender agent that suggest which of the available agents is best suited to answer the user's query. ", 
                    "You should create a prompt for the selected agent that will help it answer the user's query effectively. ",
                    "This is the list of available agents: " + ", ".join([f"{card.agent_id}: {card.name}, description: {card.description}, skills: {card.skills}, examples: {card.examples}" for card in self.AGENT_CARDS.values()]) + ". ",
                    "Based on the user's query, recommend the most appropriate agent by providing its agent_id, a suitable query for that agent, a brief description of why this agent is appropriate, the intent the category, and the complexity level (low, medium, high) of the query. ",
                    "This is the user input:"    + query + ". "
                ),
                tools=[],
            )

            response = await recommender.run(
                "Please provide a query for one of the available agents, and explain which agent is best suited to answer it and why.",
                response_format=AgentQueryExample
            )

            if response.value:
                agent_query_info = response.value
                print(f"Agent ID: {agent_query_info.agent_id}, Query: {agent_query_info.query}, Description: {agent_query_info.description}, Intent: {agent_query_info.intent}, Category: {agent_query_info.category}, Complexity: {agent_query_info.complexity}, Score: {agent_query_info.score}")
            else:
                print("No structured data found in response")
            
            return agent_query_info
            
        except Exception as exc:  # pragma: no cover - defensive
            logger.error(f"Error searching for queries: {exc}")
            raise

    def agent_comparison(self, vector1, vector2):
        """
        Get cosine similarity value between two embedded vectors
        """
        if (len(vector1) != len(vector2)):
            print("Vector1 has length: ", len(vector1))
            print("Vector2 has length: ", len(vector2))
            raise ValueError("Vectors must be the same length")

        dot_product = sum(x * y for x, y in zip(vector1, vector2))
        magnitude1 = math.sqrt(sum(x * x for x in vector1))
        magnitude2 = math.sqrt(sum(x * x for x in vector2))
        cos_similarity = round(dot_product / (magnitude1 * magnitude2), 10)
        return cos_similarity

    async def execute_agent(self, agent_id: str, query: str) -> QueryExecutionResult:
        """Execute the agent using A2A protocol and return the result."""
        try:
            # Get the agent card from the registry
            if agent_id not in self.AGENT_CARDS:
                logger.error(f"Agent with id '{agent_id}' not found in registry")
                return QueryExecutionResult(
                    id=agent_id,
                    query=query,
                    content=f"Agent '{agent_id}' not found in registry",
                    is_error=True
                )

            agent_repository_card = self.AGENT_CARDS[agent_id]
            a2a_agent_host = agent_repository_card.url

            # Initialize A2ACardResolver
            async with httpx.AsyncClient(timeout=80.0) as http_client:
                resolver = A2ACardResolver(httpx_client=http_client, base_url=a2a_agent_host)

                # Get agent card
                agent_card = await resolver.get_agent_card()
                logger.info(f"Found agent: {agent_card.name} - {agent_card.description}")

                # Create A2A agent instance
                agent = A2AAgent(
                    name=agent_card.name,
                    description=agent_card.description,
                    agent_card=agent_card,
                    url=a2a_agent_host,
                )

                logger.info(f"Found agent capabilities: {agent_card}")

                # Invoke the agent and get the result
                logger.info(f"Sending message to {agent_card.name} agent...")
                response = await agent.run(query)

                # Extract the response content
                response_content = str(response.value) if response.value else str(response)

                return QueryExecutionResult(
                    id=agent_id,
                    query=query,
                    content=response_content,
                    score=1.0,
                    is_error=False
                )

        except Exception as exc:  # pragma: no cover - defensive
            logger.error(f"Error executing agent '{agent_id}': {exc}")
            return QueryExecutionResult(
                id=agent_id,
                query=query,
                content=str(exc),
                is_error=True
            )