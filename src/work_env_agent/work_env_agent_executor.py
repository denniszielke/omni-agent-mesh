import os
import logging
from random import randint
from typing import Annotated, override

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
from a2a.utils import new_agent_text_message, new_task, new_text_artifact
from src.work_env_agent.model_client import create_chat_client as _create_openai_client
from dotenv import load_dotenv

from pydantic import Field

load_dotenv()

model_name = os.environ["AZURE_OPENAI_BIG_CHAT_DEPLOYMENT_NAME"]


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("agent-executor")

def get_vacation_days(
    location: Annotated[str, Field(description="The work country location of the employee")],
) -> str:
    """Simple weather tool returning fake conditions for a location."""
    countries = ["Germany", "USA", "UK", "Netherlands"]
    return f"In {location}, employees get {randint(15, 30)} vacation days per year."

def get_performance_evaluation_info() -> str:
    """Simple tool returning fake performance evaluation info."""
    return "Performance evaluations are conducted annually, typically in Q1."

def get_payment_benefits_info() -> str:
    """Simple tool returning fake payment and benefits info."""
    return "Employees are paid monthly, with benefits including health insurance and retirement plans."

def get_employee_id() -> str:
    """Simple tool returning a fake employee ID."""
    return "EMP" + str(randint(1000, 9999))

def get_bonus_info(
    employee_id: Annotated[str, Field(description="The employee identifier for bonus lookup.")],
) -> str:
    """Simple tool returning fake bonus info with a random bonus amount."""
    return f"Employee {employee_id} has a bonus of ${randint(1000, 5000)} for this year."

def work_env_agent_card(url: str) -> AgentCard:
    """Define the agent card for the work environment Q&A agent."""
    vacation_days_skill = AgentSkill(
        id='vacation_days_skill',
        name='Answer questions about vacation days',
        description=(
            'The agent can answer questions about vacation days based on location.'
        ),
        tags=['vacation', 'q&a'],
        examples=[
            'How many vacation days do I get if I work from St. Louis?',
            'What is the vacation policy for employees in Leverkusen?',
            'Who on my team is on vacation next week?',
        ],
    )

    performance_evaluation_skill = AgentSkill(
        id='performance_evaluation_skill',
        name='Answer questions about performance evaluations',
        description=(
            'The agent can answer questions about performance evaluations.'
        ),
        tags=['performance', 'q&a'],
        examples=[
            'When is my expected bonus his year?',
            'How often are performance evaluations conducted?',
            'What criteria are used for performance evaluations?',
        ],
    )

    payment_benefits_skill = AgentSkill(
        id='payment_benefits_skill',
        name='Answer questions about payment and benefits',
        description=(
            'The agent can answer questions about payment and benefits.'
        ),
        tags=['payment', 'benefits', 'q&a'],
        examples=[
            'What is the payment schedule for employees in Leverkusen?',
            'What is my expected salary payout this month?',
            'What benefits am I eligible for as a full-time employee?',
        ],
    )

    agent_card = AgentCard(
        name='Work Environment Agent',
        description=(
            'A work environment question answering agent that can answers questions about the company work environment especially' \
            'around remote work policies, vacation days, team mate availability, bonus, payments and benefits.'
        ),
        url=f'{url}',
        version='1.0.0',
        default_input_modes=['text'],
        default_output_modes=['text'],
        capabilities=AgentCapabilities(
            input_modes=['text'],
            output_modes=['text'],
            # The current executor implementation performs a single-turn completion
            # and returns the final result, so we do not enable streaming here.
            streaming=False,
        ),
        skills=[vacation_days_skill, performance_evaluation_skill, payment_benefits_skill],
        examples=[
            'What are my vacation days this year?',
            'What is the payment schedule for employees in Leverkusen?',
            'How much salary will I receive this month?',
        ],
    )
    return agent_card


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

        query = "You are a work environment agent and need to help users to ask their work environment related questions. Try to help the user with their input using the tools you have available. " + context.get_user_input()
        # Use the Microsoft agent framework chat client with the weather tool.
        # We do a single-turn completion and treat the result as the final task artifact.
        query = context.get_user_input()

        # get_response may return a rich object; coerce to string for A2A
        response = await self.agent.get_response(
            query,
            tools=[
                get_vacation_days,
                get_performance_evaluation_info,
                get_payment_benefits_info,
                get_employee_id,
                get_bonus_info,
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
                    description='Result of request to weather agent.',
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