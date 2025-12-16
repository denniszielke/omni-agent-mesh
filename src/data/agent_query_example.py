from dataclasses import dataclass
from typing import Optional
from pydantic import BaseModel

class AgentQueryExample(BaseModel):
    """Information about a person."""
    agent_id: str
    query: str
    description: str
    intent: str
    category: Optional[str] = None
    complexity: Optional[str] = None
    score: Optional[float] = None
