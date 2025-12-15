# Copyright (c) Microsoft. All rights reserved.

"""Agent Workflow - Intent recognition, task Validation, and plan Execution.

This workflow demonstrates a multi-agent scenario:
- Moderator clarifies the user intent and terminology
- Planer retrieves example plans queries from Azure AI Search and makes a plan
- Executor executes the chosen plan with specialized agents and tools
- Summarizer answers the original user question using execution results
"""

from json import tool
import os
from dataclasses import dataclass, asdict
from typing import Any, Optional
import logging


from agent_framework import (
    AgentExecutorResponse,
    ChatMessage,
    Executor,
    FunctionApprovalRequestContent,
    FunctionApprovalResponseContent,
    WorkflowBuilder,
    WorkflowContext,
    ai_function,
    executor,
    handler,
)
from agent_framework.observability import get_tracer
from dotenv import load_dotenv

from src.tools.search_tool import QuerySearchTool

from src.data.query_example import QueryExample
from src.data.query_execution_result import QueryExecutionResult
from src.tools.taxonomy_tool import TaxonomyTool
from src.workflows.model_client import create_chat_client, create_embedding_client, setup_azure_ai_observability

from opentelemetry.trace import SpanKind
from opentelemetry.trace.span import format_trace_id

load_dotenv()

logging.getLogger('azure.core.pipeline.policies.http_logging_policy').setLevel(logging.WARNING)
logging.getLogger('azure.monitor.opentelemetry.exporter.export').setLevel(logging.WARNING)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


AZURE_OPENAI_SMALL_CHAT_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_SMALL_CHAT_DEPLOYMENT_NAME", "")
AZURE_OPENAI_BIG_CHAT_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_BIG_CHAT_DEPLOYMENT_NAME", "")

# Instantiate shared tools
_search_tool = QuerySearchTool()
_taxonomy_tool = TaxonomyTool()

@ai_function
async def search_queries(
    query: str, top_k: int = 5, category: Optional[str] = None
) -> list[dict]:
    """Search for similar queries using Azure AI Search.

    Returns plain dicts so DevUI/agent framework can JSON-serialize results.
    """

    try:
        examples: list[QueryExample] = await _search_tool.run(
            query=query, top_k=top_k, category=category
        )
        return [asdict(e) for e in examples]
    except Exception as e:
        logging.exception("search_queries failed")
        return [{"error": f"search_queries: {str(e)}"}]


@ai_function
async def get_domain_hints(table_name: Optional[str] = None) -> str:
    """Get domain hints for a specific table or all tables.
    
    Args:
        table_name: Optional table name (e.g., 'Plants', 'ProductionLines', 'Equipment').
                   If not provided, returns hints for all domains.
    
    Returns:
        Comma-separated string of relevant domain terms.
    """
    try:
        return _taxonomy_tool.get_domain_hints(table_name=table_name)
    except Exception as e:
        logging.exception("get_domain_hints failed")
        return f"error: get_domain_hints: {str(e)}"

@ai_function
async def search_term_hints(search_term: str) -> str:
    """Search for domain hints related to a specific term or keyword.
    
    Args:
        search_term: The term to search for (e.g., 'plant', 'equipment', 'line', 'order').
    
    Returns:
        Formatted information about domains containing the search term.
    """
    try:
        return _taxonomy_tool.get_term_hints(search_term=search_term)
    except Exception as e:
        logging.exception("search_term_hints failed")
        return f"error: search_term_hints: {str(e)}"

@ai_function
async def list_domain_categories() -> str:
    """List all available domain categories with descriptions.
    
    Returns:
        Formatted list of all domain categories, their descriptions, and common filters.
    """
    try:
        return _taxonomy_tool.list_all_domains()
    except Exception as e:
        logging.exception("list_domain_categories failed")
        return f"error: list_domain_categories: {str(e)}"


# Create Azure OpenAI chat client
embedding_client = create_embedding_client()

moderator_client = create_chat_client(model_name=AZURE_OPENAI_SMALL_CHAT_DEPLOYMENT_NAME, agent_name="Moderator")
# Moderator: clarifies user intent and terminology
moderator = moderator_client.create_agent(
    name="Moderator",
    instructions=(
        "You are a moderator that is helping clarify the user's intent and terminology for a task. "
    ),
    tools=[search_term_hints, list_domain_categories, get_domain_hints],
)

# Get query hints from the schema tool's query hints tool
_query_hints = _taxonomy_tool.get_all_query_hints()

planner_client = create_chat_client(model_name=AZURE_OPENAI_BIG_CHAT_DEPLOYMENT_NAME, agent_name="Planner")
# Planner: designs a query plan based on the user's objective
planner = planner_client.create_agent(
    name="Planner",
    instructions=(
        "You are a Planner that is helping design a query plan based on the user's objective. " 
    ),
    tools=[search_queries, search_term_hints, get_domain_hints],
)


executor_client = create_chat_client(model_name=AZURE_OPENAI_SMALL_CHAT_DEPLOYMENT_NAME, agent_name="Executor")
# Executor: executes the chosen query plan
executor = executor_client.create_agent(
    name="Executor",
    instructions=(
        "You are a Executor that is executing the plann and is coordinating the output of the different agents"
    ),
    tools=[],
)

summarizer_client = create_chat_client(model_name=AZURE_OPENAI_BIG_CHAT_DEPLOYMENT_NAME, agent_name="Summarizer")
# Summarizer: answers the original user question using execution results
summarizer = summarizer_client.create_agent(
    name="Summarizer",
    instructions=(
        "You are a Summarizer that is answering the original user question using execution results."
    ),
)


workflow = (
    WorkflowBuilder(
        name="Friday Query Workflow",
        description=(
            "Multi-agent workflow: clarify objective, retrieve examples, "
            "design and validate queries, execute, then summarize."
        ),
    )
    .set_start_executor(moderator)
    .add_edge(moderator, planner)
    .add_edge(planner, executor)
    .add_edge(executor, summarizer)
    .build()
)

async def init_observability():
    """Initialize observability for the workflow."""
    await setup_azure_ai_observability(enable_sensitive_data=False)

def main():
    """Launch the branching workflow in DevUI."""

    import asyncio
    asyncio.run(
        init_observability()
    )

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger = logging.getLogger(__name__)

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8093"))
    auto_open = os.getenv("AUTO_OPEN", "True").lower() in (False, True)
    mode = os.getenv("MODE", "developer").lower()

    print("Host:", host)
    print("Port:", port)
    print("Auto open:", auto_open)
    print("Mode:", mode)

    from agent_framework.devui import serve

    # Build linear workflow:
    # Writer → Reviewer → Editor → Executor → Summarizer
    with get_tracer().start_as_current_span("Sequential Workflow Scenario", kind=SpanKind.CLIENT) as current_span:
        print(f"Trace ID: {format_trace_id(current_span.get_span_context().trace_id)}")
    

        logger.info("Starting Agent Workflow  Query Generation and Execution)")
        logger.info(f"Available at: http://{host}:{port}")
        logger.info("\nThis workflow demonstrates:")
        logger.info("- Moderator clarifies the user's intent and terminology for a task")
        logger.info("- Planner enriches context with example queries from Azure AI Search")
        logger.info("- Executor runs the selected query against Azure Data Explorer")
        logger.info("- Executor runs the selected query against Azure Data Explorer")
        logger.info("- Summarizer answers the original user question using the results")

        serve(entities=[workflow], host=host, port=port, auto_open=auto_open, mode=mode)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Workflow execution interrupted by user.")