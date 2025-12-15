import logging
import os
from dataclasses import dataclass
from typing import List, Optional

from dotenv import load_dotenv
from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery

load_dotenv()

SEARCH_ENDPOINT = os.getenv("AZURE_AI_SEARCH_ENDPOINT")
SEARCH_KEY = os.getenv("AZURE_AI_SEARCH_KEY")
SEARCH_INDEX_NAME = os.getenv("AZURE_AI_SEARCH_INDEX_NAME", "queries-index")
EMBEDDING_DEPLOYMENT = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME", "text-embedding-3-small")
EMBEDDING_DIMENSIONS = int(os.getenv("AZURE_OPENAI_EMBEDDING_DIMENSIONS", "1536"))
OPENAI_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")
OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
OPENAI_KEY = os.getenv("AZURE_OPENAI_API_KEY")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PolicySearchTool")
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.WARNING)
logging.getLogger("azure.monitor.opentelemetry.exporter.export").setLevel(logging.WARNING)

openai_client: Optional[AzureOpenAI] = None


def get_openai_client() -> AzureOpenAI:
    global openai_client
    if openai_client:
        return openai_client

    credential = DefaultAzureCredential()
    token_provider = get_bearer_token_provider(credential, "https://cognitiveservices.azure.com/.default")

    openai_client = AzureOpenAI(
        azure_deployment=EMBEDDING_DEPLOYMENT,
        api_version=OPENAI_VERSION,
        azure_endpoint=OPENAI_ENDPOINT,
        api_key=OPENAI_KEY,
        azure_ad_token_provider=token_provider if not OPENAI_KEY else None,
    )
    return openai_client


@dataclass
class QueryExample:
    id: str
    content: str
    description: str
    intent: str
    category: Optional[str]
    complexity: Optional[str]
    score: Optional[float] = None


class PolicySearchTool:
    def __init__(self) -> None:
        self.search_client = self._build_search_client()

    def _build_search_client(self) -> Optional[SearchClient]:
        if not SEARCH_ENDPOINT:
            logger.warning("AZURE_AI_SEARCH_ENDPOINT is not configured; policy searches will return no results.")
            return None

        credential = self._build_search_credential()
        try:
            return SearchClient(
                endpoint=SEARCH_ENDPOINT,
                index_name=SEARCH_INDEX_NAME,
                credential=credential,
            )
        except Exception as exc:  # pragma: no cover - best effort
            logger.error("Failed to create Azure Search client: %s", exc)
            return None

    def _build_search_credential(self):
        if SEARCH_KEY:
            from azure.core.credentials import AzureKeyCredential

            return AzureKeyCredential(SEARCH_KEY)
        return DefaultAzureCredential()

    def run(self, query: str, top_k: int = 5, category: Optional[str] = None) -> List[QueryExample]:
        if not self.search_client:
            logger.warning("Search client unavailable; returning empty result set.")
            return []

        try:
            embedding = (
                get_openai_client()
                .embeddings.create(
                    input=query,
                    model=EMBEDDING_DEPLOYMENT,
                    dimensions=EMBEDDING_DIMENSIONS,
                )
                .data[0]
                .embedding
            )

            vector_query = VectorizedQuery(
                vector=embedding,
                k_nearest_neighbors=top_k,
                fields="intent_vector",
            )

            search_kwargs = {
                "search_text": None,
                "vector_queries": [vector_query],
                "select": ["id", "content", "description", "intent", "category", "complexity"],
                "top": top_k,
            }

            if category:
                safe_category = category.replace("'", "''")
                search_kwargs["filter"] = f"category eq '{safe_category}'"

            results = self.search_client.search(**search_kwargs)
            examples: List[QueryExample] = []

            for result in results:
                examples.append(
                    QueryExample(
                        id=result.get("id", ""),
                        content=result.get("content", ""),
                        description=result.get("description", ""),
                        intent=result.get("intent", ""),
                        category=result.get("category"),
                        complexity=result.get("complexity"),
                        score=result.get("@search.score"),
                    )
                )
                logger.info("Found Query Example: %s", examples[-1])

            return examples
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Error searching for queries: %s", exc)
            return []
