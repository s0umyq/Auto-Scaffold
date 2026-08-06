"""
GUI — Local web UI for Auto-Scaffold CLI.
"""

from __future__ import annotations

import contextlib
import logging
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from auto_scaffold.agents.fix_proposer import propose_fixes
from auto_scaffold.agents.language_detector import detect_language
from auto_scaffold.agents.test_generator import generate_tests
from auto_scaffold.skills.approval_gate import ApprovalGate
from auto_scaffold.skills.ast_parser import parse_codebase
from auto_scaffold.skills.test_runner import run_tests

logger = logging.getLogger(__name__)

app = FastAPI(title="Auto-Scaffold CLI GUI")

# Mount static files (CSS, JS, etc.)
# Use robust path resolution that works regardless of working directory
GUI_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=GUI_DIR), name="static")

# WebSocket connection manager
class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict[str, Any]) -> None:
        for conn in self.active_connections:
            with contextlib.suppress(Exception):
                await conn.send_json(message)

manager = ConnectionManager()


# Request/Response models
class ScanRequest(BaseModel):
    folder: str


class GenerateTestsRequest(BaseModel):
    folder: str


class RunTestsRequest(BaseModel):
    folder: str


class ProposeFixesRequest(BaseModel):
    folder: str


class ReviewRequest(BaseModel):
    folder: str
    auto_approve: bool = False


class PipelineRequest(BaseModel):
    folder: str


# Helper to send progress updates
async def send_progress(step: str, message: str, data: dict | None = None) -> None:
    await manager.broadcast({
        "type": "progress",
        "step": step,
        "message": message,
        "data": data or {},
    })


