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
    WorkflowBuilder,
    WorkflowContext,
    ai_function,
    executor,
    handler,
)
from agent_framework.observability import get_tracer
from dotenv import load_dotenv

from src.data.agent_query_example import AgentQueryExample
from src.tools.agent_registry import AgentRegistryTool
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
_agent_registry_tool = AgentRegistryTool()
_taxonomy_tool = TaxonomyTool()

@ai_function
async def generate_agent_query(
    query: str, category: Optional[str] = None
) -> AgentQueryExample:
    """Generate an agent query recommendation by searching the agent registry.

    IMPORTANT: This tool queries the agent registry to find the most suitable agent
    for the given query. You MUST use this tool to identify which agent to use -
    do NOT assume or invent agent IDs on your own.

    Args:
        query: The user's natural language query describing what they want to accomplish.
        category: Optional category filter to narrow down the search.

    Returns:
        A dictionary containing the recommended agent information including:
        - agent_id: The unique identifier of the recommended agent (use this for execute_agent_query)
        - agent_name: Human-readable name of the agent
        - description: What the agent can do
        - confidence: How well the agent matches the query

    Usage:
        1. Call this tool FIRST to discover which agent can handle the user's request
        2. Review the returned agent recommendation before proceeding
        3. Use the returned agent_id in subsequent execute_agent_query calls
        4. NEVER fabricate agent IDs - always use values returned by this tool
    """

    try:
        agent_query = await _agent_registry_tool.generate_agent_recommendation(query=query)
        return agent_query.model_dump()
    except Exception as e:
        logging.exception("generate_agent_query failed")
        return [{"error": f"generate_agent_query: {str(e)}"}]

@ai_function
async def execute_agent_query(
    agent_id: str, query: str
) -> AgentQueryExample:
    """Execute a query using a specific agent identified by its agent_id.

    CRITICAL: Only use agent_id values that were returned by the generate_agent_query tool.
    Do NOT invent or guess agent IDs - this will cause execution failures.

    Args:
        agent_id: The unique identifier of the agent to execute. This MUST be an agent_id
                  returned from a previous call to generate_agent_query.
        query: The specific query or task to send to the agent for execution.

    Returns:
        A dictionary containing the execution results from the agent, including:
        - status: Whether the execution succeeded or failed
        - result: The actual output/response from the agent
        - metadata: Additional information about the execution

    Usage:
        1. ALWAYS call generate_agent_query first to get a valid agent_id
        2. Pass the exact agent_id returned - do not modify or fabricate IDs
        3. Formulate a clear, specific query for the agent to execute
        4. Base your summaries and responses ONLY on the data returned by this tool
        5. If execution fails, report the error - do not make up results
    """

    try:
        agent_query = await _agent_registry_tool.execute_agent(agent_id=agent_id, query=query)
        return asdict(agent_query)
    except Exception as e:
        logging.exception("execute_agent_query failed")
        return [{"error": f"execute_agent_query: {str(e)}"}]
    
@ai_function
async def get_domain_hints(table_name: Optional[str] = None) -> str:
    """Retrieve domain-specific vocabulary and terminology hints from the taxonomy.

    Use this tool to understand the correct terminology and domain concepts before
    formulating queries. This ensures you use accurate, domain-appropriate language.

    IMPORTANT: Always consult domain hints when:
    - The user mentions unfamiliar terms
    - You need to translate user language into domain terminology
    - You want to ensure query accuracy

    Args:
        table_name: Optional table name to filter hints (e.g., 'Plants', 'ProductionLines', 'Equipment').
                   If not provided, returns hints for all available domains.

    Returns:
        Comma-separated string of relevant domain terms and vocabulary.
        Use these exact terms when formulating queries - do not substitute with synonyms.

    Usage:
        1. Call this tool when you encounter domain-specific terminology
        2. Use the returned terms EXACTLY as provided in your queries
        3. Do not invent domain terms - only use what this tool returns
        4. If a user's term doesn't match, use search_term_hints to find alternatives
    """
    try:
        return _taxonomy_tool.get_domain_hints(table_name=table_name)
    except Exception as e:
        logging.exception("get_domain_hints failed")
        return f"error: get_domain_hints: {str(e)}"

