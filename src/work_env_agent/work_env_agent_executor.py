import os
import logging
from random import randint
from typing import Annotated, Optional, override

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import (
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
)
from a2a.utils import new_agent_text_message, new_task, new_text_artifact
from work_env_agent.model_client import create_chat_client as _create_openai_client
from dotenv import load_dotenv
from work_env_agent.policy_search_tool import PolicySearchTool
from pydantic import Field

load_dotenv()

model_name = os.environ["AZURE_OPENAI_BIG_CHAT_DEPLOYMENT_NAME"]
policy_search_tool = PolicySearchTool()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
logging.getLogger('azure.core.pipeline.policies.http_logging_policy').setLevel(logging.WARNING)
logging.getLogger('azure.monitor.opentelemetry.exporter.export').setLevel(logging.WARNING)


def get_vacation_days(
    location: Annotated[str, Field(description="The work country location of the employee (e.g., Germany, USA, UK, Netherlands)")],
) -> str:
    """Get the number of vacation days for an employee based on their work location. For detailed vacation policies, use search_policy_information with queries about statutory vacation, BUrlG, or leave entitlements."""
    countries = ["Germany", "USA", "UK", "Netherlands"]
    logging.info("get_vacation_days called with location: %s", location)
    return f"In {location}, employees get {randint(15, 30)} vacation days per year."

def get_performance_evaluation_info() -> str:
    """Get basic performance evaluation schedule information. For detailed policies on promotions, reviews, and criteria, use search_policy_information with category 'hr-policies' or 'training-development'."""
    logging.info("get_performance_evaluation_info called")
    return "Performance evaluations are conducted annually, typically in Q1."

def get_payment_benefits_info() -> str:
    """Get basic payment and benefits overview. For detailed information on salary schedules, overtime, bonuses, reimbursements, parental leave, or retirement, use search_policy_information with category 'compensation-benefits'."""
    logging.info("get_payment_benefits_info called") 
    return "Employees are paid monthly, with benefits including health insurance and retirement plans."

def get_employee_id() -> str:
    """Simple tool returning a fake employee ID."""
    logging.info("get_employee_id called")
    return "EMP" + str(randint(1000, 9999))

def get_latest_relevant_content(
    query: Annotated[str, Field(description="The topic to search for recent updates about")],
    days: Annotated[int, Field(description="Number of days to look back for content")] = 30,
) -> str:
    """Get recent company news and updates related to a topic. For official HR policies, use search_policy_information instead."""
    news = [
        "Company expands remote work options.",
        "New health benefits introduced for employees.",
        "Annual performance reviews scheduled for next month.",
    ]
    logging.info("get_latest_relevant_content called with query: %s and days: %d", query, days)
    return f"Latest content related to '{query}': " + ", ".join(news)

async def search_policy_information(
    query: Annotated[str, Field(description="The search query to find relevant HR policy documents. Be specific about the topic.")],
    category: Annotated[Optional[str], Field(description="Optional category filter: 'hr-policies', 'compensation-benefits', 'training-development', or 'company-policy'")] = None,
) -> str:
    """Search for HR policy documents using semantic search. Available categories:
    - hr-policies: working hours, time off, remote work, harassment complaints, dress code, internal job postings, probation periods, performance evaluations, workplace complaints, employee referrals, statutory vacation entitlements (including German BUrlG regulations)
    - compensation-benefits: salary schedules, benefits overview, payslip access, overtime policy, bonuses/incentives, expense reimbursement, retirement, unpaid leave, parental leave, emergency financial aid
    - training-development: training programs, course enrollment, tuition reimbursement, promotions, mentorship programs
    - company-policy: policy violations, conflict resolution, flexible working hours, sabbaticals, HR contact options
    """
    try:
        logging.info("search_policy_information called with query: %s, category: %s", query, category)
        results = await policy_search_tool.run(query=query, top_k=5, category=category)
        if not results:
            return "No policy documents found matching your query."
        
        # Format results for the agent
        formatted_results = []
        for result in results:
            formatted_results.append(
                f"[Document ID: {result.id}] (Category: {result.category}, Intent: {result.intent})\n"
                f"Content: {result.content}\n"
                f"Description: {result.description}"
            )
        return "\n\n".join(formatted_results)
    except Exception as e:
        logging.exception("search_policy_information failed")
        return f"error: search_policy_information: {str(e)}"

def get_bonus_info(
    employee_id: Annotated[str, Field(description="The employee identifier for bonus lookup.")],
) -> str:
    """Get bonus information for a specific employee. For general bonus and incentive policies, use search_policy_information with a query about 'bonuses' or 'incentives' in category 'compensation-benefits'."""
    logging.info("get_bonus_info called with employee_id: %s", employee_id)
    return f"Employee {employee_id} has a bonus of ${randint(1000, 5000)} for this year."


class WorkEnvAgentExecutor(AgentExecutor):
    """Simple work environment Q&A agent using Microsoft agent framework."""

    def __init__(self):
        # Reuse the same authentication logic as the basic agent sample
        logging.info("Creating OpenAIChatClient for WorkEnvAgentExecutor with model %s", model_name)
        self.agent = _create_openai_client(model_name)

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

        system_prompt = (
            "You are a work environment agent that helps users with HR and workplace-related questions. "
            "IMPORTANT: Use the search_policy_information tool to find accurate policy information. "
            "Available policy categories: 'hr-policies' (working hours, time off, remote work, vacation entitlements, German BUrlG), "
            "'compensation-benefits' (salary, bonuses, overtime, parental leave, reimbursements), "
            "'training-development' (training programs, promotions, mentorship), "
            "'company-policy' (policy violations, conflict resolution, flexible hours, sabbaticals). "
            "When answering from policy documents, always cite the document ID in brackets [ID: X]. "
            "Do not make up policy information - always search first."
        )

        query = system_prompt + "\n\nUser question: " + context.get_user_input()

        # get_response may return a rich object; coerce to string for A2A
        response = await self.agent.get_response(
            query,
            tools=[
                get_vacation_days,
                get_performance_evaluation_info,
                get_payment_benefits_info,
                get_employee_id,
                get_bonus_info,
                search_policy_information,
                get_latest_relevant_content,
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
                    description='Result of request to work environment agent.',
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