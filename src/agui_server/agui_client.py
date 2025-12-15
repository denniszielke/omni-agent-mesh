# Copyright (c) Microsoft. All rights reserved.

"""AG-UI client for Workflow with JSON query upload capability."""

import asyncio
import json
import os
from pathlib import Path
from typing import Optional

import httpx
from agent_framework import TextContent
from agent_framework.ag_ui import AGUIChatClient
from dotenv import load_dotenv

load_dotenv()


async def main():
    """Main client loop for AG-UI Workflow."""
    # Get server URL from environment or use default
    server_url = os.environ.get("AGUI_SERVER_URL", "http://127.0.0.1:8090/")
    workflow_endpoint = f"{server_url.rstrip('/')}/workflow"
    
    print(f"\n{'='*60}")
    print("Workflow AG-UI Client")
    print(f"{'='*60}")
    print(f"Server URL: {server_url}")
    print(f"Workflow endpoint: {workflow_endpoint}")
    print(f"{'='*60}\n")
    
    print("Commands:")
    print("  - Type your query question to chat with the workflow")
    print("  - :upload <file.json> - Upload a JSON file with test queries")
    print("  - :queries - List all uploaded queries")
    print("  - :delete <filename> - Delete uploaded queries")
    print("  - :q or quit - Exit the client\n")
    
    # Create AG-UI client
    async with AGUIChatClient(endpoint=workflow_endpoint) as client:
        thread_id: Optional[str] = None
        
        try:
            while True:
                # Get user input
                message = input("\nUser (:q or quit to exit): ").strip()
                
                if not message:
                    continue
                
                # Check for exit command
                if message.lower() in [':q', 'quit', 'exit']:
                    print("\nExiting...")
                    break
                
                
                # Chat with the workflow
                try:
                    print("\nAgent: ", end="", flush=True)
                    
                    # Stream responses from the agent
                    async for update in client.get_streaming_response(
                        message, thread_id=thread_id
                    ):
                        # Extract thread ID for conversation continuity
                        if hasattr(update, 'thread_id') and update.thread_id:
                            thread_id = update.thread_id
                        
                        # Print text content
                        for content in update.contents:
                            if isinstance(content, TextContent) and content.text:
                                print(content.text, end="", flush=True)
                    
                    print()  # New line after response
                    
                except KeyboardInterrupt:
                    print("\n\nInterrupted by user")
                    break
                except Exception as e:
                    print(f"\n❌ Error: {e}")
                    print("Make sure the server is running and accessible")
        
        except KeyboardInterrupt:
            print("\n\nExiting...")


if __name__ == "__main__":
    asyncio.run(main())
