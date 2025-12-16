from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)


def hello_world_agent_card() -> AgentCard:
    """Define the agent card for the Hello World Foundry agent."""
    greeting_skill = AgentSkill(
        id='greeting_skill',
        name='Greet users with personalized messages',
        description=(
            'The agent can greet users with friendly, personalized welcome messages. '
            'It can adapt greetings based on time of day, user preferences, or context.'
        ),
        tags=['greeting', 'welcome', 'hello', 'introduction'],
        examples=[
            'Say hello to me',
            'Greet me with a friendly message',
            'Welcome me to the system',
            'Give me a warm introduction',
        ],
    )

    introduction_skill = AgentSkill(
        id='introduction_skill',
        name='Introduce itself and explain capabilities',
        description=(
            'The agent can introduce itself, explain what it can do, '
            'and provide information about its purpose and functionality.'
        ),
        tags=['introduction', 'about', 'capabilities', 'help'],
        examples=[
            'Who are you?',
            'What can you do?',
            'Tell me about yourself',
            'How can you help me?',
        ],
    )

    conversation_starter_skill = AgentSkill(
        id='conversation_starter_skill',
        name='Start friendly conversations',
        description=(
            'The agent can initiate and maintain friendly conversations, '
            'ask how users are doing, and provide positive interactions.'
        ),
        tags=['conversation', 'friendly', 'chat', 'interaction'],
        examples=[
            'How are you today?',
            'Start a friendly conversation with me',
            'Chat with me',
            'I want to have a nice conversation',
        ],
    )

    agent_card = AgentCard(
        name='Hello World Foundry Agent',
        description=(
            'A friendly Hello World agent that greets users, introduces itself, '
            'and engages in pleasant conversations. This Foundry-based agent provides '
            'warm welcomes and can start friendly interactions with users.'
        ),
        url='',
        version='1.0.0',
        default_input_modes=['text'],
        default_output_modes=['text'],
        capabilities=AgentCapabilities(
            input_modes=['text'],
            output_modes=['text'],
            streaming=False,
        ),
        skills=[greeting_skill, introduction_skill, conversation_starter_skill],
        examples=[
            'Say hello to me',
            'Who are you?',
            'How are you today?',
            'Welcome me to the system',
        ],
    )
    return agent_card
