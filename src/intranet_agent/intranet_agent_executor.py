import logging
import os
from typing import override

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
)
from a2a.utils import new_task, new_text_artifact
from agent_framework import ChatAgent, MCPStreamableHTTPTool
from dotenv import load_dotenv

from intranet_agent.model_client import create_chat_client as _create_openai_client

load_dotenv()

logger = logging.getLogger("intranet_agent")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.WARNING)
logging.getLogger("azure.monitor.opentelemetry.exporter.export").setLevel(logging.WARNING)

model_name = os.getenv("AZURE_OPENAI_BIG_CHAT_DEPLOYMENT_NAME") or os.getenv("COMPLETION_DEPLOYMENT_NAME")
if not model_name:
    raise ValueError(
        "Please set AZURE_OPENAI_BIG_CHAT_DEPLOYMENT_NAME (preferred) or COMPLETION_DEPLOYMENT_NAME in your .env file"
    )


def intranet_agent_card(url: str) -> AgentCard:
    hr_policy_skill = AgentSkill(
        id="hr_policy_skill",
        name="HR policies",
        description="Answer questions about HR policies (working hours, leave, remote work, dress code, probation, complaints).",
        tags=["hr", "policy", "intranet"],
        examples=[
            "What is the company's working hour policy?",
            "How do I request time off?",
            "What are the rules for remote work?",
            "What is the dress code policy?",
        ],
    )

    compensation_benefits_skill = AgentSkill(
        id="compensation_benefits_skill",
        name="Compensation & benefits",
        description="Answer questions about salary schedule, benefits, payslips, overtime, bonuses, reimbursements, retirement, parental leave.",
        tags=["compensation", "benefits", "hr"],
        examples=[
            "When do employees receive their salary?",
            "What benefits does the company provide?",
            "How do I access my payslip?",
        ],
    )

    training_development_skill = AgentSkill(
        id="training_development_skill",
        name="Training & development",
        description="Answer questions about training programs, enrollment, education sponsorship, promotions, mentorship.",
        tags=["training", "development", "hr"],
        examples=[
            "What training programs does the company offer?",
            "How do I enroll in a training course?",
            "Does the company sponsor higher education?",
        ],
    )

    statutory_vacation_skill = AgentSkill(
        id="statutory_vacation_skill",
        name="Statutory vacation (Germany)",
        description="Answer questions about German statutory vacation entitlement (BUrlG): minimum days, carryover, proration, probation accrual, illness, termination.",
        tags=["vacation", "germany", "burlg", "hr"],
        examples=[
            "How many days of statutory vacation are required each year?",
            "How long can unused statutory vacation be carried over?",
            "How is vacation entitlement calculated for part-time employees?",
        ],
    )

    time_period_skill = AgentSkill(
        id="time_period_skill",
        name="Timeframes & deadlines",
        description="Clarify/answer timeframes and deadlines (waiting periods, submission windows, carryover dates, payout timing).",
        tags=["deadline", "timeframe", "schedule", "hr"],
        examples=[
            "When is the deadline for unused statutory vacation?",
            "How long is the probation period for new employees?",
            "How much notice is needed for parental leave applications?",
        ],
    )

    return AgentCard(
        name="HR Intranet Agent",
        description="Answers HR policy questions from the company knowledge base and can use the remote intranet MCP server.",
        url=url,
        version="1.0.0",
        default_input_modes=["text"],
        default_output_modes=["text"],
        capabilities=AgentCapabilities(input_modes=["text"], output_modes=["text"], streaming=False),
        skills=[
            hr_policy_skill,
            compensation_benefits_skill,
            training_development_skill,
            statutory_vacation_skill,
            time_period_skill,
        ],
        examples=[
            "What is the company's working hour policy?",
            "How do I request time off?",
            "When do employees receive their salary?",
            "How many vacation days do I get in Germany?",
            "When do unused vacation days expire?",
        ],
    )


class IntranetAgentExecutor(AgentExecutor):
    """HR intranet agent that calls a remote MCP server via streamable-http."""

    def __init__(self):
        logger.info("Creating IntranetAgentExecutor with model %s", model_name)
        self.chat_client = _create_openai_client(model_name)
        self.mcp_server_url = os.getenv("INTRANET_MCP_SERVER_URL", "http://localhost:8001/mcp")
        logger.info("Connecting to Intranet MCP server at: %s", self.mcp_server_url)

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
        instructions = (
            "You are a helpful HR intranet assistant. Use the provided tools to look up answers in the company knowledge base. "
            "If the user asks about a timeframe (deadlines, probation period, carry-over date, notice period), make sure you answer with the exact period/date; "
            "if the question is missing key timeframe details, ask a short clarifying question first. "
            "Be professional and concise."
        )

        async with ChatAgent(
            chat_client=self.chat_client,
            name="HRIntranetAgent",
            instructions=instructions,
            tools=MCPStreamableHTTPTool(name="Intranet MCP Server", url=self.mcp_server_url),
        ) as agent:
            result = await agent.run(query)

        # Extract assistant text (fallback to string)
        response_text_parts: list[str] = []
        for msg in getattr(result, "messages", []) or []:
            if getattr(msg, "role", None) == "assistant":
                text = getattr(msg, "text", None)
                if text:
                    response_text_parts.append(text)
        response_text = "\n".join(response_text_parts).strip() or str(result)
    
        await event_queue.enqueue_event(
            TaskArtifactUpdateEvent(
                append=False,
                context_id=task.context_id,
                task_id=task.id,
                last_chunk=True,
                artifact=new_text_artifact(
                    name='current_result',
                    description='Result of request to HR intranet agent.',
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