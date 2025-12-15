# Copyright (c) Microsoft. All rights reserved.

import os
import asyncio
import logging
from collections.abc import AsyncIterable
from typing import Any, Annotated, List, Literal

import httpx
from agent_framework import (
    AgentRunResponse,
    AgentRunResponseUpdate,
    AgentThread,
    BaseAgent,
    ChatMessage,
    Role,
    TextContent,
)
from agent_framework.observability import get_tracer, setup_observability
from agent_framework.openai import OpenAIChatClient
from dotenv import load_dotenv
from openai import AsyncOpenAI
from opentelemetry.trace import SpanKind
from pydantic import Field

"""Hacker News Agent Implementation Example

This sample demonstrates implementing a custom news agent by extending
BaseAgent and delegating Hacker News related questions to an OpenAI model
that can call tools to fetch and summarize top stories.
"""


load_dotenv()

logger = logging.getLogger("news_agent")

if (os.environ.get("GITHUB_TOKEN") is not None):
    token = os.environ["GITHUB_TOKEN"]
    endpoint = "https://models.github.ai/inference"
    print("Using GitHub Token for authentication")
elif (os.environ.get("AZURE_OPENAI_API_KEY") is not None):
    token = os.environ["AZURE_OPENAI_API_KEY"]
    endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
    print("Using Azure OpenAI Token for authentication")

async_openai_client = AsyncOpenAI(
    base_url=endpoint,
    api_key=token
)

completion_model_name = os.environ.get("COMPLETION_DEPLOYMENT_NAME")
medium_model_name = os.environ.get("MEDIUM_DEPLOYMENT_MODEL_NAME")
small_model_name = os.environ.get("SMALL_DEPLOYMENT_MODEL_NAME")

completion_client=OpenAIChatClient(
    model_id = completion_model_name,
    api_key=token,
    async_client = async_openai_client
)

medium_client=OpenAIChatClient(
    model_id = medium_model_name,
    api_key=token,
    async_client = async_openai_client
)

small_client=OpenAIChatClient(
    model_id = small_model_name,
    api_key=token,
    async_client = async_openai_client
)


def get_hackernews_story_ids(
    list_type: Annotated[
        Literal["top", "new", "best"],
        Field(description="Which Hacker News list to fetch: 'top', 'new', or 'best'."),
    ] = "top",
    limit: Annotated[
        int,
        Field(
            description="Maximum number of story IDs to return (1-50).",
            ge=1,
            le=50,
        ),
    ] = 10,
) -> List[int]:
    """Get a list of recent Hacker News story IDs using the Firebase API."""

    base = "https://hacker-news.firebaseio.com/v0"
    path_map = {
        "top": "topstories",
        "new": "newstories",
        "best": "beststories",
    }
    path = path_map[list_type]
    url = f"{base}/{path}.json"

    with httpx.Client(timeout=10) as client:
        response = client.get(url, params={"print": "pretty"})
        response.raise_for_status()
        ids = response.json() or []

    return ids[:limit]


def get_hackernews_story(
    story_id: Annotated[
        int,
        Field(description="The Hacker News story ID to retrieve."),
    ],
) -> dict:
    """Get the full JSON details of a Hacker News story by ID."""

    base = "https://hacker-news.firebaseio.com/v0"
    url = f"{base}/item/{story_id}.json"

    with httpx.Client(timeout=10) as client:
        response = client.get(url, params={"print": "pretty"})
        response.raise_for_status()
        data = response.json() or {}

    return data


