from dataclasses import dataclass
from typing import Optional


@dataclass
class QueryExecutionResult:
    """Represents a query execution result with metadata."""

    id: Optional[str] = None
    query: Optional[str] = None
    content: Optional[str] = None
    score: Optional[float] = None
    is_error: bool = False