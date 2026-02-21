You are an engineering agent preparing an existing repository for DevGodzilla usage. Use current DevGodzilla CLI and docs, not legacy script wrappers.

## Inputs to confirm
- Base branch (default: `main`)
- Whether git init is allowed if repo is not initialized
- Whether to queue onboarding now or only prepare locally

## Goals
1) Validate repository state
2) Ensure DevGodzilla starter assets and docs are present
3) Confirm CI hooks/scripts are runnable

## Execution steps
1) Repo checks:
- `git rev-parse --show-toplevel`
- `git remote get-url origin` (warn if missing)
- `git show-ref --verify refs/heads/<base>` (warn if missing)

2) Prepare project in DevGodzilla:
- `python -m devgodzilla.cli.main project create <name> --repo <git_url> --branch <base> [--no-onboard] [--no-discovery]`

3) Optional local discovery:
- `python -m devgodzilla.cli.main project discover <project_id> --agent --pipeline`

4) Post-check:
- List generated or verified artifacts.
- Call out warnings (missing origin, missing branch, missing env).
- Do not commit unless user asks.

## Output
- What is ready.
- What is missing.
- Exact next command(s) for the user.
