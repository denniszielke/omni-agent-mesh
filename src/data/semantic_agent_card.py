from dataclasses import dataclass
from typing import Optional

@dataclass
class AgentRepositoryCard:
    """Represents a query example with metadata."""
    agent_id: str
    is_foundry_agent: bool
    is_a2a_agent: bool
    url: str
    name: str
    description: str
    skills: str
    examples: str
