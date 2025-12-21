"""
DevGodzilla CLI

Click-based command-line interface for DevGodzilla.
Provides commands for managing protocols, steps, and quality assurance.
"""

import click
import json
import sys
from pathlib import Path
from typing import Optional

from devgodzilla.logging import get_logger, init_cli_logging

logger = get_logger(__name__)

# Banner for display
BANNER = r"""
██████╗ ███████╗██╗   ██╗ ██████╗  ██████╗ ██████╗ ███████╗██╗██╗     ██╗      █████╗ 
██╔══██╗██╔════╝██║   ██║██╔════╝ ██╔═══██╗██╔══██╗╚══███╔╝██║██║     ██║     ██╔══██╗
██║  ██║█████╗  ██║   ██║██║  ███╗██║   ██║██║  ██║  ███╔╝ ██║██║     ██║     ███████║
██║  ██║██╔══╝  ╚██╗ ██╔╝██║   ██║██║   ██║██║  ██║ ███╔╝  ██║██║     ██║     ██╔══██║
██████╔╝███████╗ ╚████╔╝ ╚██████╔╝╚██████╔╝██████╔╝███████╗██║███████╗███████╗██║  ██║
╚═════╝ ╚══════╝  ╚═══╝   ╚═════╝  ╚═════╝ ╚═════╝ ╚══════╝╚═╝╚══════╝╚══════╝╚═╝  ╚═╝
"""


def get_service_context(project_id: Optional[int] = None):
    """Create a ServiceContext for CLI operations.
    
    Args:
        project_id: Optional project ID for request-scoped context.
    """
    from devgodzilla.config import load_config
    from devgodzilla.services.base import ServiceContext
    
    config = load_config()
    return ServiceContext(config=config, project_id=project_id)


def get_db():
    """Get database connection."""
    from devgodzilla.db import get_database
    from devgodzilla.config import load_config
    from devgodzilla.services.event_persistence import install_db_event_sink
    
    global _DB, _DB_KEY
    try:
        _DB
    except NameError:  # pragma: no cover
        _DB = None  # type: ignore[assignment]
        _DB_KEY = None  # type: ignore[assignment]

    config = load_config()
    current_key = (
        config.db_url,
        str(config.db_path) if getattr(config, "db_path", None) else None,
        getattr(config, "db_pool_size", 20),
    )

    if _DB is None or _DB_KEY != current_key:
        _DB = get_database(  # type: ignore[assignment]
            db_url=config.db_url,
            db_path=Path(config.db_path) if getattr(config, "db_path", None) else None,
            pool_size=getattr(config, "db_pool_size", 20),
        )
        _DB.init_schema()
        _DB_KEY = current_key  # type: ignore[assignment]

    install_db_event_sink(db_provider=lambda: _DB)  # type: ignore[arg-type]
    return _DB  # type: ignore[return-value]


# =============================================================================
# Main CLI Group
# =============================================================================

@click.group()
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose output")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
@click.pass_context
def cli(ctx, verbose, json_output):
    """DevGodzilla - AI Development Pipeline."""
    ctx.ensure_object(dict)
    ctx.obj["VERBOSE"] = verbose
    ctx.obj["JSON"] = json_output
    
    if verbose:
        init_cli_logging(level="DEBUG")

    # Load configuration and agents
    from devgodzilla.config import load_config
    config = load_config()

    # Ensure engines are available for local CLI execution paths.
    try:
        from devgodzilla.engines.bootstrap import bootstrap_default_engines

        bootstrap_default_engines(replace=False)
    except Exception as e:
        if verbose:
            click.echo(f"Warning: Failed to bootstrap engines: {e}", err=True)
    
    # Load agent configurations if available
    if config.agent_config_path and config.agent_config_path.exists():
        try:
            from devgodzilla.services.agent_config import AgentConfigService
            from devgodzilla.services.base import ServiceContext
            agent_config = AgentConfigService(ServiceContext(config=config), str(config.agent_config_path))
            agent_config.load_config()
        except Exception as e:
            if verbose:
                click.echo(f"Warning: Failed to load agent config: {e}", err=True)

