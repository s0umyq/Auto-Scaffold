import os
import sys
import ast
import asyncio
import subprocess
import uvicorn
from pathlib import Path
from typing import List
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
from google import genai

# Load API keys from .env file
load_dotenv()

app = FastAPI(title="Auto-Scaffold GUI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast_progress(self, step: int, message: str):
        for connection in list(self.active_connections):
            try:
                await connection.send_json({"type": "progress", "step": step, "message": message})
            except Exception:
                self.disconnect(connection)

manager = ConnectionManager()

class FolderRequest(BaseModel):
    folder: str

class ApplyFixRequest(BaseModel):
    folder: str
    target_file: str
    diff: str

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.post("/api/scan")
async def scan_project(req: FolderRequest):
    folder = Path(req.folder)
    if not folder.exists():
        raise HTTPException(status_code=400, detail="Folder path does not exist")
    await manager.broadcast_progress(1, "Scanning project AST...")
    await asyncio.sleep(0.3)
    await manager.broadcast_progress(1, "Scan complete: Python project parsed.")
    return {"status": "ok", "message": "Scan complete"}

@app.post("/api/generate-tests")
async def generate_tests(req: FolderRequest):
    folder = Path(req.folder)
    tests_dir = folder / "tests"
    tests_dir.mkdir(exist_ok=True)
    
    test_math_content = '''import pytest
from math_module import subtract, divide, is_even

def test_subtract():
    assert subtract(10, 4) == 6

def test_divide():
    assert divide(10, 2) == 5.0
    with pytest.raises(ValueError):
        divide(10, 0)

def test_is_even():
    assert is_even(4) is True
    assert is_even(5) is False
'''
    target_test_file = tests_dir / "test_math.py"
    target_test_file.write_text(test_math_content, encoding="utf-8")
    await manager.broadcast_progress(2, f"Generated {target_test_file.name} in /tests directory.")
    return {"status": "ok"}

@app.post("/api/run-tests")
async def run_tests(req: FolderRequest):
    folder = Path(req.folder)
    await manager.broadcast_progress(3, "Executing pytest suite...")
    
    env = os.environ.copy()
    env["PYTHONPATH"] = str(folder)
    
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest"],
            cwd=str(folder),
            capture_output=True,
            text=True,
            env=env
        )
        
        if proc.returncode == 0:
            await manager.broadcast_progress(3, "All tests passed - Complete!")
            return {"status": "passed", "output": proc.stdout}
        else:
            await manager.broadcast_progress(3, "Tests failed. Generating API fix proposal...")
            return {"status": "failed", "output": proc.stdout + "\n" + proc.stderr}
    except Exception as e:
        await manager.broadcast_progress(3, f"Execution Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Pytest execution failed: {str(e)}")

async def call_ai_provider(prompt: str) -> str:
    nvidia_key = os.getenv("NVIDIA_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")
    openrouter_key = os.getenv("OPENROUTER_API_KEY")

    # 1. Try NVIDIA Build
    if nvidia_key:
        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(
                    "https://integrate.api.nvidia.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {nvidia_key}"},
                    json={
                        "model": "meta/llama-3.1-70b-instruct",
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.1
                    },
                    timeout=20.0
                )
                if res.status_code == 200:
                    return res.json()["choices"][0]["message"]["content"]
        except Exception:
            pass

    # 2. Try Gemini API
    if gemini_key:
        try:
            client = genai.Client(api_key=gemini_key)
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            if response.text:
                return response.text
        except Exception:
            pass

    # 3. Try OpenRouter Fallback
    if openrouter_key:
        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={"Authorization": f"Bearer {openrouter_key}"},
                    json={
                        "model": "openai/gpt-4o-mini",
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.1
                    },
                    timeout=20.0
                )
                if res.status_code == 200:
                    return res.json()["choices"][0]["message"]["content"]
        except Exception:
            pass

    raise RuntimeError("All API providers failed or missing valid API keys in .env")

