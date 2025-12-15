from dataclasses import dataclass
from typing import Optional


@dataclass
class QueryExample:
    """Represents a query example with metadata."""
    id: str
    query: str
    description: str
    intent: str
    category: Optional[str] = None
    complexity: Optional[str] = None
    score: Optional[float] = None
