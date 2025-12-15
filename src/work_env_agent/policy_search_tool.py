import os
from openai import AzureOpenAI
from typing import Optional
import logging
from dotenv import load_dotenv
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from azure.search.documents import SearchItemPaged
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from agent_framework import ChatAgent, HostedMCPTool, MCPStreamableHTTPTool
from dataclasses import dataclass
from typing import Optional

@dataclass
class QueryExample:
    """Represents a query example with metadata."""
    id: str
    content: str
    description: str
    intent: str
    category: Optional[str] = None
    complexity: Optional[str] = None
    score: Optional[float] = None

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
logger = logging.getLogger(__name__)

logging.getLogger('azure.core.pipeline.policies.http_logging_policy').setLevel(logging.WARNING)
logging.getLogger('azure.monitor.opentelemetry.exporter.export').setLevel(logging.WARNING)

openai_client = None

def get_openai_client():
    global openai_client
    if openai_client:
        return openai_client

    openai_credential = DefaultAzureCredential()
    token_provider = get_bearer_token_provider(openai_credential, "https://cognitiveservices.azure.com/.default")

    openai_client = AzureOpenAI(
        azure_deployment=EMBEDDING_DEPLOYMENT,
        api_version=OPENAI_VERSION,
        azure_endpoint=OPENAI_ENDPOINT,
        api_key=OPENAI_KEY,
        azure_ad_token_provider=token_provider if not OPENAI_KEY else None
    )
    return openai_client

class PolicySearchTool():
    """Tool that searches for similar queries using Azure AI Search."""

    def __init__(self) -> None:

        if SEARCH_KEY:
            from azure.core.credentials import AzureKeyCredential

            credential = AzureKeyCredential(SEARCH_KEY)
        else:
            credential = DefaultAzureCredential()

        self.search_client = SearchClient(
            endpoint=SEARCH_ENDPOINT,
            index_name=SEARCH_INDEX_NAME,
            credential=credential,
        )

    async def run(self, query: str, top_k: int = 5, category: Optional[str] = None) -> list[QueryExample]:
        """Execute the search and return a list of QueryExample objects."""
        try:

            openai_client = get_openai_client()
            embedding = openai_client.embeddings.create(input=query, model=EMBEDDING_DEPLOYMENT, dimensions=EMBEDDING_DIMENSIONS).data[0].embedding

            vector_query = VectorizedQuery(vector=embedding, k_nearest_neighbors=top_k, fields="intent_vector")
            logger.info(f"Vector Query: {vector_query}")
            results: SearchItemPaged[dict]
            results = self.search_client.search(  
                search_text=None,  
                vector_queries= [vector_query],
                select=["content", "description", "intent", "category", "complexity", "id"],
                top=top_k,
            )  
            logger.info(f"Search Results: {results}")
  

            # logger.info(f"Searching for queries with query: {query}, top_k: {top_k}, category: {category}")
            # search_params = {
            #     "search_text": query,
            #     "top": top_k,
            #     "include_total_count": True,
            #     "select": [
            #         "id",
            #         "query",
            #         "description",
            #         "intent",
            #         "category",
            #         "complexity",
            #     ],
            # }

            # if category:
            #     search_params["filter"] = f"category eq '{category}'"
            
            # results = self.search_client.search(**search_params)

            # semantic_answers = results.get_answers()
            # if semantic_answers:
            #     for answer in semantic_answers:
            #         if answer.highlights:
            #             logger.info(f"Semantic Answer: {answer.highlights}")
            #         else:
            #             logger.info(f"Semantic Answer: {answer.text}")
            #     logger.info(f"Semantic Answer Score: {answer.score}\n")

            # logger.info(f"Search returned {len(results)} results")
            query_examples = []
            for result in results:
                example = QueryExample(
                    id =result.get("id", ""),
                    content=result.get("content", ""),
                    description=result.get("description", ""),
                    intent=result.get("intent", ""),
                    category=result.get("category"),
                    complexity=result.get("complexity"),
                    score=result.get("@search.score"),
                )

                logger.info(f"Found Query Example: {example}")
                query_examples.append(example)

            return query_examples
            
        except Exception as exc:  # pragma: no cover - defensive
            # Return empty list on error, or you could raise the exception
            logger.error(f"Error searching for queries: {exc}")
            return []