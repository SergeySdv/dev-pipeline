import click
from rich.console import Console
from rich.table import Table

from devgodzilla.engines.registry import get_registry

console = Console()

@click.group()
def agent():
    """Agent management commands."""
    pass

@agent.command("list")
def list_agents():
    """List available agents."""
    registry = get_registry()
    agents = registry.list_metadata()
    
    table = Table(title="Available Agents")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="magenta")
    table.add_column("Kind", style="green")
    
    if not agents:
        console.print("[yellow]No agents registered[/yellow]")
        return

    for a in agents:
        table.add_row(a.id, a.display_name, str(a.kind))
        
    console.print(table)
    
@agent.command("test")
@click.argument("agent_id")
def test_agent(agent_id):
    """Test agent availability."""
    registry = get_registry()
    try:
        engine = registry.get(agent_id)
        is_available = engine.check_availability()
        if is_available:
            console.print(f"[green]Agent {agent_id} is available[/green]")
        else:
            console.print(f"[red]Agent {agent_id} is unavailable[/red]")
    except Exception as e:
        console.print(f"[red]Error testing agent: {e}[/red]")


@agent.command("check")
def agent_check():
    """Health check all registered agents."""
    import json
    
    registry = get_registry()
    agents = registry.list_metadata()
    
    if not agents:
        console.print("[yellow]No agents registered[/yellow]")
        return
    
    table = Table(title="Agent Health Check")
    table.add_column("ID", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Response", style="dim")
    
    results = []
    for a in agents:
        try:
            engine = registry.get(a.id)
            is_available = engine.check_availability()
            status = "[green]✓ available[/green]" if is_available else "[red]✗ unavailable[/red]"
            response = "OK" if is_available else "Not responding"
            results.append({"id": a.id, "available": is_available})
        except Exception as e:
            status = "[red]✗ error[/red]"
            response = str(e)[:50]
            results.append({"id": a.id, "available": False, "error": str(e)})
        
        table.add_row(a.id, status, response)
    
    console.print(table)
    
    # Summary
    available_count = sum(1 for r in results if r.get("available"))
    total_count = len(results)
    console.print(f"\n[bold]{available_count}/{total_count} agents available[/bold]")


@agent.command("config")
@click.argument("agent_id")
@click.option("--model", help="Set default model")
@click.option("--timeout", type=int, help="Set timeout in seconds")
@click.option("--show", is_flag=True, help="Show current configuration")
@click.pass_context
def agent_config(ctx, agent_id: str, model: str, timeout: int, show: bool):
    """Configure an agent."""
    import yaml
    from pathlib import Path
    
    from devgodzilla.config import load_config
    
    config = load_config()
    
    # Determine config file path
    config_path = getattr(config, 'agent_config_path', None)
    if not config_path:
        config_path = Path("config/agents.yaml")
    else:
        config_path = Path(config_path)
    
    # Load existing config or create new
    agent_configs = {}
    if config_path.exists():
        with open(config_path) as f:
            agent_configs = yaml.safe_load(f) or {}
    
    # Get agent-specific config
    agent_config = agent_configs.get('agents', {}).get(agent_id, {})
    
    if show:
        # Display current config
        console.print(f"[bold]Configuration for {agent_id}:[/bold]")
        if not agent_config:
            console.print("[dim]No custom configuration[/dim]")
        else:
            for key, value in agent_config.items():
                console.print(f"  {key}: {value}")
        return
    
    # Update configuration
    updated = False
    if model is not None:
        agent_config['model'] = model
        updated = True
        console.print(f"[green]Set model to: {model}[/green]")
    
    if timeout is not None:
        agent_config['timeout_seconds'] = timeout
        updated = True
        console.print(f"[green]Set timeout to: {timeout}s[/green]")
    
    if not updated:
        console.print("[yellow]No configuration changes specified[/yellow]")
        console.print("Use --model or --timeout options to update configuration")
        return
    
    # Save configuration
    if 'agents' not in agent_configs:
        agent_configs['agents'] = {}
    agent_configs['agents'][agent_id] = agent_config
    
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, 'w') as f:
        yaml.dump(agent_configs, f, default_flow_style=False)
    
    console.print(f"[green]✓ Configuration saved to {config_path}[/green]")
