import click
import uvicorn
import sys
import os
from starlette.responses import JSONResponse
from starlette.routing import Route
from a2a.server.agent_execution import AgentExecutor
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers.default_request_handler import DefaultRequestHandler
from a2a.server.tasks.inmemory_task_store import InMemoryTaskStore
from a2a.types import GetTaskRequest, GetTaskResponse, SendMessageRequest, SendMessageResponse
from src.intranet_agent.intranet_agent_executor import IntranetAgentExecutor, intranet_agent_card


class A2ARequestHandler(DefaultRequestHandler):
    """A2A Request Handler for the Intranet Agent."""

    def __init__(self, agent_executor: AgentExecutor, task_store: InMemoryTaskStore):
        super().__init__(agent_executor, task_store)

    async def on_get_task(self, request: GetTaskRequest, *args, **kwargs) -> GetTaskResponse:
        return await super().on_get_task(request, *args, **kwargs)

    async def on_message_send(self, request: SendMessageRequest, *args, **kwargs) -> SendMessageResponse:
        return await super().on_message_send(request, *args, **kwargs)


@click.command()
@click.option('--host', 'host', default='0.0.0.0')
@click.option('--port', 'port', default=8082)
def main(host: str, port: int):
    """Start the Intranet A2A agent server."""

    task_store = InMemoryTaskStore()
    request_handler = A2ARequestHandler(
        agent_executor=IntranetAgentExecutor(),
        task_store=task_store,
    )

    if os.environ.get("CONTAINER_APP_NAME") and os.environ.get("CONTAINER_APP_ENV_DNS_SUFFIX"):
        url = f'https://{os.environ["CONTAINER_APP_NAME"]}.{os.environ["CONTAINER_APP_ENV_DNS_SUFFIX"]}'
    else:
        url = f'http://{host}:{port}/'

    server = A2AStarletteApplication(
        agent_card=intranet_agent_card(url=url), 
        http_handler=request_handler
    )

    app = server.build()

    async def healthz(request):
        return JSONResponse({"status": "ok"})

    app.router.routes.append(Route("/_healthz", endpoint=healthz))

    print(f"Starting Intranet A2A Agent Server at {url}")
    print(f"Connecting to MCP server at: {os.getenv('INTRANET_MCP_SERVER_URL', 'http://localhost:8001/mcp')}")
    
    uvicorn.run(app, host=host, port=port)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(e)
        sys.exit(0)