from devgodzilla.cli.projects import project
from devgodzilla.cli.agents import agent
from devgodzilla.cli.speckit import spec_cli
from devgodzilla.cli.clarifications import clarification_cli

cli.add_command(project)
cli.add_command(agent)
cli.add_command(spec_cli)
cli.add_command(clarification_cli)


@cli.command()
def version():
    """Show version information."""
    click.echo("DevGodzilla v0.1.0")


@cli.command()
def banner():
    """Show the DevGodzilla banner."""
    click.echo(BANNER)


# =============================================================================
# Protocol Commands
# =============================================================================

@cli.group()
def protocol():
    """Protocol management commands."""
    pass


@protocol.command('create')
@click.argument('project_id', type=int)
@click.argument('name')
@click.option('--description', '-d', help='Protocol description')
@click.option('--branch', '-b', help='Base branch')
@click.pass_context
def protocol_create(ctx, project_id, name, description, branch):
    """Create a new protocol run."""
    try:
        context = get_service_context()
        db = get_db()
        
        from devgodzilla.services.orchestrator import OrchestratorService
        
        orchestrator = OrchestratorService(context=context, db=db)
        result = orchestrator.create_protocol_run(
            project_id=project_id,
            protocol_name=name,
            base_branch=branch,
            description=description,
        )
        
        if ctx.obj and ctx.obj.get("JSON"):
            click.echo(json.dumps({
                'success': True,
                'protocol_run_id': result.id if hasattr(result, 'id') else None,
                'message': 'Protocol created',
            }))
        else:
            click.echo(f"✓ Created protocol run: {name}")
            if hasattr(result, 'id'):
                click.echo(f"  ID: {result.id}")
                
    except Exception as e:
        logger.exception("Failed to create protocol")
        click.echo(f"✗ Error: {e}", err=True)
        sys.exit(1)


@protocol.command('start')
@click.argument('protocol_id', type=int)
@click.pass_context
def protocol_start(ctx, protocol_id):
    """Start a protocol run."""
    try:
        context = get_service_context()
        db = get_db()
        
        from devgodzilla.services.orchestrator import OrchestratorService
        
        orchestrator = OrchestratorService(context=context, db=db)
        result = orchestrator.start_protocol_run(protocol_id)
        
        if ctx.obj and ctx.obj.get("JSON"):
            click.echo(json.dumps({
                'success': result.success,
                'job_id': result.job_id,
                'message': result.message,
            }))
        else:
            if result.success:
                click.echo(f"✓ Started protocol {protocol_id}")
                if result.job_id:
                    click.echo(f"  Job ID: {result.job_id}")
            else:
                click.echo(f"✗ Failed: {result.error or result.message}", err=True)
                sys.exit(1)
                
    except Exception as e:
        logger.exception("Failed to start protocol")
        click.echo(f"✗ Error: {e}", err=True)
        sys.exit(1)


@protocol.command('status')
@click.argument('protocol_id', type=int)
@click.pass_context
def protocol_status(ctx, protocol_id):
    """Get protocol status."""
    try:
        db = get_db()
        run = db.get_protocol_run(protocol_id)
        
        if not run:
            click.echo(f"✗ Protocol {protocol_id} not found", err=True)
            sys.exit(1)
        
        if ctx.obj and ctx.obj.get("JSON"):
            click.echo(json.dumps({
                'id': run.id,
                'name': run.protocol_name,
                'status': run.status,
                'created_at': str(run.created_at) if hasattr(run, 'created_at') else None,
            }))
        else:
            click.echo(f"Protocol: {run.protocol_name}")
            click.echo(f"  Status: {run.status}")
            click.echo(f"  ID: {run.id}")
            
    except Exception as e:
        logger.exception("Failed to get protocol status")
        click.echo(f"✗ Error: {e}", err=True)
        sys.exit(1)


