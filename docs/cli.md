# DevGodzilla CLI

> Status: Active
> Scope: Current CLI usage
> Source of truth: `devgodzilla/cli/main.py`, `devgodzilla/cli/*.py`
> Last updated: 2026-02-21

## Entry Points

Preferred:

```bash
python -m devgodzilla.cli.main --help
```

Compatibility wrapper scripts still present in `scripts/` may reference legacy names; prefer module invocation above.

## Global Options

```bash
python -m devgodzilla.cli.main [--json] [--verbose] <command> ...
```

- `--json`: machine-readable output
- `--verbose`: debug logging

## Main Command Groups

- `project`: project lifecycle and discovery
- `protocol`: protocol run lifecycle
- `step`: step execution and status
- `qa`: QA operations
- `agent`: engine/agent listing and availability tests
- `spec`: SpecKit-style artifact workflow
- `clarify`: clarification listing/answering

## Common Examples

### Projects

```bash
python -m devgodzilla.cli.main project list
python -m devgodzilla.cli.main project show 1
python -m devgodzilla.cli.main project create demo --repo https://github.com/org/repo.git --branch main
python -m devgodzilla.cli.main project discover 1 --agent --pipeline
```

### Protocols

```bash
python -m devgodzilla.cli.main protocol create 1 0001-demo --description "demo task"
python -m devgodzilla.cli.main protocol start 1
python -m devgodzilla.cli.main protocol status 1
python -m devgodzilla.cli.main protocol list --project 1
python -m devgodzilla.cli.main protocol cancel 1
```

### Steps and QA

```bash
python -m devgodzilla.cli.main step list --protocol 1
python -m devgodzilla.cli.main step run 5
python -m devgodzilla.cli.main step qa 5
python -m devgodzilla.cli.main qa evaluate . step-1
python -m devgodzilla.cli.main qa gates
```

### Agents

```bash
python -m devgodzilla.cli.main agent list
python -m devgodzilla.cli.main agent test opencode
```

### Spec Workflow

```bash
python -m devgodzilla.cli.main spec init .
python -m devgodzilla.cli.main spec specify "Add authentication"
python -m devgodzilla.cli.main spec plan specs/001-add-auth/spec.md
python -m devgodzilla.cli.main spec tasks specs/001-add-auth/plan.md
```

## Configuration Notes

CLI reads config via `devgodzilla.config.load_config()` and uses `DEVGODZILLA_*` env vars (DB URL/path, Windmill settings, engine defaults, etc.).

See:

- `README.md`
- `docs/DevGodzilla/CURRENT_STATE.md`
