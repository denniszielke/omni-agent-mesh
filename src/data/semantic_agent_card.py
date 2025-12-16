from dataclasses import dataclass
from typing import Optional

@dataclass
class AgentRepositoryCard:
    """Represents a query example with metadata."""
    agent_id: str
    url: str
    name: str
    description: str
    skills: str
    examples: str