# API Routes
@app.get("/")
async def index() -> HTMLResponse:
    html_file = GUI_DIR / "index.html"
    if html_file.exists():
        return HTMLResponse(html_file.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>GUI not built</h1>")


@app.post("/api/scan")
async def api_scan(req: ScanRequest) -> dict[str, Any]:
    folder = Path(req.folder).resolve()
    if not folder.exists():
        raise HTTPException(404, "Folder not found")

    await send_progress("scan", "Detecting language...")
    lang_result = await detect_language(folder)

    await send_progress("scan", "Parsing AST...")
    summary = parse_codebase(folder)

    return {
        "language": lang_result.primary_language,
        "package_manager": lang_result.package_manager,
        "test_framework": lang_result.test_framework,
        "confidence": lang_result.confidence,
        "files_parsed": len(summary.files),
        "total_functions": sum(len(f.functions) for f in summary.files),
        "total_classes": sum(len(f.classes) for f in summary.files),
    }


@app.post("/api/generate-tests")
async def api_generate_tests(req: GenerateTestsRequest) -> dict[str, Any]:
    folder = Path(req.folder).resolve()
    if not folder.exists():
        raise HTTPException(404, "Folder not found")

    await send_progress("generate", "Detecting language...")
    _ = await detect_language(folder)

    await send_progress("generate", "Parsing codebase...")
    summary = parse_codebase(folder)

    await send_progress("generate", "Generating tests...")
    generated = await generate_tests(folder, summary)

    return {
        "generated_count": len(generated),
        "files": [str(f) for f in generated],
    }


@app.post("/api/run-tests")
async def api_run_tests(req: RunTestsRequest) -> dict[str, Any]:
    folder = Path(req.folder).resolve()
    if not folder.exists():
        raise HTTPException(404, "Folder not found")

    await send_progress("run", "Detecting language...")
    lang_result = await detect_language(folder)

    await send_progress("run", "Running tests...")
    result = run_tests(folder, lang_result.test_framework)

    failures = [r for r in result.results if not r.passed]
    return {
        "exit_code": result.exit_code,
        "total_tests": len(result.results),
        "passed": sum(1 for r in result.results if r.passed),
        "failed": len(failures),
        "failures": [
            {
                "test_id": r.test_id,
                "file": r.file,
                "error_type": r.error_type,
                "message": r.message,
                "traceback": r.traceback,
            }
            for r in failures
        ],
    }


@app.post("/api/propose-fixes")
async def api_propose_fixes(req: ProposeFixesRequest) -> dict[str, Any]:
    folder = Path(req.folder).resolve()
    if not folder.exists():
        raise HTTPException(404, "Folder not found")

    await send_progress("propose", "Running tests to find failures...")
    lang_result = await detect_language(folder)
    result = run_tests(folder, lang_result.test_framework)
    failures = [r for r in result.results if not r.passed]

    if not failures:
        return {"proposals": [], "message": "No failures to fix"}

    await send_progress("propose", "Reading source files...")
    source_files = {}
    for f in folder.rglob("*"):
        if f.is_file() and f.suffix in (".py", ".js", ".ts", ".go", ".rs"):
            try:
                rel = f.relative_to(folder)
                source_files[str(rel)] = f.read_text(encoding="utf-8")
            except Exception:
                pass

    await send_progress("propose", "Generating fix proposals...")
    proposals = await propose_fixes(folder, failures, source_files)

    return {
        "proposals_count": len(proposals),
        "proposals": [
            {
                "id": p.id,
                "target_file": p.target_file,
                "diff": p.diff,
                "test_failures_addressed": p.test_failures_addressed,
                "status": p.status,
            }
            for p in proposals
        ],
    }


@app.post("/api/review")
async def api_review(req: ReviewRequest) -> dict[str, Any]:
    folder = Path(req.folder).resolve()
    if not folder.exists():
        raise HTTPException(404, "Folder not found")

    await send_progress("review", "Running tests...")
    lang_result = await detect_language(folder)
    result = run_tests(folder, lang_result.test_framework)
    failures = [r for r in result.results if not r.passed]

    source_files = {}
    for f in folder.rglob("*"):
        if f.is_file() and f.suffix in (".py", ".js", ".ts", ".go", ".rs"):
            try:
                rel = f.relative_to(folder)
                source_files[str(rel)] = f.read_text(encoding="utf-8")
            except Exception:
                pass

    proposals = await propose_fixes(folder, failures, source_files)

    if not proposals:
        return {"applied": 0, "message": "No proposals to review"}

    await send_progress("review", "Reviewing proposals...")
    gate = ApprovalGate(auto_approve=req.auto_approve)
    reviewed = gate.review(proposals)

    approved = [p for p in reviewed if p.status == "approved"]

    await send_progress("review", "Applying approved fixes...")
    applied = gate.apply_approved(reviewed)
    applied_count = sum(1 for p in applied if p.status == "applied")

    await send_progress("review", "Re-running tests...")
    result2 = run_tests(folder, lang_result.test_framework)

    return {
        "approved": len(approved),
        "applied": applied_count,
        "tests_after": {
            "passed": sum(1 for r in result2.results if r.passed),
            "failed": sum(1 for r in result2.results if not r.passed),
        },
    }


@app.post("/api/pipeline")
async def api_pipeline(req: PipelineRequest) -> dict[str, Any]:
    folder = Path(req.folder).resolve()
    if not folder.exists():
        raise HTTPException(404, "Folder not found")

    await send_progress("pipeline", "Step 1/6: Scanning...", {"step": "scan"})
    lang_result = await detect_language(folder)
    summary = parse_codebase(folder)

    await send_progress("pipeline", "Step 2/6: Generating tests...", {"step": "generate"})
    _ = await generate_tests(folder, summary)

    await send_progress("pipeline", "Step 3/6: Running tests...", {"step": "run"})
    result = run_tests(folder, lang_result.test_framework)
    failures = [r for r in result.results if not r.passed]

    if not failures:
        return {"message": "All tests pass!", "tests_passed": len(result.results)}

    await send_progress("pipeline", "Step 4/6: Proposing fixes...", {"step": "propose"})
    source_files = {}
    for f in folder.rglob("*"):
        if f.is_file() and f.suffix in (".py", ".js", ".ts", ".go", ".rs"):
            try:
                rel = f.relative_to(folder)
                source_files[str(rel)] = f.read_text(encoding="utf-8")
            except Exception:
                pass

    proposals = await propose_fixes(folder, failures, source_files)

    await send_progress("pipeline", "Step 5/6: Awaiting review...", {
        "step": "review",
        "proposals": [
            {
                "id": p.id,
                "target_file": p.target_file,
                "diff": p.diff,
                "test_failures_addressed": p.test_failures_addressed,
            }
            for p in proposals
        ],
    })

    return {
        "proposals_count": len(proposals),
        "proposals": [
            {
                "id": p.id,
                "target_file": p.target_file,
                "diff": p.diff,
                "test_failures_addressed": p.test_failures_addressed,
            }
            for p in proposals
        ],
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            logger.info("WS message: %s", data)
    except WebSocketDisconnect:
        manager.disconnect(websocket)


def run_gui(host: str = "127.0.0.1", port: int = 8080) -> None:
    """Run the GUI server using uvicorn (recommended) or hypercorn."""
    import uvicorn
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    run_gui()