@protocol.command('cancel')
@click.argument('protocol_id', type=int)
@click.option('--force', '-f', is_flag=True, help='Force cancellation')
@click.pass_context
def protocol_cancel(ctx, protocol_id, force):
    """Cancel a running protocol."""
    try:
        context = get_service_context()
        db = get_db()
        
        from devgodzilla.services.orchestrator import OrchestratorService
        
        orchestrator = OrchestratorService(context=context, db=db)
        result = orchestrator.cancel_protocol(protocol_id)
        
        if ctx.obj and ctx.obj.get("JSON"):
            click.echo(json.dumps({
                'success': result.success,
                'message': result.message,
            }))
        else:
            if result.success:
                click.echo(f"✓ Cancelled protocol {protocol_id}")
            else:
                click.echo(f"✗ Failed: {result.error or result.message}", err=True)
                sys.exit(1)
                
    except Exception as e:
        logger.exception("Failed to cancel protocol")
        click.echo(f"✗ Error: {e}", err=True)
        sys.exit(1)


@protocol.command('list')
@click.option('--project', '-p', type=int, help='Filter by project ID')
@click.option('--status', '-s', help='Filter by status')
@click.option('--limit', '-n', type=int, default=20, help='Max results')
@click.pass_context
def protocol_list(ctx, project, status, limit):
    """List protocol runs."""
    try:
        db = get_db()
        runs = db.list_protocol_runs(
            project_id=project,
            status=status,
            limit=limit,
        ) if hasattr(db, 'list_protocol_runs') else []
        
        if ctx.obj and ctx.obj.get("JSON"):
            click.echo(json.dumps([
                {'id': r.id, 'name': r.protocol_name, 'status': r.status}
                for r in runs
            ]))
        else:
            if not runs:
                click.echo("No protocols found")
            else:
                for r in runs:
                    status_icon = "●" if r.status == "running" else "○"
                    click.echo(f"  {status_icon} [{r.id}] {r.protocol_name} ({r.status})")
                    
    except Exception as e:
        logger.exception("Failed to list protocols")
        click.echo(f"✗ Error: {e}", err=True)
        sys.exit(1)


@protocol.command("worktree")
@click.argument("protocol_id", type=int)
@click.pass_context
def protocol_worktree(ctx, protocol_id: int) -> None:
    """Ensure a git worktree exists for a protocol and store it on the run."""
    try:
        context = get_service_context()
        db = get_db()

        from devgodzilla.services.git import GitService

        run = db.get_protocol_run(protocol_id)
        project = db.get_project(run.project_id)

        if not project.local_path:
            raise RuntimeError("Project has no local_path; set it before creating a worktree.")

        repo_root = Path(project.local_path).expanduser()
        git = GitService(context)
        worktree = git.ensure_worktree(
            repo_root,
            run.protocol_name,
            run.base_branch,
            protocol_run_id=run.id,
            project_id=project.id,
        )
        worktree_path, branch_name = git.get_worktree_path(repo_root, run.protocol_name)

        db.update_protocol_paths(run.id, worktree_path=str(worktree))

        payload = {
            "success": True,
            "protocol_run_id": run.id,
            "repo_root": str(repo_root),
            "worktree_path": str(worktree_path),
            "branch": branch_name,
        }
        if ctx.obj and ctx.obj.get("JSON"):
            click.echo(json.dumps(payload))
        else:
            click.echo("✓ Worktree ready")
            click.echo(f"  Repo: {repo_root}")
            click.echo(f"  Worktree: {worktree_path}")
            click.echo(f"  Branch: {branch_name}")
    except Exception as e:
        logger.exception("Failed to ensure protocol worktree")
        click.echo(f"✗ Error: {e}", err=True)
        sys.exit(1)


def _slugify_step_name(raw: str) -> str:
    import re

    value = re.sub(r"[^a-zA-Z0-9]+", "-", raw.strip().lower()).strip("-")
    return value or "step"


