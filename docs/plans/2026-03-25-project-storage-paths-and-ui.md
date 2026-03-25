# Project Storage Paths And UI

## Goal

Define the correct filesystem layout and UI/configuration model for DevGodzilla so that:

- the control-plane repo is not mixed with managed project repos
- managed repos do not live under the `dev-pipeline` checkout
- worktrees and artifacts have a predictable structure
- operators can choose where a project lives without exposing unsafe arbitrary path behavior
- local development and remote build-server deployments use the same conceptual model

## Problem

The current local-dev default puts managed repos under:

- `dev-pipeline/projects/...`

This creates several problems:

- IntelliJ and other IDEs detect many nested Git roots
- the control-plane repo and managed project repos become physically mixed
- old worktrees under `projects/.../worktrees/...` create noisy Git remote and VCS root lists
- the layout is convenient for local bootstrapping but misleading for real server deployment

The current model is also too simple conceptually:

- there is a global `DEVGODZILLA_PROJECTS_ROOT`
- there is a per-project `local_path`

That works operationally, but it does not clearly distinguish:

- managed clone vs existing repo
- repo path vs worktree path vs artifact path
- admin-level storage policy vs per-project overrides

## Design Principles

1. Keep the control plane separate from managed code.
2. Treat server filesystem paths as operator-controlled, not end-user free-form values.
3. Make repository location explicit.
4. Derive worktree and artifact locations by policy whenever possible.
5. Allow overrides, but only for admins or project managers.
6. Make all paths absolute, validated, and server-local.

## Correct Filesystem Layout

Recommended remote-server layout:

- app repo: `/srv/devgodzilla/app`
- managed repos root: `/srv/devgodzilla/repos`
- worktrees root: `/srv/devgodzilla/worktrees`
- artifacts root: `/srv/devgodzilla/artifacts`

Recommended local layout:

- app repo: `/Users/<user>/IdeaProjects/dev-pipeline`
- managed repos root: `/Users/<user>/DevGodzillaProjects/repos`
- worktrees root: `/Users/<user>/DevGodzillaProjects/worktrees`
- artifacts root: `/Users/<user>/DevGodzillaProjects/artifacts`

This keeps the DevGodzilla source tree clean and avoids nested Git roots under the app checkout.

## Storage Concepts

The system should model three storage locations:

1. Repository root
2. Worktree root
3. Artifact root

These should not be collapsed into one ambiguous `local_path`.

Important clarification:

- branches do not need their own storage path setting
- Git branch refs belong to the repository itself
- worktrees may live outside the main repo root, but they are still attached to that repo

## Project Storage Modes

Each project should conceptually support two modes:

### 1. Managed Clone

DevGodzilla clones and owns the working repo.

Inputs:

- `git_url`
- optional `managed_repo_root_override`

Behavior:

- repo path is derived under the managed repo root
- worktrees are derived under the worktree root
- artifacts are derived under the artifact root

### 2. Existing Server Repo

DevGodzilla attaches to an already existing repo on the build machine.

Inputs:

- `existing_repo_path`

Behavior:

- repo path is exactly the validated server path
- worktrees are still derived by policy
- artifacts are still derived by policy

## UI Model

The UI should expose storage in a controlled way.

### Project-Level UI

Project create/edit should show:

- `Repository Source`
  - `Managed by DevGodzilla`
  - `Existing repository on build server`

If `Managed by DevGodzilla`:

- show `Git URL`
- optionally show `Managed Repo Root Override`

If `Existing repository on build server`:

- show `Server Repository Path`

### Advanced Storage Section

This should be admin-only or manager-only.

Show:

- `Use default storage policy`
- `Customize storage roots`

If customized:

- `Worktrees Root Override`
- `Artifacts Root Override`

Normal users should not be asked to configure all of these fields directly.

## Validation Rules

All path inputs must be:

- absolute
- normalized
- server-local
- readable
- writable when required

For existing repos:

- path must exist
- `.git` must exist
- path must be inside an allowed root unless explicitly whitelisted

For managed roots, worktree roots, and artifact roots:

- path must be absolute
- parent must exist or be creatable
- path must not point inside the DevGodzilla app repo

## Global Configuration

Global config should be the default policy layer.

Desired settings:

- `DEVGODZILLA_PROJECTS_ROOT`
- `DEVGODZILLA_WORKTREES_ROOT`
- `DEVGODZILLA_ARTIFACTS_ROOT`
- `DEVGODZILLA_ALLOWED_EXTERNAL_REPO_ROOTS`

Behavior:

- project settings override global defaults only when explicitly configured
- otherwise the project inherits the global storage policy

## Runtime Resolution Rules

Resolution order should be:

1. Project-level explicit override
2. Global config default
3. derived fallback

Repository resolution:

- existing repo mode uses configured repo path
- managed clone mode derives a repo path under the managed repo root

Worktree resolution:

- default should be derived from the configured worktrees root
- if no dedicated worktrees root exists yet, fallback may be under the repo

Artifact resolution:

- derive from artifact root by project and run identifiers
- avoid storing long-lived workflow artifacts inside the DevGodzilla app checkout

## Recommended Defaults

For production:

- default to `Managed by DevGodzilla`
- allow `Existing repository on build server` for advanced cases
- keep worktrees outside the main repo tree when supported
- keep artifacts outside both the app repo and the managed repo when practical

For local development:

- do not default to `dev-pipeline/projects`
- use an external root such as `~/DevGodzillaProjects`

## Migration Strategy

Existing installations need a safe migration path.

Steps:

1. Add new storage config fields and UI labels.
2. Keep current `local_path` support as compatibility mode.
3. Move existing managed repos outside `dev-pipeline`.
4. Repair Git worktree metadata after repo moves.
5. Rewrite persisted DB paths for projects, protocol runs, and spec runs.
6. Remove stale IDE VCS mappings that point at old nested paths.

Compatibility note:

- legacy projects that only have `local_path` should continue to work
- new UI should interpret such projects as `Existing repository on build server`

## What To Avoid

Do not implement:

- unrestricted arbitrary filesystem path entry for all users
- separate branch storage settings
- defaults that place managed repos under the DevGodzilla app checkout
- UI wording that implies a local desktop path when the value is actually server-side

## Recommended Next Implementation Slice

The smallest useful implementation slice is:

1. keep `local_path` compatibility
2. add project `repo_mode`
3. add admin-level storage defaults for repos, worktrees, and artifacts
4. update project UI to expose `Managed by DevGodzilla` vs `Existing repository on build server`
5. derive the rest of the paths from policy instead of asking users for too many raw paths

That gives a cleaner mental model immediately without requiring a full storage-system rewrite in one step.
