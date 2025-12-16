from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)


def intranet_agent_card(url: str) -> AgentCard:
    """Define the agent card for the Intranet News agent."""
    
    office_locations_skill = AgentSkill(
        id='office_locations_skill',
        name='List and browse office locations',
        description=(
            'The agent can list all company office locations and retrieve '
            'location-specific news and updates. Supported locations include '
            'St. Louis, London, Berlin, and Leverkusen.'
        ),
        tags=['offices', 'locations', 'intranet', 'news', 'updates'],
        examples=[
            'What office locations does the company have?',
            'List all office locations',
            'Where are our company offices located?',
            'Show me the available office sites',
        ],
    )

    office_news_skill = AgentSkill(
        id='office_news_skill',
        name='Get news for office locations',
        description=(
            'The agent can retrieve the latest news and announcements for specific '
            'office locations including updates about facilities, events, and local initiatives.'
        ),
        tags=['news', 'offices', 'announcements', 'updates', 'locations'],
        examples=[
            'What is the latest news from the St. Louis office?',
            'Tell me about updates from the London office',
            'What is happening at the Berlin office?',
            'Get news for all office locations',
            'Any announcements from the Leverkusen office?',
        ],
    )

    departments_skill = AgentSkill(
        id='departments_skill',
        name='List company departments',
        description=(
            'The agent can list all company departments including HR, Finance, '
            'Engineering, Marketing, Sales, Customer Support, IT, Legal, Operations, and R&D.'
        ),
        tags=['departments', 'organization', 'teams', 'structure'],
        examples=[
            'What departments does the company have?',
            'List all departments',
            'Show me the company structure',
            'What teams are in the organization?',
        ],
    )

    department_news_skill = AgentSkill(
        id='department_news_skill',
        name='Get news for departments',
        description=(
            'The agent can retrieve the latest news and updates for specific '
            'departments within the company.'
        ),
        tags=['news', 'departments', 'updates', 'announcements', 'teams'],
        examples=[
            'What is the latest news from the Engineering department?',
            'Tell me about updates from HR',
            'What is happening in the Marketing team?',
            'Get news for the Finance department',
            'Any announcements from IT?',
        ],
    )

    agent_card = AgentCard(
        name='Intranet News Agent',
        description=(
            'A company intranet agent that provides news and information about '
            'office locations and departments. Can list available offices and departments, '
            'and retrieve location-specific or department-specific news and announcements.'
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
            office_locations_skill,
            office_news_skill,
            departments_skill,
            department_news_skill,
        ],
        examples=[
            'What office locations does the company have?',
            'What is the latest news from the St. Louis office?',
            'List all departments',
            'What is happening at the Berlin office?',
            'Get news for the Engineering department',
            'Tell me about updates from the London office',
            'What departments are in the company?',
            'Any announcements from the HR department?',
        ],
    )
    return agent_card