@protocol.command("scaffold")
@click.argument("protocol_id", type=int)
@click.option("--step", "steps", multiple=True, help="Step name (repeatable)")
@click.option("--overwrite", is_flag=True, help="Overwrite existing step files")
@click.pass_context
def protocol_scaffold(ctx, protocol_id: int, steps: tuple[str, ...], overwrite: bool) -> None:
    """Create `.protocols/<protocol_name>/step-*.md` files for a protocol."""
    try:
        db = get_db()
        run = db.get_protocol_run(protocol_id)
        project = db.get_project(run.project_id)

        workspace = Path(run.worktree_path or project.local_path or ".").expanduser()
        protocol_root = workspace / ".protocols" / run.protocol_name
        protocol_root.mkdir(parents=True, exist_ok=True)

        if not steps:
            steps = ("setup", "implement", "tests")

        created: list[str] = []
        for i, name in enumerate(steps, start=1):
            slug = _slugify_step_name(name)
            path = protocol_root / f"step-{i:02d}-{slug}.md"
            if path.exists() and not overwrite:
                continue
            path.write_text(
                f"# {name}\n\n"
                f"- Protocol: `{run.protocol_name}`\n"
                f"- Step: `{path.stem}`\n"
                f"- Agent: `opencode`\n",
                encoding="utf-8",
            )
            created.append(str(path))

        plan_path = protocol_root / "plan.md"
        if overwrite or not plan_path.exists():
            plan_path.write_text(
                f"# Plan: {run.protocol_name}\n\n"
                f"## Description\n{run.description or '(none)'}\n\n"
                f"## Steps\n"
                + "\n".join([f"- {i+1}. {s}" for i, s in enumerate(steps)]),
                encoding="utf-8",
            )

        db.update_protocol_paths(run.id, protocol_root=str(protocol_root))

        payload = {"success": True, "protocol_root": str(protocol_root), "created": created}
        if ctx.obj and ctx.obj.get("JSON"):
            click.echo(json.dumps(payload))
        else:
            click.echo("✓ Protocol files created")
            click.echo(f"  Root: {protocol_root}")
            for p in created:
                click.echo(f"  - {p}")
    except Exception as e:
        logger.exception("Failed to scaffold protocol files")
        click.echo(f"✗ Error: {e}", err=True)
        sys.exit(1)


@protocol.command("plan")
@click.argument("protocol_id", type=int)
@click.pass_context
def protocol_plan(ctx, protocol_id: int) -> None:
    """Plan a protocol locally (creates step runs from protocol files)."""
    try:
        context = get_service_context()
        db = get_db()

        from devgodzilla.services.git import GitService
        from devgodzilla.services.planning import PlanningService

        planning = PlanningService(context, db, git_service=GitService(context))
        result = planning.plan_protocol(protocol_id)

        payload = {
            "success": result.success,
            "protocol_run_id": protocol_id,
            "steps_created": result.steps_created,
            "spec_hash": result.spec_hash,
            "policy_hash": result.policy_hash,
            "warnings": result.warnings,
            "error": result.error,
        }
        if ctx.obj and ctx.obj.get("JSON"):
            click.echo(json.dumps(payload))
        else:
            if result.success:
                click.echo(f"✓ Planned protocol {protocol_id} ({result.steps_created} steps)")
            else:
                click.echo(f"✗ Failed: {result.error}", err=True)
                sys.exit(1)
    except Exception as e:
        logger.exception("Failed to plan protocol")
        click.echo(f"✗ Error: {e}", err=True)
        sys.exit(1)