@ai_function
async def search_term_hints(search_term: str) -> str:
    """Search the taxonomy for domain hints matching a specific term or keyword.

    Use this tool to find the correct domain terminology when you're unsure how
    a concept is represented in the system. This is essential for accurate query formulation.

    IMPORTANT: Call this tool when:
    - A user uses informal or ambiguous language
    - You need to map user terms to system terminology
    - You want to discover related concepts in a domain

    Args:
        search_term: The term to search for (e.g., 'plant', 'equipment', 'line', 'order').
                    Use singular form for best results.

    Returns:
        Formatted information about domains containing the search term, including:
        - Matching domain categories
        - Related terms and concepts
        - Contextual usage information

    Usage:
        1. Use this when the user's terminology is unclear or informal
        2. Search for key nouns from the user's request
        3. Use the returned terminology in your queries - do not paraphrase
        4. If no matches found, try alternative spellings or related terms
        5. NEVER assume terminology - always verify with this tool first
    """
    try:
        return _taxonomy_tool.get_term_hints(search_term=search_term)
    except Exception as e:
        logging.exception("search_term_hints failed")
        return f"error: search_term_hints: {str(e)}"

@ai_function
async def list_domain_categories() -> str:
    """List all available domain categories with their descriptions and capabilities.

    Use this tool to understand what domains and categories are available in the system.
    This provides a complete overview of the taxonomy structure.

    IMPORTANT: Call this tool when:
    - Starting a new conversation to understand available domains
    - The user asks about what topics/areas you can help with
    - You need to determine which domain a query belongs to

    Returns:
        Formatted list containing for each domain:
        - Category name and unique identifier
        - Description of what the domain covers
        - Common filters and query patterns
        - Example use cases

    Usage:
        1. Call this at the start to understand the full scope of available domains
        2. Use returned category names EXACTLY when filtering queries
        3. Reference domain descriptions to determine query routing
        4. Do NOT invent categories - only use those returned by this tool
        5. If a user's request doesn't fit any category, clarify with them
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
        "You are a Moderator responsible for clarifying the user's intent and ensuring correct terminology.\n\n"
        "YOUR RESPONSIBILITIES:\n"
        "1. Understand the user's request and identify key concepts\n"
        "2. Use tools to verify terminology - NEVER assume domain terms\n"
        "3. Map informal user language to official system terminology\n"
        "4. Clarify ambiguous requests before proceeding\n\n"
        "CRITICAL RULES:\n"
        "- ALWAYS use search_term_hints or get_domain_hints to verify terminology\n"
        "- NEVER invent or assume domain terms - only use terms returned by tools\n"
        "- If the user's terms don't match any domain, ask for clarification\n"
        "- Use list_domain_categories to understand available domains\n"
        "- Your output must be grounded in tool results - do not fabricate information\n\n"
        "WORKFLOW:\n"
        "1. Extract key terms from user's request\n"
        "2. Call search_term_hints for each key term to find correct terminology\n"
        "3. If needed, call get_domain_hints for specific domain context\n"
        "4. Reformulate the user's request using verified terminology\n"
        "5. Pass the clarified intent to the next agent\n\n"
        "OUTPUT FORMAT:\n"
        "Provide a clear summary of:\n"
        "- Original user intent\n"
        "- Verified terminology (with tool sources)\n"
        "- Clarified request ready for planning"
    ),
    tools=[search_term_hints, list_domain_categories, get_domain_hints],
)

# Get query hints from the schema tool's query hints tool
_query_hints = _taxonomy_tool.get_all_query_hints()

planner_client = create_chat_client(model_name=AZURE_OPENAI_BIG_CHAT_DEPLOYMENT_NAME, agent_name="Planner")

# Get available agents list for the planner
_available_agents = _agent_registry_tool.get_all_agents()

# Planner: designs a query plan based on the user's objective
planner = planner_client.create_agent(
    name="Planner",
    instructions=(
        "You are a Planner responsible for designing an execution plan based on the user's objective.\n\n"
        "=== AVAILABLE AGENTS (USE ONLY THESE) ===\n"
        f"{_available_agents}\n"
        "=== END OF AVAILABLE AGENTS ===\n\n"
        "CRITICAL CONSTRAINT: You can ONLY use the agents listed above. Do NOT invent, assume, or reference any other agents.\n\n"
        "YOUR RESPONSIBILITIES:\n"
        "1. Analyze the clarified intent from the Moderator\n"
        "2. Select the best agent(s) from the AVAILABLE AGENTS list above\n"
        "3. Design a step-by-step execution plan using ONLY those agents\n"
        "4. Ensure all terminology is verified with domain tools\n\n"
        "CRITICAL RULES:\n"
        "- You MUST ONLY use agent_id values from the AVAILABLE AGENTS list above\n"
        "- Do NOT fabricate, invent, or assume any agent names, IDs, or capabilities\n"
        "- If no agent from the list can handle the request, clearly state this limitation\n"
        "- Use search_term_hints and get_domain_hints to verify domain terminology\n"
        "- Your plan must be executable using ONLY the agents listed above\n"
        "- Match user intent to agent skills and examples from the list\n\n"
        "WORKFLOW:\n"
        "1. Review the clarified request from the Moderator\n"
        "2. Review the AVAILABLE AGENTS list and their capabilities\n"
        "3. Select the most appropriate agent(s) based on their skills and examples\n"
        "4. If domain terms need verification, use search_term_hints or get_domain_hints\n"
        "5. Create an execution plan with specific agent_ids from the available list\n\n"
        "OUTPUT FORMAT:\n"
        "Provide a structured plan with:\n"
        "- Goal: What the user wants to achieve\n"
        "- Selected Agent(s): List the exact agent_id values from the AVAILABLE AGENTS list\n"
        "- Justification: Why each selected agent is appropriate (reference their skills/examples)\n"
        "- Steps: Ordered list of agent executions with specific queries\n"
        "- Expected output: What data the execution should return\n\n"
        "REMINDER: If you cannot find a suitable agent from the available list, say so. Never make up agents."
    ),
    tools=[search_term_hints, get_domain_hints],
)


executor_client = create_chat_client(model_name=AZURE_OPENAI_SMALL_CHAT_DEPLOYMENT_NAME, agent_name="Executor")
# Executor: executes the chosen query plan
executor_agent = executor_client.create_agent(
    name="Executor",
    instructions=(
        "You are an Executor responsible for running the execution plan created by the Planner.\n\n"
        "YOUR RESPONSIBILITIES:\n"
        "1. Execute the plan step-by-step using execute_agent_query\n"
        "2. Collect and organize results from each agent execution\n"
        "3. Handle errors gracefully and report failures accurately\n"
        "4. Pass complete, unmodified results to the Summarizer\n\n"
        "CRITICAL RULES:\n"
        "- ONLY use agent_id values provided in the Planner's output\n"
        "- NEVER invent, modify, or guess agent IDs\n"
        "- Execute agents in the order specified by the plan\n"
        "- Report EXACT results returned by execute_agent_query - do not modify or embellish\n"
        "- If an execution fails, report the actual error - do not fabricate success\n"
        "- Do NOT add information that wasn't returned by the tools\n"
        "- If results are empty or unexpected, report this accurately\n\n"
        "WORKFLOW:\n"
        "1. Parse the execution plan from the Planner\n"
        "2. For each step, call execute_agent_query with the specified agent_id and query\n"
        "3. Capture the complete response from each execution\n"
        "4. Compile all results maintaining the original structure and data\n"
        "5. Pass the compiled results to the Summarizer\n\n"
        "OUTPUT FORMAT:\n"
        "Provide execution results with:\n"
        "- Execution status for each step (success/failure)\n"
        "- Complete, unmodified results from each agent\n"
        "- Any errors encountered (exact error messages)\n"
        "- Clear indication of what data is available for summarization"
    ),
    tools=[execute_agent_query],
)

summarizer_client = create_chat_client(model_name=AZURE_OPENAI_BIG_CHAT_DEPLOYMENT_NAME, agent_name="Summarizer")
# Summarizer: answers the original user question using execution results
summarizer = summarizer_client.create_agent(
    name="Summarizer",
    instructions=(
        "You are a Summarizer responsible for answering the user's original question using execution results.\n\n"
        "YOUR RESPONSIBILITIES:\n"
        "1. Review the original user question and the execution results\n"
        "2. Synthesize a clear, accurate answer based ONLY on the provided data\n"
        "3. Present information in a user-friendly format\n"
        "4. Acknowledge limitations when data is incomplete\n\n"
        "CRITICAL RULES:\n"
        "- ONLY use information from the execution results - do not add external knowledge\n"
        "- NEVER fabricate, invent, or assume data that wasn't in the results\n"
        "- If the results don't fully answer the question, clearly state what's missing\n"
        "- Quote or reference specific data points from the results\n"
        "- If results contain errors, explain what went wrong based on the error messages\n"
        "- Do NOT speculate about what the results 'might' contain\n"
        "- Distinguish clearly between facts from results and any necessary interpretation\n\n"
        "WORKFLOW:\n"
        "1. Identify the original user question\n"
        "2. Review all execution results from the Executor\n"
        "3. Extract relevant data points that address the question\n"
        "4. Organize the information logically\n"
        "5. Compose a clear, grounded response\n\n"
        "OUTPUT FORMAT:\n"
        "Provide a response that:\n"
        "- Directly answers the user's question\n"
        "- Cites specific data from execution results\n"
        "- Clearly indicates the source of each piece of information\n"
        "- Notes any limitations or gaps in the available data\n"
        "- Uses clear, accessible language"
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
    .add_edge(planner, executor_agent)
    .add_edge(executor_agent, summarizer)
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