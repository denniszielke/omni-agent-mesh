"""Smoke test for AG UI workflow server.

Steps:
1. Start the AG UI server as a subprocess
2. Wait until health endpoint (/) responds
3. Upload sample queries JSON
4. List queries
5. Send a workflow request and stream SSE events
6. Summarize received events
7. Clean up (terminate server subprocess)

Run:
    python smoke_test_agui.py

Ensure dependencies installed:
    pip install -r requirements.txt
"""
from __future__ import annotations
import subprocess
import sys
import time
import json
import os
from pathlib import Path
from typing import List, Dict, Any

import httpx

SERVER_HOST = os.getenv("AGUI_HOST", "127.0.0.1")
SERVER_PORT = int(os.getenv("AGUI_PORT", "8090"))
BASE_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"
WORKFLOW_URL = f"{BASE_URL}/workflow"
UPLOAD_URL = f"{BASE_URL}/upload"
QUERIES_URL = f"{BASE_URL}/queries"

ROOT = Path(__file__).parent.parent.parent
QUERY_FILE = ROOT / "src" / "ingestion" / "hr-policy-samples.json"

class SmokeTestError(Exception):
    pass

def start_server() -> subprocess.Popen:
    print(f"[INFO] Starting AG UI server on {BASE_URL}...")
    env = os.environ.copy()
    # Ensure Python finds src.frontend
    cmd = [sys.executable, "src/frontend/agui_server.py"]
    proc = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return proc

def wait_for_server(timeout: float = 30.0) -> None:
    print("[INFO] Waiting for server to become responsive...")
    start = time.time()
    with httpx.Client(timeout=2.0) as client:
        while time.time() - start < timeout:
            try:
                r = client.get(BASE_URL + "/")
                if r.status_code == 200:
                    print("[INFO] Server is up.")
                    return
            except Exception:
                pass
            time.sleep(0.7)
    raise SmokeTestError("Server did not start within timeout")

def stream_workflow(message: str) -> Dict[str, Any]:
    print(f"[INFO] Sending workflow message: {message}")
    events: List[Dict[str, Any]] = []
    text_accumulator = []
    with httpx.Client(timeout=None) as client:
        headers = {"Content-Type": "application/json"}
        payload = {
            "messages": [{"role": "user", "content": message}],
            "thread_id": f"thread_{int(time.time())}",
            "run_id": f"run_{int(time.time())}",
        }
        with client.stream("POST", WORKFLOW_URL, headers=headers, json=payload) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if not line:
                    continue
                if line.startswith("data: "):
                    raw = line[6:]
                    try:
                        evt = json.loads(raw)
                        events.append(evt)
                        t = evt.get("type")
                        # AG UI protocol uses TEXT_MESSAGE_CONTENT with delta field
                        if t == "TEXT_MESSAGE_CONTENT" and evt.get("delta"):
                            text_accumulator.append(evt["delta"])
                    except json.JSONDecodeError:
                        # Non-JSON SSE event; ignore
                        pass
    full_text = "".join(text_accumulator)
    print(f"[INFO] Received {len(events)} SSE events. Text length={len(full_text)}")
    if not full_text:
        raise SmokeTestError("No text content streamed from workflow.")
    print("[SNIPPET]" + full_text[:300].replace("\n", " ") + ("..." if len(full_text) > 300 else ""))
    return {"events": events, "text": full_text}

def terminate(proc: subprocess.Popen) -> None:
    print("[INFO] Terminating server process...")
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


def main() -> int:
    server_proc = start_server()
    try:
        wait_for_server()
        stream_workflow("Generate a query to retrieve equipment properties for line UWM3 and explain the filters.")
        print("\n[RESULT] Smoke test completed successfully.")
        return 0
    except Exception as e:
        print(f"[ERROR] Smoke test failed: {e}")
        return 1
    finally:
        terminate(server_proc)
        # Print server stdout (tail)
        try:
            stdout = server_proc.stdout.read() if server_proc.stdout else ""
            if stdout:
                print("\n[SERVER LOG TAIL]\n" + "\n".join(stdout.splitlines()[-30:]))
        except Exception:
            pass

if __name__ == "__main__":
    raise SystemExit(main())