@protocol.command("generate")
@click.argument("protocol_id", type=int)
@click.option("--steps", "step_count", type=int, default=3, help="Number of step-*.md files to generate")
@click.option(
    "--prompt",
    "prompt_path",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Prompt file to use (default: prompts/devgodzilla-protocol-generate.prompt.md in this repo)",
)
@click.option("--engine", "engine_id", default="opencode", help="Engine ID to use (default: opencode)")
@click.option("--model", default=None, help="Model to use (default: engine default)")
@click.option("--timeout-seconds", type=int, default=900, help="Agent timeout in seconds")
@click.pass_context
def protocol_generate(
    ctx,
    protocol_id: int,
    step_count: int,
    prompt_path: Optional[str],
    engine_id: str,
    model: Optional[str],
    timeout_seconds: int,
) -> None:
    """Generate `.protocols/<protocol>/` artifacts via an AI agent (no manual scaffolding)."""
    try:
        context = get_service_context()
        db = get_db()

        from devgodzilla.services.git import GitService
        from devgodzilla.services.protocol_generation import ProtocolGenerationService

        run = db.get_protocol_run(protocol_id)
        project = db.get_project(run.project_id)

        if not project.local_path:
            raise RuntimeError("Project has no local_path; set it before generating protocol artifacts.")

        repo_root = Path(project.local_path).expanduser()
        git = GitService(context)

        # Ensure worktree for isolation.
        if run.worktree_path:
            worktree_root = Path(run.worktree_path).expanduser()
        else:
            worktree_root = git.ensure_worktree(
                repo_root,
                run.protocol_name,
                run.base_branch,
                protocol_run_id=run.id,
                project_id=project.id,
            )
            db.update_protocol_paths(run.id, worktree_path=str(worktree_root))

        svc = ProtocolGenerationService(context)
        result = svc.generate(
            worktree_root=worktree_root,
            protocol_name=run.protocol_name,
            description=run.description or "",
            step_count=step_count,
            engine_id=engine_id,
            model=model,
            prompt_path=Path(prompt_path) if prompt_path else None,
            timeout_seconds=timeout_seconds,
            strict_outputs=True,
        )

        # Persist protocol_root so `protocol plan` can pick it up deterministically.
        db.update_protocol_paths(run.id, protocol_root=str(result.protocol_root))

        payload = {
            "success": result.success,
            "protocol_run_id": protocol_id,
            "engine_id": result.engine_id,
            "model": result.model,
            "worktree_root": str(result.worktree_root),
            "protocol_root": str(result.protocol_root),
            "prompt_path": str(result.prompt_path),
            "created_files": [str(p) for p in result.created_files],
            "error": result.error,
        }

        if ctx.obj and ctx.obj.get("JSON"):
            click.echo(json.dumps(payload))
        else:
            if result.success:
                click.echo("✓ Protocol artifacts generated")
                click.echo(f"  Worktree: {result.worktree_root}")
                click.echo(f"  Protocol: {result.protocol_root}")
            else:
                click.echo(f"✗ Failed: {result.error}", err=True)
                sys.exit(1)
    except Exception as e:
        logger.exception("Failed to generate protocol artifacts")
        click.echo(f"✗ Error: {e}", err=True)
        sys.exit(1)


# =============================================================================
# Step Commands
# =============================================================================

@cli.group()
def step():
    """Step management commands."""
    pass


@step.command('run')
@click.argument('step_id', type=int)
@click.pass_context
def step_run(ctx, step_id):
    """Execute a step."""
    try:
        context = get_service_context()
        db = get_db()
        
        from devgodzilla.services.orchestrator import OrchestratorService
        
        orchestrator = OrchestratorService(context=context, db=db)
        result = orchestrator.run_step(step_id)
        
        if ctx.obj and ctx.obj.get("JSON"):
            click.echo(json.dumps({
                'success': result.success,
                'job_id': result.job_id,
                'message': result.message,
            }))
        else:
            if result.success:
                click.echo(f"✓ Started step {step_id}")
                if result.job_id:
                    click.echo(f"  Job ID: {result.job_id}")
            else:
                click.echo(f"✗ Failed: {result.error or result.message}", err=True)
                sys.exit(1)
                
    except Exception as e:
        logger.exception("Failed to run step")
        click.echo(f"✗ Error: {e}", err=True)
        sys.exit(1)


