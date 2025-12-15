import os
import logging
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
from agent_framework import MCPStreamableHTTPTool
from src.intranet_agent.model_client import create_chat_client as _create_openai_client
from dotenv import load_dotenv

load_dotenv()
model_name = os.environ.get("AZURE_OPENAI_BIG_CHAT_DEPLOYMENT_NAME") or os.environ.get("COMPLETION_DEPLOYMENT_NAME")

if not model_name:
    raise ValueError("Please set AZURE_OPENAI_BIG_CHAT_DEPLOYMENT_NAME or COMPLETION_DEPLOYMENT_NAME in your .env file")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("intranet-agent-executor")


def intranet_agent_card(url: str) -> AgentCard:
    """Define the agent card for the Intranet HR Policy agent."""
    
    hr_policy_skill = AgentSkill(
        id='hr_policy_skill',
        name='Answer HR policy questions',
        description=(
            'The agent can answer questions about company HR policies including '
            'working hours, leave requests, remote work, dress code, probation periods, '
            'performance evaluations, and workplace complaints.'
        ),
        tags=['hr', 'policy', 'intranet', 'working-hours', 'leave'],
        examples=[
            'What is the company\'s working hour policy?',
            'How do I request time off?',
            'What are the rules for remote work?',
            'What is the probation period for new employees?',
            'How often is performance evaluated?',
        ],
    )

    compensation_benefits_skill = AgentSkill(
        id='compensation_benefits_skill',
        name='Answer compensation and benefits questions',
        description=(
            'The agent can answer questions about salary schedules, benefits, '
            'payslips, overtime policy, bonuses, expense reimbursement, retirement, '
            'and parental leave.'
        ),
        tags=['compensation', 'benefits', 'salary', 'bonus', 'leave'],
        examples=[
            'When do employees receive their salary?',
            'What benefits does the company provide?',
            'How do I access my payslip?',
            'Does the company offer bonuses?',
            'How do I apply for maternity leave?',
        ],
    )

    training_development_skill = AgentSkill(
        id='training_development_skill',
        name='Answer training and development questions',
        description=(
            'The agent can answer questions about training programs, course enrollment, '
            'higher education sponsorship, promotions, and mentorship opportunities.'
        ),
        tags=['training', 'development', 'promotion', 'mentorship', 'education'],
        examples=[
            'What training programs does the company offer?',
            'How do I enroll in a training course?',
            'Does the company sponsor higher education?',
            'How do promotions work?',
            'Is mentorship available?',
        ],
    )

    statutory_vacation_skill = AgentSkill(
        id='statutory_vacation_skill',
        name='Answer statutory vacation questions (Germany)',
        description=(
            'The agent can answer detailed questions about German statutory vacation '
            'entitlement (BUrlG), including minimum days, carryover rules, part-time '
            'calculations, probation accrual, and special cases.'
        ),
        tags=['vacation', 'statutory', 'germany', 'burlg', 'leave'],
        examples=[
            'How many days of statutory vacation are required in Germany?',
            'How is vacation calculated for part-time employees?',
            'What happens to unused vacation?',
            'Do severely disabled employees receive extra vacation?',
            'What are my vacation rights during probation?',
        ],
    )

    company_policy_skill = AgentSkill(
        id='company_policy_skill',
        name='Answer general company policy questions',
        description=(
            'The agent can answer questions about policy violations, workplace conflicts, '
            'flexible working hours, sabbaticals, and how to contact HR.'
        ),
        tags=['policy', 'hr', 'conflict', 'flexible-hours', 'contact'],
        examples=[
            'What are the consequences of policy violations?',
            'How does the company handle workplace conflicts?',
            'Can I request flexible working hours?',
            'Are employees allowed to take sabbaticals?',
            'How can I contact HR?',
        ],
    )

    agent_card = AgentCard(
        name='HR Intranet Agent',
        description=(
            'An HR intranet agent that provides comprehensive information about company '
            'policies, compensation, benefits, training programs, and statutory vacation '
            'entitlements (Germany). Access to internal HR knowledge base and policy documentation.'
        ),
        url=f'{url}',
        version='1.0.0',
        default_input_modes=['text'],
        default_output_modes=['text'],
        capabilities=AgentCapabilities(
            input_modes=['text'],
            output_modes=['text'],
            streaming=False,
        ),
        skills=[
            hr_policy_skill,
            compensation_benefits_skill,
            training_development_skill,
            statutory_vacation_skill,
            company_policy_skill,
        ],
        examples=[
            'What is the company\'s working hour policy?',
            'When do employees receive their salary?',
            'How many vacation days do I get in Germany?',
            'What training programs are available?',
            'How do I request time off or leave?',
            'What happens to unused vacation days?',
            'Does the company offer bonuses or incentives?',
            'How is vacation calculated for part-time employees?',
        ],
    )
    return agent_card


class IntranetAgentExecutor(AgentExecutor):
    """HR Intranet agent using Microsoft Agent Framework with MCP integration."""

    def __init__(self):
        logging.info("Creating IntranetAgentExecutor with model %s", model_name)
        self.chat_client = _create_openai_client(model_name)
        
        # Get the MCP server URL from environment or use default
        self.mcp_server_url = os.getenv("INTRANET_MCP_SERVER_URL", "http://localhost:8001/mcp")
        logger.info(f"Connecting to Intranet MCP server at: {self.mcp_server_url}")

    @override
    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        from agent_framework import ChatAgent
        
        task = context.current_task

        if not context.message:
            raise Exception('No message provided')

        if not task:
            task = new_task(context.message)
            await event_queue.enqueue_event(task)

        query = context.get_user_input()

        # Create ChatAgent with HostedMCPTool pointing to the Intranet MCP server
        async with ChatAgent(
            chat_client=self.chat_client,
            name="HRIntranetAgent",
            instructions=(
                "You are a helpful HR intranet assistant with access to the company's HR policy knowledge base. "
                "You can answer questions about:\n"
                "- HR policies (working hours, leave requests, remote work, dress code, probation, performance reviews)\n"
                "- Compensation & Benefits (salary, bonuses, payslips, overtime, retirement, parental leave)\n"
                "- Training & Development (courses, sponsorship, promotions, mentorship)\n"
                "- Statutory Vacation Entitlements in Germany (BUrlG regulations, minimum days, carryover, part-time calculations)\n"
                "- Company policies (violations, conflicts, flexible hours, sabbaticals, HR contact)\n\n"
                "Use the available tools to search the HR knowledge base and provide accurate, helpful answers. "
                "Always cite relevant policies when applicable. Be professional and concise."
            ),
            tools=MCPStreamableHTTPTool(
                name="HR Intranet MCP",
                url=self.mcp_server_url,
            ),
        ) as agent:
            result = await agent.run(query)
            
            # Extract the text response
            response_text = ""
            for msg in result.messages:
                if msg.role == "assistant" and msg.text:
                    response_text += msg.text

            if not response_text:
                response_text = str(result)

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