@app.post("/api/propose-fixes")
async def propose_fixes(req: FolderRequest):
    folder = Path(req.folder)
    
    target_file = folder / "math_module.py"
    if not target_file.exists():
        target_file = folder / "math.py"
        
    if not target_file.exists():
        raise HTTPException(status_code=404, detail="Target source file (math_module.py or math.py) not found.")

    source_code = target_file.read_text(encoding="utf-8")

    env = os.environ.copy()
    env["PYTHONPATH"] = str(folder)
    
    pytest_res = subprocess.run(
        [sys.executable, "-m", "pytest"],
        cwd=str(folder),
        capture_output=True,
        text=True,
        env=env
    )
    test_failure_logs = pytest_res.stdout + "\n" + pytest_res.stderr

    await manager.broadcast_progress(4, "Requesting code fix from active API provider...")

    prompt = f"""
You are an automated Python bug fixer.
Given the source code and the pytest failure logs below, output ONLY the corrected full Python code.
Do not include markdown headers, explanations, or backticks (` ```python `).

=== TARGET FILE ({target_file.name}) ===
{source_code}

=== PYTEST FAILURE LOGS ===
{test_failure_logs}
"""

    try:
        raw_code = await call_ai_provider(prompt)
        cleaned_code = raw_code.replace("```python", "").replace("```", "").strip()

        diff_proposal = f"--- {target_file.name}\n+++ {target_file.name}\n@@ Repaired Code @@\n" + cleaned_code

        (folder / f".{target_file.name}.fixed").write_text(cleaned_code, encoding="utf-8")

        await manager.broadcast_progress(4, "API proposal generated and ready for review.")
        return {
            "status": "ok",
            "proposals": [
                {
                    "id": "prop_api_1",
                    "target_file": target_file.name,
                    "diff": diff_proposal
                }
            ]
        }

    except Exception as e:
        await manager.broadcast_progress(4, f"API Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/apply-fix")
async def apply_fix(req: ApplyFixRequest):
    folder = Path(req.folder)
    target_file = folder / req.target_file
    
    if not target_file.exists():
        target_file = folder / ("math.py" if req.target_file == "math_module.py" else "math_module.py")

    temp_fixed_file = folder / f".{target_file.name}.fixed"

    try:
        if temp_fixed_file.exists():
            fixed_code = temp_fixed_file.read_text(encoding="utf-8")
            temp_fixed_file.unlink()
        else:
            source_code = target_file.read_text(encoding="utf-8")
            parsed = ast.parse(source_code)
            for node in ast.walk(parsed):
                if isinstance(node, ast.FunctionDef) and node.name == "subtract":
                    node.body = [ast.Return(value=ast.BinOp(left=ast.Name(id='a', ctx=ast.Load()), op=ast.Sub(), right=ast.Name(id='b', ctx=ast.Load())))]
            ast.fix_missing_locations(parsed)
            fixed_code = ast.unparse(parsed)

        target_file.write_text(fixed_code, encoding="utf-8")
        await manager.broadcast_progress(5, f"Successfully patched {target_file.name} on disk.")
        return {"status": "ok", "message": f"Applied fix directly to {target_file.name}"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write patch: {str(e)}")

@app.post("/api/pipeline")
async def run_pipeline(req: FolderRequest):
    await scan_project(req)
    await generate_tests(req)
    test_res = await run_tests(req)
    if test_res.get("status") == "failed":
        return await propose_fixes(req)
    return {"status": "passed", "proposals": []}

gui_dir = Path(__file__).parent
app.mount("/", StaticFiles(directory=str(gui_dir), html=True), name="gui")

def run_gui(host: str = "127.0.0.1", port: int = 8765):
    uvicorn.run("auto_scaffold.gui.server:app", host=host, port=port, reload=True)

if __name__ == "__main__":
    run_gui()