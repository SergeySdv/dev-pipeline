You are an engineering agent bootstrapping a **new repository** with DevGodzilla starter assets. Create the folder structure, prompts, and CI scaffolding so the team can start shipping quickly.

## Inputs to confirm
- `PROJECT_NAME`
- `DESCRIPTION`
- Default branch name (assume `main` if not provided)
- Target CI(s): GitHub, GitLab, or both
- Preferred stack hints (Python/Node/Go/etc.)

## Goals
1) Create baseline project structure and docs
2) Add reusable DevGodzilla prompts
3) Wire CI script entrypoints for GitHub/GitLab
4) Leave repo in a clean, reviewable state

## Execution checklist

### 0) Safety
- Confirm repo root (`pwd`, `git status -sb`, `git branch --show-current`).
- If the repo is uninitialized and user approves, run `git init -b <default_branch>`.
- Never rewrite or drop existing user changes.

### 1) Scaffold
- Ensure directories: `docs/`, `prompts/`, `scripts/ci/`, `.github/workflows/` (if GitHub requested).
- Add/update `.gitignore` with common excludes.
- Add `README.md` with DevGodzilla overview, workflow entry points, and CI hooks.
- Add canonical docs references to:
  - `docs/DevGodzilla/CURRENT_STATE.md`
  - `docs/DevGodzilla/ARCHITECTURE.md`
  - `docs/cli.md`
  - `docs/ci.md`

### 2) Add prompts (`prompts/`)
- `project-init.prompt.md` (this file)
- `protocol-new.prompt.md`
- `protocol-resume.prompt.md`
- `protocol-review-merge.prompt.md`
- `protocol-review-merge-resume.prompt.md`

### 3) CI scripts (`scripts/ci/`)
- Add executable stubs:
  - `bootstrap.sh`
  - `lint.sh`
  - `typecheck.sh`
  - `test.sh`
  - `build.sh`
- If stack hints are known, prefill commands. Otherwise add safe placeholders that exit 0.

### 4) GitHub Actions (`.github/workflows/ci.yml`)
- Trigger on `push` and `pull_request`.
- Execute each `scripts/ci/*.sh` script only if present/executable.

### 5) GitLab CI (`.gitlab-ci.yml`)
- Stages: `bootstrap`, `lint`, `typecheck`, `test`, `build`.
- Each job runs matching `scripts/ci/*.sh` script if executable; otherwise logs skip and exits 0.

### 6) Finalize
- Run `git status` and summarize created/updated files.
- Do not commit unless user explicitly asks.

## Deliverable
- Short summary of what was created.
- Paths to key files.
- Remaining placeholders the team must customize.
