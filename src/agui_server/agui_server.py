# Copyright (c) Microsoft. All rights reserved.

"""AG-UI server for Workflow with JSON query upload capability."""
import sys
import logging
import os
import json
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from starlette.responses import StreamingResponse

from agent_framework.ag_ui import add_agent_framework_fastapi_endpoint
from agent_framework import ChatAgent
from agent_framework.azure import AzureOpenAIChatClient

# Add the parent directory (src) to the path to enable sibling imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from workflows.kusto_workflow import workflow
from ingestion.search_index_pipeline import SearchIndexMaintainer

load_dotenv()

# Configure logging
log_level = logging.DEBUG if os.getenv("ENABLE_DEBUG_LOGGING") == "1" else logging.INFO
logging.basicConfig(
    level=log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

if os.getenv("ENABLE_DEBUG_LOGGING") == "1":
    logger.info("Debug logging enabled")
    # Enable debug logging for agent framework and fastapi
    logging.getLogger('agent_framework').setLevel(logging.DEBUG)
    logging.getLogger('uvicorn').setLevel(logging.DEBUG)
else:
    # Suppress verbose Azure logs
    logging.getLogger('azure.core.pipeline.policies.http_logging_policy').setLevel(logging.WARNING)
    logging.getLogger('azure.monitor.opentelemetry.exporter.export').setLevel(logging.WARNING)

# Create FastAPI app
app = FastAPI(title="Workflow AG-UI Server")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directory to store uploaded query files
UPLOAD_DIR = Path(__file__).parent / "uploaded_queries"
UPLOAD_DIR.mkdir(exist_ok=True)

# Store for uploaded queries (in-memory, can be replaced with a database)
uploaded_queries: dict[str, list[dict[str, Any]]] = {}

@app.get("/health")
async def health() -> JSONResponse:
    """Basic health check including required environment validation."""
    required_env = [
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_SMALL_CHAT_DEPLOYMENT_NAME",
        "AZURE_OPENAI_BIG_CHAT_DEPLOYMENT_NAME",
    ]
    missing = [name for name in required_env if not os.getenv(name)]
    status = "ok" if not missing else "degraded"
    return JSONResponse({
        "status": status,
        "missing_env": missing,
        "workflow": True,
        "upload_enabled": True,
    })

@app.get("/diagnostics")
async def diagnostics() -> JSONResponse:
    """Return diagnostics useful for debugging prompt send failures."""
    diag: dict[str, Any] = {}
    # Key Azure OpenAI settings
    diag["azure_openai"] = {
        "endpoint": bool(os.getenv("AZURE_OPENAI_ENDPOINT")),
        "small_deployment": os.getenv("AZURE_OPENAI_SMALL_CHAT_DEPLOYMENT_NAME") or "",
        "big_deployment": os.getenv("AZURE_OPENAI_BIG_CHAT_DEPLOYMENT_NAME") or "",
        "version": os.getenv("AZURE_OPENAI_VERSION") or "",
    }

    diag["search"] = {
        "endpoint": bool(os.getenv("AZURE_SEARCH_ENDPOINT")),
        "index_name": os.getenv("AZURE_SEARCH_INDEX_NAME") or "",
    }
    # Uploaded files
    diag["uploaded_files"] = list(uploaded_queries.keys())
    # Runtime
    diag["server"] = {
        "host": os.getenv("AGUI_HOST", "127.0.0.1"),
        "port": os.getenv("AGUI_PORT", "8090"),
    }
    return JSONResponse(diag)


@app.get("/")
async def index():
    """Serve the main HTML page."""
    static_dir = Path(__file__).parent / "static"
    index_file = static_dir / "agui_index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return JSONResponse({"message": "AG-UI Server is running", "endpoints": ["/", "/workflow"   ]})



# Add AG-UI endpoint for the workflow
# Convert workflow to agent using as_agent() method
try:
    logger.info("Converting workflow to agent...")
    workflow_agent = workflow.as_agent()
    logger.info(f"Workflow agent created: {workflow_agent}")
    logger.info("Registering /workflow endpoint with AG UI...")
    add_agent_framework_fastapi_endpoint(
        app=app,
        agent=workflow_agent,
        path="/workflow",
    )
    logger.info("/workflow endpoint registered successfully.")
except Exception as e:
    logger.error(f"Failed to register /workflow endpoint: {e}", exc_info=True)
    # Don't fail the whole server if workflow registration fails
    logger.warning("Server will continue without /workflow endpoint")

# Minimal sanity endpoint: basic chat agent without tools to validate SSE
try:
    simple_chat_client = AzureOpenAIChatClient(
        endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        deployment_name=os.getenv("AZURE_OPENAI_SMALL_CHAT_DEPLOYMENT_NAME"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    )

    simple_agent = ChatAgent(
        name="SanityAgent",
        instructions="You are a helpful assistant. Answer briefly.",
        chat_client=simple_chat_client,
    )

    add_agent_framework_fastapi_endpoint(
        app=app,
        agent=simple_agent,
        path="/workflow_sanity",
    )
except Exception as e:
    logger.warning(f"Sanity endpoint initialization skipped: {e}")

# Safe fallback endpoint: emits SSE error messages instead of closing abruptly
@app.post("/workflow_safe")
async def workflow_safe(request):
    """AG-UI compatible fallback endpoint that always streams SSE and surfaces errors.

    It does not run the full workflow. Instead, it returns a brief message
    acknowledging the request and explains that the main workflow encountered errors.
    """

    try:
        payload = await request.json()
        thread_id = payload.get("thread_id") or f"thread_{os.getpid()}"
        run_id = payload.get("run_id") or f"run_{os.getpid()}"
        messages = payload.get("messages", [])
        user_text = ""
        if messages and isinstance(messages, list):
            last = messages[-1]
            user_text = (last.get("content") or "").strip()
    except Exception:
        thread_id = f"thread_{os.getpid()}"
        run_id = f"run_{os.getpid()}"
        user_text = ""

    async def event_generator():
        # Emit thread id
        yield f"data: {{\"type\": \"THREAD_ID\", \"threadId\": \"{thread_id}\"}}\n\n"
        # Emit run started
        yield f"data: {{\"type\": \"RUN_STARTED\", \"runId\": \"{run_id}\"}}\n\n"
        # Emit an explanatory message
        text = (
            "We received your request"
            + (f": '{user_text}'. " if user_text else ". ")
            + "However, the main workflow encountered an internal error during execution. "
              "Please check diagnostics (/diagnostics) and ensure Search configs are set. "
              "You can use /workflow_sanity for basic chat validation."
        )
        # Stream as TEXT_DELTA chunks for UI rendering
        for chunk in [text]:
            yield f"data: {{\"type\": \"TEXT_DELTA\", \"text\": {json.dumps(chunk)} }}\n\n"
        # Mark completion
        yield "data: {\"type\": \"RUN_COMPLETED\"}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

# Mount static files
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


def main():
    """Run the AG-UI server."""
    port = int(os.getenv("AGUI_PORT", "8090"))
    host = os.getenv("AGUI_HOST", "127.0.0.1")
    
    logger.info(f"\n{'='*60}")
    logger.info("Workflow AG-UI Server")
    logger.info(f"{'='*60}")
    logger.info(f"Server running at: http://{host}:{port}")
    logger.info(f"Workflow endpoint: http://{host}:{port}/workflow")
    logger.info(f"Upload endpoint: http://{host}:{port}/upload")
    logger.info(f"Queries endpoint: http://{host}:{port}/queries")
    logger.info(f"{'='*60}\n")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nProgram interrupted by user. Cleaning up...")
    except Exception as e:
        print(f"An error occurred: {e}")
