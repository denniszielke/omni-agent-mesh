import os
import logging
from typing import override

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import (
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
)
from a2a.utils import new_task, new_text_artifact
from agent_framework import MCPStreamableHTTPTool
from intranet_agent.model_client import create_chat_client as _create_openai_client
from agent_framework import HostedMCPTool
from intranet_agent.model_client import create_chat_client as _create_openai_client
from dotenv import load_dotenv

load_dotenv()
model_name = os.environ["AZURE_OPENAI_BIG_CHAT_DEPLOYMENT_NAME"]

if not model_name:
    raise ValueError("Please set AZURE_OPENAI_BIG_CHAT_DEPLOYMENT_NAME  in your .env file")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
logging.getLogger('azure.core.pipeline.policies.http_logging_policy').setLevel(logging.WARNING)
logging.getLogger('azure.monitor.opentelemetry.exporter.export').setLevel(logging.WARNING)


class IntranetAgentExecutor(AgentExecutor):
    """HR Intranet agent using Microsoft Agent Framework with MCP integration."""

    def __init__(self):
        logging.info("Creating IntranetAgentExecutor with model %s", model_name)
        self.agent = _create_openai_client(model_name)
        
        # Get the MCP server URL from environment or use default
        self.mcp_server_url = os.getenv("INTRANET_MCP_SERVER_URL", "http://localhost:8001/mcp")
        logger.info(f"Connecting to Intranet MCP server at: {self.mcp_server_url}")

    @override
    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        
        task = context.current_task

        if not context.message:
            raise Exception('No message provided')

        if not task:
            task = new_task(context.message)
            await event_queue.enqueue_event(task)

        query = context.get_user_input()

        system_prompt=(
                "You are a helpful intranet assistant with access to the company's intranet news system. "
                "You can help users with:\n"
                "- Listing all company office locations (St. Louis, London, Berlin, Leverkusen)\n"
                "- Getting news and announcements for specific office locations\n"
                "- Listing all company departments (HR, Finance, Engineering, Marketing, Sales, Customer Support, IT, Legal, Operations, R&D)\n"
                "- Getting news and updates for specific departments\n\n"
                "Use the available tools to retrieve office locations, departments, and their associated news. "
                "Be helpful and provide relevant information from the intranet. Be professional and concise."
        )
        
        query = system_prompt + "\n\nUser question: " + context.get_user_input()

        # get_response may return a rich object; coerce to string for A2A
        response = await self.agent.get_response(
            query,
            tools=[
                MCPStreamableHTTPTool(
                    name="Intranet News Server", 
                    url=self.mcp_server_url
                )
            ],
        )

        # Ensure the artifact text is always a plain string
        response_text = str(response)
    
        await event_queue.enqueue_event(
            TaskArtifactUpdateEvent(
                append=False,
                context_id=task.context_id,
                task_id=task.id,
                last_chunk=True,
                artifact=new_text_artifact(
                    name='current_result',
                    description='Result of request to intranet news agent.',
                    text=response_text,
                ),
            )
        )
        await event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                status=TaskStatus(state=TaskState.completed),
                final=True,
                context_id=task.context_id,
                task_id=task.id,
            )
        )

    @override
    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        raise Exception('cancel not supported')