class NewsAgent(BaseAgent):
    """A custom agent that can answer news questions via tools.

    The agent delegates response generation to an OpenAI model using
    Hacker News tools for fetching and summarizing top stories.
    """

    def __init__(
        self,
        *,
        name: str | None = None,
        description: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the NewsAgent.

        Args:
            name: The name of the agent.
            description: The description of the agent.
            **kwargs: Additional keyword arguments passed to BaseAgent.
        """
        super().__init__(
            name=name,
            description=description,
            **kwargs,
        )

    async def run(
        self,
        messages: str | ChatMessage | list[str] | list[ChatMessage] | None = None,
        *,
        thread: AgentThread | None = None,
        **kwargs: Any,
    ) -> AgentRunResponse:
        logger.info("NewsAgent.run called", extra={"agent_id": self.id})

        normalized_messages = self._normalize_messages(messages)

        if not normalized_messages:
            user_text = (
                "Hello! You can ask me about the latest top stories "
                "on Hacker News, or news on specific topics."
            )
        else:
            last_message = normalized_messages[-1]
            user_text = last_message.text or "Tell me about the latest Hacker News stories."

        logger.info("NewsAgent handling query", extra={"agent_id": self.id, "user_text": user_text})

        # Set up observability tools
        setup_observability()
        tracer = get_tracer()

        async def get_hn_ids_observed(*args, **kwargs):
            with tracer.start_as_current_span(
                "tool:get_hackernews_story_ids", kind=SpanKind.CLIENT
            ) as span:
                span.set_attribute("tool.name", "get_hackernews_story_ids")
                return get_hackernews_story_ids(*args, **kwargs)

        async def get_hn_story_observed(*args, **kwargs):
            with tracer.start_as_current_span(
                "tool:get_hackernews_story", kind=SpanKind.CLIENT
            ) as span:
                span.set_attribute("tool.name", "get_hackernews_story")
                return get_hackernews_story(*args, **kwargs)

        # Delegate reply generation to the OpenAI client using the HN tools
        response = await small_client.get_response(
            user_text,
            tools=[get_hn_ids_observed, get_hn_story_observed],
        )
        reply_text = str(response)

        logger.info(
            "NewsAgent model response ready",
            extra={"agent_id": self.id, "response_preview": reply_text[:200]},
        )

        response_message = ChatMessage(
            role=Role.ASSISTANT,
            contents=[TextContent(text=reply_text)],
        )

        # Notify the thread of new messages if provided
        if thread is not None:
            await self._notify_thread_of_new_messages(thread, normalized_messages, response_message)

        return AgentRunResponse(messages=[response_message])

    async def run_stream(
        self,
        messages: str | ChatMessage | list[str] | list[ChatMessage] | None = None,
        *,
        thread: AgentThread | None = None,
        **kwargs: Any,
    ) -> AsyncIterable[AgentRunResponseUpdate]:
        logger.info("NewsAgent.run_stream called", extra={"agent_id": self.id})

        normalized_messages = self._normalize_messages(messages)

        if not normalized_messages:
            user_text = (
                "Hello! You can ask me about the latest top stories "
                "on Hacker News, or news on specific topics."
            )
        else:
            last_message = normalized_messages[-1]
            user_text = last_message.text or "Tell me about the latest Hacker News stories."

        # Set up observability tools
        setup_observability()
        tracer = get_tracer()

        async def get_hn_ids_observed(*args, **kwargs):
            with tracer.start_as_current_span(
                "tool:get_hackernews_story_ids", kind=SpanKind.CLIENT
            ) as span:
                span.set_attribute("tool.name", "get_hackernews_story_ids")
                return get_hackernews_story_ids(*args, **kwargs)

        async def get_hn_story_observed(*args, **kwargs):
            with tracer.start_as_current_span(
                "tool:get_hackernews_story", kind=SpanKind.CLIENT
            ) as span:
                span.set_attribute("tool.name", "get_hackernews_story")
                return get_hackernews_story(*args, **kwargs)

        full_text_chunks: list[str] = []

        async for chunk in small_client.get_streaming_response(
            user_text,
            tools=[get_hn_ids_observed, get_hn_story_observed],
        ):
            if chunk.text:
                full_text_chunks.append(chunk.text)
                logger.debug(
                    "NewsAgent streaming chunk",
                    extra={"agent_id": self.id, "chunk_length": len(chunk.text)},
                )
                yield AgentRunResponseUpdate(
                    contents=[TextContent(text=chunk.text)],
                    role=Role.ASSISTANT,
                )

        # Notify the thread of the complete response if provided
        if thread is not None and full_text_chunks:
            complete_response = ChatMessage(
                role=Role.ASSISTANT,
                contents=[TextContent(text="".join(full_text_chunks))],
            )
            logger.info(
                "NewsAgent streaming complete",
                extra={"agent_id": self.id, "total_length": len("".join(full_text_chunks))},
            )
            await self._notify_thread_of_new_messages(thread, normalized_messages, complete_response)


async def main() -> None:
    """Demonstrates how to use the custom NewsAgent for Hacker News."""
    print("=== Hacker News Agent Example ===\n")

    # Create NewsAgent
    print("--- NewsAgent Example ---")
    news_agent = NewsAgent(
        name="NewsBot",
        description=(
            "An agent that can fetch and summarize the latest top "
            "stories from Hacker News using tools."
        ),
    )

    # Test non-streaming
    print(f"Agent Name: {news_agent.name}")
    print(f"Agent ID: {news_agent.id}")
    print(f"Display Name: {news_agent.display_name}")

    query = "Give me a brief summary of the current top 5 Hacker News stories."
    print(f"\nUser: {query}")
    result = await news_agent.run(query)
    print(f"Agent: {result.messages[0].text}")

    # Test streaming
    query2 = "Now, focus on any stories related to AI or machine learning."
    print(f"\nUser: {query2}")
    print("Agent: ", end="", flush=True)
    async for chunk in news_agent.run_stream(query2):
        if chunk.text:
            print(chunk.text, end="", flush=True)
    print()

    # Example with threads
    print("\n--- Using NewsAgent with Thread ---")
    thread = news_agent.get_new_thread()

    # First message
    result1 = await news_agent.run("Give me the top 3 Hacker News stories.", thread=thread)
    print("User: Give me the top 3 Hacker News stories.")
    print(f"Agent: {result1.messages[0].text}")

    # Second message in same thread
    result2 = await news_agent.run("Remind me which story had the highest score.", thread=thread)
    print("User: Remind me which story had the highest score.")
    print(f"Agent: {result2.messages[0].text}")

    # Check conversation history
    if thread.message_store:
        messages = await thread.message_store.list_messages()
        print(f"\nThread contains {len(messages)} messages in history")
    else:
        print("\nThread has no message store configured")


if __name__ == "__main__":
    asyncio.run(main())