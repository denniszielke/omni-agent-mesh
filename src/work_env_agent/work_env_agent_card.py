from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)


def work_env_agent_card(url: str) -> AgentCard:
    """Define the agent card for the work environment Q&A agent."""
    vacation_days_skill = AgentSkill(
        id='vacation_days_skill',
        name='Answer questions about vacation and leave policies',
        description=(
            'The agent can answer questions about vacation days, statutory leave entitlements (including German BUrlG), '
            'time off requests, parental leave, sabbaticals, and unpaid leave policies.'
        ),
        tags=['vacation', 'leave', 'time-off', 'q&a'],
        examples=[
            'How many vacation days do I get if I work from Germany?',
            'What is the statutory vacation entitlement under BUrlG?',
            'How do I request parental leave?',
            'Can I carry over unused vacation days?',
        ],
    )

    performance_evaluation_skill = AgentSkill(
        id='performance_evaluation_skill',
        name='Answer questions about performance and career development',
        description=(
            'The agent can answer questions about performance evaluations, promotions, '
            'training programs, mentorship, and tuition reimbursement.'
        ),
        tags=['performance', 'training', 'career', 'q&a'],
        examples=[
            'How often are performance evaluations conducted?',
            'How do promotions work within the company?',
            'What training programs are available?',
            'Is mentorship available within the company?',
        ],
    )

    payment_benefits_skill = AgentSkill(
        id='payment_benefits_skill',
        name='Answer questions about compensation and benefits',
        description=(
            'The agent can answer questions about salary schedules, bonuses, incentives, '
            'overtime policy, expense reimbursement, health benefits, and retirement plans.'
        ),
        tags=['payment', 'benefits', 'compensation', 'q&a'],
        examples=[
            'When do employees receive their salary?',
            'What benefits does the company provide?',
            'How do I claim reimbursement for work-related expenses?',
            'Does the company offer bonuses or incentives?',
        ],
    )

    hr_policy_skill = AgentSkill(
        id='hr_policy_skill',
        name='Answer questions about HR policies and workplace guidelines',
        description=(
            'The agent can answer questions about working hours, remote work policy, dress code, '
            'workplace complaints, harassment policies, policy violations, and conflict resolution.'
        ),
        tags=['hr', 'policies', 'workplace', 'q&a'],
        examples=[
            'What is the company\'s working hour policy?',
            'What are the rules for remote work?',
            'How do I file a workplace complaint?',
            'What are the consequences of policy violations?',
        ],
    )   

    agent_card = AgentCard(
        name='Work Environment Agent',
        description=(
            'A work environment question answering agent that can search and answer questions about HR policies, '
            'vacation and leave entitlements (including German BUrlG), compensation and benefits, training and development, '
            'remote work policies, and workplace guidelines. Uses semantic search to find relevant policy documents.'
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
        skills=[vacation_days_skill, performance_evaluation_skill, payment_benefits_skill, hr_policy_skill],
        examples=[
            'What is the statutory vacation entitlement in Germany?',
            'How do I apply for parental leave?',
            'What training programs does the company offer?',
            'How do I file a workplace complaint?',
        ],
    )
    return agent_card
