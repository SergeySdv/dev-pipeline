# Windmill integration assets

This directory contains the Windmill-side assets for the DevGodzilla stack.

## What’s here

- `windmill/flows/devgodzilla/`: exported flow JSON (intended to live under `f/devgodzilla/*` in Windmill).
- `windmill/scripts/devgodzilla/`: Python scripts for Windmill’s `python` runtime (intended to live under `u/devgodzilla/*` in Windmill).

## How scripts talk to DevGodzilla

Most scripts call the DevGodzilla API via `windmill/scripts/devgodzilla/_api.py`, which reads:

- `DEVGODZILLA_API_URL` (defaults to `http://devgodzilla-api:8000` inside Docker Compose)

Docker Compose already sets `DEVGODZILLA_API_URL` for the Windmill server/workers.

## Notes

- Some flows rely on JavaScript `input_transforms` and require a Windmill build with `deno_core` enabled (see `docs/DevGodzilla/WINDMILL-WORKFLOWS.md`).
- A few legacy scripts/docs still reference TasksGodzilla (`TASKSGODZILLA_API_URL`, `TASKSGODZILLA_API_TOKEN`) for Codex log/artifact proxying.

