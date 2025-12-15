# Copyright (c) Microsoft. All rights reserved.

"""AG-UI client for Kusto Workflow with JSON query upload capability."""

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


async def upload_query_file(server_url: str, file_path: Path) -> dict:
    """Upload a JSON query file to the server.
    
    Args:
        server_url: Base URL of the AG-UI server
        file_path: Path to the JSON file to upload
        
    Returns:
        Server response as dictionary
    """
    upload_url = f"{server_url.rstrip('/')}/upload"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        with open(file_path, 'rb') as f:
            files = {'file': (file_path.name, f, 'application/json')}
            response = await client.post(upload_url, files=files)
            response.raise_for_status()
            return response.json()


async def get_uploaded_queries(server_url: str) -> dict:
    """Get all uploaded queries from the server.
    
    Args:
        server_url: Base URL of the AG-UI server
        
    Returns:
        Server response as dictionary
    """
    queries_url = f"{server_url.rstrip('/')}/queries"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(queries_url)
        response.raise_for_status()
        return response.json()


async def delete_queries(server_url: str, filename: str) -> dict:
    """Delete uploaded queries from the server.
    
    Args:
        server_url: Base URL of the AG-UI server
        filename: Name of the file to delete
        
    Returns:
        Server response as dictionary
    """
    delete_url = f"{server_url.rstrip('/')}/queries/{filename}"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.delete(delete_url)
        response.raise_for_status()
        return response.json()


async def main():
    """Main client loop for AG-UI Kusto Workflow."""
    # Get server URL from environment or use default
    server_url = os.environ.get("AGUI_SERVER_URL", "http://127.0.0.1:8090/")
    workflow_endpoint = f"{server_url.rstrip('/')}/workflow"
    
    print(f"\n{'='*60}")
    print("Kusto Workflow AG-UI Client")
    print(f"{'='*60}")
    print(f"Server URL: {server_url}")
    print(f"Workflow endpoint: {workflow_endpoint}")
    print(f"{'='*60}\n")
    
    print("Commands:")
    print("  - Type your Kusto query question to chat with the workflow")
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
                
                # Handle upload command
                if message.startswith(':upload '):
                    file_path_str = message[8:].strip()
                    file_path = Path(file_path_str)
                    
                    if not file_path.exists():
                        print(f"❌ Error: File not found: {file_path}")
                        continue
                    
                    if not file_path.suffix == '.json':
                        print("❌ Error: Only JSON files are supported")
                        continue
                    
                    try:
                        print(f"⬆️  Uploading {file_path.name}...")
                        result = await upload_query_file(server_url, file_path)
                        print(f"✅ Upload successful!")
                        print(f"   - Filename: {result['filename']}")
                        print(f"   - Query count: {result['query_count']}")
                        print(f"\nUploaded queries:")
                        for i, query in enumerate(result['queries'][:5], 1):
                            print(f"   {i}. {query.get('description', 'No description')}")
                        if len(result['queries']) > 5:
                            print(f"   ... and {len(result['queries']) - 5} more")
                    except Exception as e:
                        print(f"❌ Error uploading file: {e}")
                    continue
                
                # Handle queries command
                if message == ':queries':
                    try:
                        result = await get_uploaded_queries(server_url)
                        if not result['uploaded_files']:
                            print("No queries uploaded yet")
                        else:
                            print(f"\nUploaded files: {len(result['uploaded_files'])}")
                            for filename in result['uploaded_files']:
                                queries = result['queries'][filename]
                                print(f"\n📄 {filename} ({len(queries)} queries)")
                                for i, query in enumerate(queries[:3], 1):
                                    print(f"   {i}. {query.get('description', 'No description')}")
                                if len(queries) > 3:
                                    print(f"   ... and {len(queries) - 3} more")
                    except Exception as e:
                        print(f"❌ Error getting queries: {e}")
                    continue
                
                # Handle delete command
                if message.startswith(':delete '):
                    filename = message[8:].strip()
                    try:
                        result = await delete_queries(server_url, filename)
                        print(f"✅ {result['message']}")
                    except Exception as e:
                        print(f"❌ Error deleting queries: {e}")
                    continue
                
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