@step.command("execute")
@click.argument("step_id", type=int)
@click.option("--engine", "engine_id", default=None, help="Engine ID to use (default: config)")
@click.option("--model", default=None, help="Model to use (default: engine default)")
@click.pass_context
def step_execute(ctx, step_id: int, engine_id: Optional[str], model: Optional[str]) -> None:
    """Execute a step locally via ExecutionService (no Windmill required)."""
    try:
        context = get_service_context()
        db = get_db()

        from devgodzilla.services.execution import ExecutionService
        from devgodzilla.services.git import GitService

        service = ExecutionService(context, db, git_service=GitService(context))
        result = service.execute_step(step_id, engine_id=engine_id, model=model)
        step_row = db.get_step_run(step_id)

        payload = {
            "success": result.success,
            "step_run_id": step_id,
            "engine_id": result.engine_id,
            "model": result.model,
            "status": step_row.status,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "error": result.error,
        }

        if ctx.obj and ctx.obj.get("JSON"):
            click.echo(json.dumps(payload))
        else:
            if result.success:
                click.echo(f"✓ Executed step {step_id} via {result.engine_id}")
            else:
                click.echo(f"✗ Failed: {result.error}", err=True)
                sys.exit(1)
    except Exception as e:
        logger.exception("Failed to execute step")
        click.echo(f"✗ Error: {e}", err=True)
        sys.exit(1)


@step.command('qa')
@click.argument('step_id', type=int)
@click.option('--gates', '-g', multiple=True, help='Specific gates to run')
@click.pass_context
def step_qa(ctx, step_id, gates):
    """Run QA on a step."""
    try:
        context = get_service_context()
        db = get_db()
        
        from devgodzilla.services.quality import QualityService
        
        quality = QualityService(context=context, db=db)
        result = quality.run_qa(step_run_id=step_id)
        
        if ctx.obj and ctx.obj.get("JSON"):
            click.echo(json.dumps({
                'step_run_id': result.step_run_id,
                'verdict': result.verdict.value if hasattr(result.verdict, 'value') else str(result.verdict),
                'gate_results': [
                    {'gate_id': g.gate_id, 'verdict': g.verdict.value}
                    for g in result.gate_results
                ],
            }))
        else:
            verdict_icon = "✓" if result.passed else "✗"
            click.echo(f"{verdict_icon} QA Verdict: {result.verdict}")
            
            for g in result.gate_results:
                gate_icon = "✓" if g.passed else "✗"
                click.echo(f"  {gate_icon} {g.gate_name}: {g.verdict}")
                for f in g.findings:
                    click.echo(f"      - {f.message}")
                    
    except Exception as e:
        logger.exception("Failed to run QA")
        click.echo(f"✗ Error: {e}", err=True)
        sys.exit(1)


@step.command('status')
@click.argument('step_id', type=int)
@click.pass_context
def step_status(ctx, step_id):
    """Get step status."""
    try:
        db = get_db()
        step = db.get_step_run(step_id)
        
        if not step:
            click.echo(f"✗ Step {step_id} not found", err=True)
            sys.exit(1)
        
        if ctx.obj and ctx.obj.get("JSON"):
            click.echo(json.dumps({
                'id': step.id,
                'name': step.step_name,
                'status': step.status,
            }))
        else:
            click.echo(f"Step: {step.step_name}")
            click.echo(f"  Status: {step.status}")
            click.echo(f"  ID: {step.id}")
            
    except Exception as e:
        logger.exception("Failed to get step status")
        click.echo(f"✗ Error: {e}", err=True)
        sys.exit(1)


