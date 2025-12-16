import os
import logging

from agent_framework import BaseChatClient
from agent_framework.azure import AzureOpenAIChatClient, AzureAIAgentClient
from azure.ai.projects import AIProjectClient
from azure.core.exceptions import ResourceNotFoundError
from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv

# Configure logging for this sample module
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

load_dotenv()

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
AZURE_OPENAI_EMBEDDING_MODEL = os.getenv("AZURE_OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
AZURE_OPENAI_VERSION = os.getenv("AZURE_OPENAI_VERSION", "2024-02-15")

def create_embedding_client() -> AzureOpenAI:
    """Create a shared Azure OpenAI embedding client."""
    openai_credential = None
    token_provider = None
    api_key = AZURE_OPENAI_API_KEY or None

    if not api_key:
        openai_credential = DefaultAzureCredential()
        token_provider = get_bearer_token_provider(
            openai_credential, "https://cognitiveservices.azure.com/.default"
        )
        return AzureOpenAI(
            azure_deployment=AZURE_OPENAI_EMBEDDING_MODEL,
            api_version=AZURE_OPENAI_VERSION,
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            azure_ad_token_provider=token_provider,
        )
    
    client = AzureOpenAI(
        azure_deployment=AZURE_OPENAI_EMBEDDING_MODEL,
        api_version=AZURE_OPENAI_VERSION,
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=api_key,
    )

    return client

async def setup_azure_ai_observability(enable_sensitive_data: bool | None = None) -> None:
    """Use this method to setup tracing in your Azure AI Project.

    This will take the connection string from the AIProjectClient instance.
    It will override any connection string that is set in the environment variables.
    It will disable any OTLP endpoint that might have been set.
    """

    conn_string = None

    try:
        project_endpoint = os.environ.get("AZURE_AI_PROJECT_ENDPOINT", "").strip()

        if (project_endpoint):
            logger.info("AZURE_AI_PROJECT_ENDPOINT found: %s", project_endpoint)
            print("Using Azure AI Project Endpoint authentication.")
        
            credential = DefaultAzureCredential()

            project_client = AIProjectClient(endpoint=project_endpoint, credential=credential)
            conn_string = project_client.telemetry.get_application_insights_connection_string()

        app_insights_connection_string = os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING", "").strip()

        if not conn_string and app_insights_connection_string:
            logger.info("Using Application Insights connection string from environment variable.")
            conn_string = app_insights_connection_string
        
        logger.info("Fetched Application Insights connection string from Azure AI Project.")
    except ResourceNotFoundError:
        print("No Application Insights connection string found for the Azure AI Project.")
        return
    from agent_framework.observability import setup_observability

    if not conn_string:
        logger.warning("No Application Insights connection string found. Observability will not be set up.")
        return
    setup_observability(applicationinsights_connection_string=conn_string, enable_sensitive_data=enable_sensitive_data)
    logger.info("Observability is set up with Application Insights connection string from Azure AI Project.")

def create_foundry_chat_client(model_name: str, agent_name: str = "") -> BaseChatClient:
    """Create an AzureAIAgentClient for Foundry."""

    project_endpoint = os.environ.get("AZURE_AI_PROJECT_ENDPOINT", "").strip()

    if not project_endpoint:
        logger.error("AZURE_AI_PROJECT_ENDPOINT is missing. Set it in your .env file.")
        raise Exception(
            "AZURE_AI_PROJECT_ENDPOINT is not set. Please set it in your .env file."
        )

    from azure.identity import DefaultAzureCredential
    from azure.ai.projects import AIProjectClient

    # Initialize the client
    project_client = AIProjectClient(
        endpoint=project_endpoint,
        credential=DefaultAzureCredential()
    )

    credential = DefaultAzureCredential()
    return AzureAIAgentClient(
        project_endpoint=project_endpoint,
        credential=credential,
        model_deployment_name=model_name,
        agent_name=agent_name,
        should_cleanup_agent = False
    )

def create_chat_client(model_name: str, agent_name: str = "") -> BaseChatClient:
    """Create an OpenAIChatClient."""

    token: str
    endpoint: str

    if (not model_name) or model_name.strip() == "":
        logger.error("Model name is missing. Set COMPLETION_DEPLOYMENT_NAME in your .env file.")
        raise Exception(
            "Model name for OpenAIChatClient is not set. Please set COMPLETION_DEPLOYMENT_NAME in your .env file."
        )

    project_endpoint = os.environ.get("AZURE_AI_PROJECT_ENDPOINT", "").strip()
    azure_api_key = os.environ.get("AZURE_OPENAI_API_KEY", "").strip()
    azure_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", "").strip()

    if project_endpoint:
        logger.info("AZURE_AI_PROJECT_ENDPOINT found: %s", project_endpoint)
        print("Using Azure AI Project Endpoint authentication.")
        credential = DefaultAzureCredential()
        return AzureAIAgentClient(
            project_endpoint=project_endpoint,
            credential=credential,
            model_deployment_name=model_name,
            agent_name=agent_name,
            should_cleanup_agent = False
        )
    
    if azure_endpoint:
        logger.info("AZURE_OPENAI_ENDPOINT found: %s", azure_endpoint)

        if azure_api_key:
            print("Using Azure OpenAI API key authentication.")
            logger.info("AZURE_OPENAI_API_KEY found - using API key authentication.")
            token = azure_api_key
            endpoint = azure_endpoint
            return AzureOpenAIChatClient(
                deployment_name=model_name,
                azure_api_key=token,
                endpoint=endpoint,
            )   
        
        else:
            print("Using Azure OpenAI AAD authentication.")
            logger.info("AZURE_OPENAI_API_KEY not found - will use AAD authentication.")
            token_provider = get_bearer_token_provider(
                DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
            )
            endpoint = azure_endpoint

            return AzureOpenAIChatClient(
                deployment_name=model_name,
                ad_token_provider=token_provider,
                endpoint=endpoint,
            )   
    