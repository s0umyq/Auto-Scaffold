"""
CLI Entrypoint — Main command interface for Auto-Scaffold CLI.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import click
from rich.console import Console
from rich.logging import RichHandler

from auto_scaffold.agents.fix_proposer import propose_fixes
from auto_scaffold.agents.language_detector import detect_language
from auto_scaffold.agents.test_generator import generate_tests
from auto_scaffold.skills.approval_gate import ApprovalGate
from auto_scaffold.skills.ast_parser import parse_codebase
from auto_scaffold.skills.test_runner import run_tests

console = Console()


def setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )


@click.group()
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose logging")
@click.pass_context
def cli(ctx: click.Context, verbose: bool) -> None:
    """Auto-Scaffold CLI — AI-powered test generation and fix proposals."""
    setup_logging(verbose)
    ctx.ensure_object(dict)


@cli.command()
@click.argument("folder", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.pass_context
def scan(ctx: click.Context, folder: Path) -> None:
    """Scan a folder: detect language, parse AST."""
    console.print(f"[bold blue]Scanning:[/bold blue] {folder}")

    async def _scan() -> None:
        lang_result = await detect_language(folder)
        console.print(f"Language: [green]{lang_result.primary_language}[/green]")
        console.print(f"Package Manager: [green]{lang_result.package_manager}[/green]")
        console.print(f"Test Framework: [green]{lang_result.test_framework}[/green]")
        console.print(f"Confidence: [green]{lang_result.confidence:.2f}[/green]")

        summary = parse_codebase(folder)
        console.print(f"\nFiles parsed: [green]{len(summary.files)}[/green]")
        total_funcs = sum(len(f.functions) for f in summary.files)
        total_classes = sum(len(f.classes) for f in summary.files)
        console.print(f"Functions: [green]{total_funcs}[/green]")
        console.print(f"Classes: [green]{total_classes}[/green]")

        ctx.obj["summary"] = summary
        ctx.obj["lang_result"] = lang_result

    asyncio.run(_scan())


@cli.command()
@click.argument("folder", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.pass_context
def generate_tests_cmd(ctx: click.Context, folder: Path) -> None:
    """Generate test files for the codebase."""
    console.print(f"[bold blue]Generating tests for:[/bold blue] {folder}")

    async def _generate() -> None:
        lang_result = await detect_language(folder)
        summary = parse_codebase(folder)
        generated = await generate_tests(folder, summary)
        console.print(f"Generated [green]{len(generated)}[/green] test files")
        for f in generated:
            console.print(f"  [green]✓[/green] {f}")

    asyncio.run(_generate())


@cli.command()
@click.argument("folder", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.pass_context
def run_tests_cmd(ctx: click.Context, folder: Path) -> None:
    """Run tests and show failures."""
    console.print(f"[bold blue]Running tests in:[/bold blue] {folder}")

    async def _run() -> None:
        lang_result = await detect_language(folder)
        result = run_tests(folder, lang_result.test_framework)

        console.print(f"Exit code: [green]{result.exit_code}[/green]")
        console.print(f"Tests run: [green]{len(result.results)}[/green]")

        passed = sum(1 for r in result.results if r.passed)
        failed = len(result.results) - passed
        console.print(f"Passed: [green]{passed}[/green]")
        console.print(f"Failed: [red]{failed}[/red]")

        for r in result.results:
            if not r.passed:
                console.print(f"  [red]✗[/red] {r.test_id} in {r.file}")
                if r.message:
                    console.print(f"    {r.message}")

        ctx.obj["failures"] = [r for r in result.results if not r.passed]
        ctx.obj["lang_result"] = lang_result

    asyncio.run(_run())


@cli.command()
@click.argument("folder", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.pass_context
def propose_fixes_cmd(ctx: click.Context, folder: Path) -> None:
    """Generate fix proposals for test failures."""
    console.print(f"[bold blue]Proposing fixes for:[/bold blue] {folder}")

    async def _propose() -> None:
        lang_result = await detect_language(folder)
        result = run_tests(folder, lang_result.test_framework)
        failures = [r for r in result.results if not r.passed]

        if not failures:
            console.print("[green]No failures to fix![/green]")
            return

        source_files = {}
        for f in folder.rglob("*"):
            if f.is_file() and f.suffix in (".py", ".js", ".ts", ".go", ".rs"):
                try:
                    rel = f.relative_to(folder)
                    source_files[str(rel)] = f.read_text(encoding="utf-8")
                except Exception:
                    pass

        proposals = await propose_fixes(folder, failures, source_files)
        console.print(f"Generated [green]{len(proposals)}[/green] fix proposals")
        for p in proposals:
            console.print(f"  [green]✓[/green] {p.id} -> {p.target_file}")

        ctx.obj["proposals"] = proposals

    asyncio.run(_propose())


@cli.command()
@click.argument("folder", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--auto-approve", is_flag=True, help="Auto-approve all proposals")
@click.pass_context
def review(ctx: click.Context, folder: Path, auto_approve: bool) -> None:
    """Review and approve/reject fix proposals."""
    console.print(f"[bold blue]Reviewing proposals in:[/bold blue] {folder}")

    async def _review() -> None:
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
            console.print("[green]No proposals to review![/green]")
            return

        gate = ApprovalGate(auto_approve=auto_approve)
        reviewed = gate.review(proposals)

        approved = [p for p in reviewed if p.status == "approved"]
        console.print(f"Approved: [green]{len(approved)}[/green]")

        if approved:
            applied = gate.apply_approved(reviewed)
            applied_count = sum(1 for p in applied if p.status == "applied")
            console.print(f"Applied: [green]{applied_count}[/green]")

            if applied_count > 0:
                console.print("\n[bold blue]Re-running tests...[/bold blue]")
                result2 = run_tests(folder, lang_result.test_framework)
                passed2 = sum(1 for r in result2.results if r.passed)
                failed2 = len(result2.results) - passed2
                console.print(f"Passed: [green]{passed2}[/green], Failed: [red]{failed2}[/red]")

    asyncio.run(_review())


@cli.command()
@click.argument("folder", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.pass_context
def auto(ctx: click.Context, folder: Path) -> None:
    """Run full pipeline: scan -> generate -> run -> propose -> review."""
    console.print(f"[bold blue]Running full pipeline on:[/bold blue] {folder}")

    async def _auto() -> None:
        console.print("\n[bold]Step 1: Scan[/bold]")
        lang_result = await detect_language(folder)
        console.print(f"Language: {lang_result.primary_language}, Framework: {lang_result.test_framework}")

        summary = parse_codebase(folder)
        console.print(f"Files: {len(summary.files)}")

        console.print("\n[bold]Step 2: Generate Tests[/bold]")
        generated = await generate_tests(folder, summary)
        console.print(f"Generated {len(generated)} test files")

        console.print("\n[bold]Step 3: Run Tests[/bold]")
        result = run_tests(folder, lang_result.test_framework)
        failures = [r for r in result.results if not r.passed]
        console.print(f"Tests: {len(result.results)}, Failed: {len(failures)}")

        if not failures:
            console.print("[green]All tests pass![/green]")
            return

        console.print("\n[bold]Step 4: Propose Fixes[/bold]")
        source_files = {}
        for f in folder.rglob("*"):
            if f.is_file() and f.suffix in (".py", ".js", ".ts", ".go", ".rs"):
                try:
                    rel = f.relative_to(folder)
                    source_files[str(rel)] = f.read_text(encoding="utf-8")
                except Exception:
                    pass

        proposals = await propose_fixes(folder, failures, source_files)
        console.print(f"Proposals: {len(proposals)}")

        console.print("\n[bold]Step 5: Review[/bold]")
        gate = ApprovalGate(auto_approve=False)
        reviewed = gate.review(proposals)
        approved = [p for p in reviewed if p.status == "approved"]

        if approved:
            applied = gate.apply_approved(reviewed)
            applied_count = sum(1 for p in applied if p.status == "applied")
            console.print(f"Applied: {applied_count}")

            console.print("\n[bold]Step 6: Re-run Tests[/bold]")
            result2 = run_tests(folder, lang_result.test_framework)
            passed2 = sum(1 for r in result2.results if r.passed)
            failed2 = len(result2.results) - passed2
            console.print(f"Passed: {passed2}, Failed: {failed2}")

    asyncio.run(_auto())


if __name__ == "__main__":
    cli()