@step.command('retry')
@click.argument('step_id', type=int)
@click.pass_context
def step_retry(ctx, step_id):
    """Retry a failed or blocked step."""
    try:
        context = get_service_context()
        db = get_db()
        
        from devgodzilla.services.orchestrator import OrchestratorService
        
        orchestrator = OrchestratorService(context=context, db=db)
        result = orchestrator.retry_step(step_id)
        
        if ctx.obj and ctx.obj.get("JSON"):
            click.echo(json.dumps({
                'success': result.success,
                'message': result.message,
            }))
        else:
            if result.success:
                click.echo(f"✓ Retrying step {step_id}")
            else:
                click.echo(f"✗ Failed: {result.error or result.message}", err=True)
                sys.exit(1)
                
    except Exception as e:
        logger.exception("Failed to retry step")
        click.echo(f"✗ Error: {e}", err=True)
        sys.exit(1)


# =============================================================================
# QA Commands
# =============================================================================

@cli.group()
def qa():
    """Quality assurance commands."""
    pass


@qa.command('evaluate')
@click.argument('workspace', type=click.Path(exists=True))
@click.argument('step_name')
@click.option('--gates', '-g', multiple=True, help='Specific gates to run')
@click.pass_context
def qa_evaluate(ctx, workspace, step_name, gates):
    """Evaluate QA gates standalone (without database)."""
    try:
        context = get_service_context()
        
        from devgodzilla.services.quality import QualityService
        from devgodzilla.qa.gates.common import TestGate, LintGate, TypeGate
        
        # Create service without DB for standalone evaluation
        quality = QualityService(
            context=context,
            db=None,
            default_gates=[TestGate(), LintGate(), TypeGate()],
        )
        
        result = quality.evaluate_step(
            workspace_root=Path(workspace),
            step_name=step_name,
        )
        
        if ctx.obj and ctx.obj.get("JSON"):
            click.echo(json.dumps({
                'verdict': str(result.verdict),
                'duration_seconds': result.duration_seconds,
                'gate_results': [
                    {
                        'gate_id': g.gate_id,
                        'gate_name': g.gate_name,
                        'verdict': str(g.verdict),
                        'findings_count': len(g.findings),
                    }
                    for g in result.gate_results
                ],
            }))
        else:
            verdict_icon = "✓" if result.passed else "✗"
            click.echo(f"{verdict_icon} QA Verdict: {result.verdict}")
            
            if result.duration_seconds:
                click.echo(f"  Duration: {result.duration_seconds:.2f}s")
            
            click.echo("\nGate Results:")
            for g in result.gate_results:
                gate_icon = "✓" if g.passed else ("⚠" if g.verdict.value == "warn" else "✗")
                click.echo(f"  {gate_icon} {g.gate_name}: {g.verdict.value}")
                for f in g.findings[:5]:  # Limit findings shown
                    loc = f"{f.file_path}:{f.line_number}" if f.file_path else ""
                    click.echo(f"      [{f.severity}] {f.message} {loc}")
                if len(g.findings) > 5:
                    click.echo(f"      ... and {len(g.findings) - 5} more findings")
                    
    except Exception as e:
        logger.exception("Failed to evaluate QA")
        click.echo(f"✗ Error: {e}", err=True)
        sys.exit(1)


@qa.command('gates')
@click.pass_context
def qa_gates(ctx):
    """List available QA gates."""
    gates_info = [
        {'id': 'test', 'name': 'Test Gate', 'description': 'Runs pytest tests'},
        {'id': 'lint', 'name': 'Lint Gate', 'description': 'Runs ruff linter'},
        {'id': 'type', 'name': 'Type Gate', 'description': 'Runs mypy type checker'},
        {'id': 'checklist', 'name': 'Checklist Gate', 'description': 'Validates required files'},
        {'id': 'constitutional', 'name': 'Constitutional Gate', 'description': 'Checks constitution compliance'},
    ]
    
    if ctx.obj and ctx.obj.get("JSON"):
        click.echo(json.dumps(gates_info))
    else:
        click.echo("Available QA Gates:\n")
        for g in gates_info:
            click.echo(f"  {g['id']:15} - {g['name']}")
            click.echo(f"                    {g['description']}")


# =============================================================================
# Entry Point
# =============================================================================

def main():
    """CLI entry point."""
    cli(obj={})


if __name__ == '__main__':
    main()
