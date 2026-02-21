#!/usr/bin/env python3
"""
Windmill Script Importer

Imports DevGodzilla scripts and flows to Windmill via the API.

Usage:
    python import_to_windmill.py --url http://192.168.1.227 --token <TOKEN>
    
To get a token:
1. Go to Windmill UI > Settings > Tokens
2. Create a new token with admin permissions
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any
import urllib.request
import urllib.error
import re

DEFAULT_IMPORT_MANIFEST: dict[str, Any] = {
    "scripts": {
        "source_dir": "scripts/devgodzilla",
        "path_prefix": "u/devgodzilla",
        "glob": "*.py",
    },
    "flows": {
        "source_dir": "flows/devgodzilla",
        "path_prefix": "f/devgodzilla",
        "glob": "*.flow.json",
        "strip_suffix": ".flow.json",
    },
    "apps": {
        "source_dir": "apps/devgodzilla",
        "path_prefix": "app/devgodzilla",
        "glob": "*.app.json",
        "items": [
            {"file": "devgodzilla_dashboard.app.json", "path": "app/devgodzilla/dashboard"},
            {"file": "devgodzilla_projects.app.json", "path": "app/devgodzilla/projects"},
            {"file": "devgodzilla_project_detail.app.json", "path": "app/devgodzilla/project_detail"},
            {"file": "devgodzilla_protocols.app.json", "path": "app/devgodzilla/protocols"},
            {"file": "devgodzilla_protocol_detail.app.json", "path": "app/devgodzilla/protocol_detail"},
        ],
    },
}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = dict(base)
    for key, value in override.items():
        base_value = merged.get(key)
        if isinstance(base_value, dict) and isinstance(value, dict):
            merged[key] = _deep_merge(base_value, value)
        else:
            merged[key] = value
    return merged


def load_import_manifest(root: Path, manifest_path: Path | None = None) -> dict[str, Any]:
    """Load importer manifest from disk, merging onto defaults."""
    manifest = DEFAULT_IMPORT_MANIFEST
    candidate = manifest_path or (root / "import-manifest.json")
    if candidate.exists():
        loaded = json.loads(candidate.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise ValueError(f"Invalid manifest format in {candidate}: expected object")
        manifest = _deep_merge(DEFAULT_IMPORT_MANIFEST, loaded)
    return manifest


def read_script_content(script_path: Path) -> str:
    """Read Python script content."""
    return script_path.read_text()


def create_script_payload(path: str, content: str, summary: str = "") -> dict:
    """Create Windmill script API payload."""
    return {
        "path": path,
        "summary": summary,
        "description": f"DevGodzilla script: {path}",
        "content": content,
        "language": "python3",
        "is_template": False,
        "kind": "script",
        "tag": "devgodzilla",
    }


def api_request(base_url: str, endpoint: str, token: str, method: str = "GET", data: dict = None) -> dict:
    """Make API request to Windmill."""
    url = f"{base_url}/api{endpoint}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    
    req_data = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            body = response.read().decode()
            try:
                return json.loads(body) if body else {}
            except json.JSONDecodeError:
                return {"version": body.strip()}  # Handle plain text response
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else str(e)
        print(f"  Error: {e.code} - {error_body[:100]}")
        return {"error": error_body, "code": e.code}
    except Exception as e:
        return {"error": str(e)}

def _load_token_from_env_file(path: Path) -> str | None:
    """
    Load a token from a simple KEY=VALUE env file.

    Recognized keys (first match wins):
    - WINDMILL_TOKEN
    - DEVGODZILLA_WINDMILL_TOKEN
    - VITE_TOKEN (Windmill React app dev token)
    """
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    keys = ["WINDMILL_TOKEN", "DEVGODZILLA_WINDMILL_TOKEN", "VITE_TOKEN"]
    for key in keys:
        m = re.search(rf"^{re.escape(key)}=(.*)$", text, flags=re.MULTILINE)
        if not m:
            continue
        value = m.group(1).strip()
        if value and not value.startswith("your_"):
            return value
    return None


def create_script(base_url: str, token: str, workspace: str, path: str, content: str, summary: str) -> bool:
    """Create or update a script in Windmill."""
    
    # Check if script exists
    check = api_request(base_url, f"/w/{workspace}/scripts/get/p/{path}", token)
    
    exists = not (isinstance(check, dict) and "error" in check)

    payload = {
        "path": path,
        "summary": summary,
        "description": f"DevGodzilla: {summary}",
        "content": content,
        "language": "python3",
        "is_template": False,
    }

    if exists:
        # Script exists: create a new version by chaining from the latest hash.
        # Without parent_hash, Windmill rejects the create with a path-conflict.
        print("  Script exists, creating new version...")
        existing_hash = check.get("hash") if isinstance(check, dict) else None
        if existing_hash:
            payload["parent_hash"] = existing_hash

    result = api_request(base_url, f"/w/{workspace}/scripts/create", token, "POST", payload)

    # If still conflicting, archive then create (last resort).
    if (
        isinstance(result, dict)
        and "error" in result
        and result.get("code") == 400
        and "Path conflict" in str(result.get("error", ""))
    ):
        api_request(base_url, f"/w/{workspace}/scripts/archive/p/{path}", token, "POST", {})
        result = api_request(base_url, f"/w/{workspace}/scripts/create", token, "POST", payload)
    
    return not (isinstance(result, dict) and "error" in result)


def create_flow(base_url: str, token: str, workspace: str, path: str, flow_def: dict) -> bool:
    """Create or update a flow in Windmill."""
    
    # Check if flow exists
    check = api_request(base_url, f"/w/{workspace}/flows/get/{path}", token)
    
    payload = {
        "path": path,
        "summary": flow_def.get("summary", ""),
        "description": flow_def.get("description", ""),
        "value": flow_def.get("value", {}),
        "schema": flow_def.get("schema", {}),
    }
    
    if not (isinstance(check, dict) and check.get("code") == 404 and "error" in check):
        # Flow exists, update it
        print("  Flow exists, updating...")
        result = api_request(base_url, f"/w/{workspace}/flows/update/{path}", token, "POST", payload)
    else:
        # Create new flow
        result = api_request(base_url, f"/w/{workspace}/flows/create", token, "POST", payload)
    
    return not (isinstance(result, dict) and "error" in result)


def _inject_script_hashes_into_flow(base_url: str, token: str, workspace: str, flow_def: dict) -> None:
    """
    Best-effort: add script hashes to PathScript modules.

    Some Windmill deployments disallow running scripts by path via the jobs API.
    Including the script hash allows flows to execute script modules reliably.
    """

    def visit(node: object) -> None:
        if isinstance(node, dict):
            # PathScript node (OpenFlow schema)
            if node.get("type") == "script" and node.get("path") and not node.get("hash"):
                path = node["path"]
                info = api_request(base_url, f"/w/{workspace}/scripts/get/p/{path}", token)
                if "hash" in info:
                    node["hash"] = info["hash"]

            # Windmill flow module wrapper commonly stores the spec under "value"
            inner = node.get("value")
            if isinstance(inner, (dict, list)):
                visit(inner)

            # Recurse into all child containers (modules, branches, etc.)
            for v in node.values():
                if isinstance(v, (dict, list)):
                    visit(v)

        elif isinstance(node, list):
            for item in node:
                visit(item)

    visit(flow_def.get("value", {}))
def create_app(base_url: str, token: str, workspace: str, path: str, app_def: dict) -> bool:
    """Create or update an app in Windmill."""
    
    # Check if app exists
    check = api_request(base_url, f"/w/{workspace}/apps/get/{path}", token)
    
    payload = {
        "path": path,
        "summary": app_def.get("summary", ""),
        "value": app_def.get("value", {}),
        "policy": app_def.get("policy", {"execution_mode": "viewer"}),
    }
    
    if "error" not in check or check.get("code") != 404:
        # App exists, update it
        print("  App exists, updating...")
        result = api_request(base_url, f"/w/{workspace}/apps/update/{path}", token, "POST", payload)
    else:
        # Create new app
        result = api_request(base_url, f"/w/{workspace}/apps/create", token, "POST", payload)
        
        # Fallback: if create fails with 400, it might exist but hidden/archived or check failed
        if "error" in result and result.get("code") == 400:
             print("  Create failed (400), trying update...", end=" ")
             result = api_request(base_url, f"/w/{workspace}/apps/update/{path}", token, "POST", payload)
    
    return "error" not in result


def _resolve_source_dir(root: Path, section: dict[str, Any], fallback: str) -> Path:
    return root / section.get("source_dir", fallback)


def _strip_suffix(filename: str, suffix: str) -> str:
    if suffix and filename.endswith(suffix):
        return filename[: -len(suffix)]
    return Path(filename).stem


def _app_name_from_file(filename: str) -> str:
    if filename.endswith(".app.json"):
        return filename[: -len(".app.json")]
    return Path(filename).stem


def main():
    parser = argparse.ArgumentParser(description="Import DevGodzilla to Windmill")
    parser.add_argument("--url", default="http://192.168.1.227", help="Windmill base URL")
    parser.add_argument("--token", required=False, help="Windmill API token (or set WINDMILL_TOKEN env var)")
    parser.add_argument(
        "--token-file",
        required=False,
        help="Path to an env file containing WINDMILL_TOKEN/DEVGODZILLA_WINDMILL_TOKEN/VITE_TOKEN",
    )
    parser.add_argument("--workspace", default="demo1", help="Windmill workspace")
    parser.add_argument(
        "--root",
        default=os.environ.get("DEVGODZILLA_WINDMILL_IMPORT_ROOT", str(Path(__file__).parent)),
        help="Windmill export root containing scripts/flows/apps",
    )
    parser.add_argument(
        "--manifest",
        default=os.environ.get("DEVGODZILLA_WINDMILL_IMPORT_MANIFEST"),
        help="Optional import manifest JSON file",
    )
    parser.add_argument("--scripts-only", action="store_true", help="Only import scripts")
    parser.add_argument("--flows-only", action="store_true", help="Only import flows")
    args = parser.parse_args()
    root = Path(args.root).expanduser().resolve(strict=False)
    manifest_path = Path(args.manifest).expanduser().resolve(strict=False) if args.manifest else None
    manifest = load_import_manifest(root=root, manifest_path=manifest_path)

    token = args.token
    if not token and args.token_file:
        token = _load_token_from_env_file(Path(args.token_file))
    if not token:
        token = os.environ.get("WINDMILL_TOKEN") or os.environ.get("DEVGODZILLA_WINDMILL_TOKEN")
    if not token:
        print("Error: missing token (pass --token, or set WINDMILL_TOKEN, or use --token-file)")
        sys.exit(2)
    
    print(f"Importing DevGodzilla to {args.url} (workspace: {args.workspace})")
    print()
    
    # Test connection
    version = api_request(args.url, "/version", token)
    if "error" in version:
        print(f"Error connecting to Windmill: {version['error']}")
        sys.exit(1)
    print(f"Connected to Windmill {version}")
    print()
    
    success_count = 0
    error_count = 0
    
    # Import scripts
    if not args.flows_only:
        print("=== Importing Scripts ===")
        scripts_cfg = manifest.get("scripts", {})
        scripts_dir = _resolve_source_dir(root, scripts_cfg, "scripts/devgodzilla")
        script_glob = scripts_cfg.get("glob", "*.py")
        script_prefix = scripts_cfg.get("path_prefix", "u/devgodzilla")
        script_files = sorted([p for p in scripts_dir.glob(script_glob) if p.is_file()])
        for script_file in script_files:
            script_name = script_file.stem
            path = f"{script_prefix}/{script_name}"
            summary = script_name.replace("_", " ").strip().title()

            content = read_script_content(script_file)
            print(f"Importing {path}...", end=" ")

            if create_script(args.url, token, args.workspace, path, content, summary):
                print("✓")
                success_count += 1
            else:
                print("✗")
                error_count += 1
        print()
    
    # Import flows
    if not args.scripts_only:
        print("=== Importing Flows ===")
        flows_cfg = manifest.get("flows", {})
        flows_dir = _resolve_source_dir(root, flows_cfg, "flows/devgodzilla")
        flow_glob = flows_cfg.get("glob", "*.flow.json")
        flow_prefix = flows_cfg.get("path_prefix", "f/devgodzilla")
        flow_strip_suffix = flows_cfg.get("strip_suffix", ".flow.json")
        flow_files = sorted([p for p in flows_dir.glob(flow_glob) if p.is_file()])
        for flow_file in flow_files:
            flow_name = _strip_suffix(flow_file.name, flow_strip_suffix)
            path = f"{flow_prefix}/{flow_name}"
            flow_def = json.loads(flow_file.read_text())
            _inject_script_hashes_into_flow(args.url, token, args.workspace, flow_def)
            print(f"Importing {path}...", end=" ")

            if create_flow(args.url, token, args.workspace, path, flow_def):
                print("✓")
                success_count += 1
            else:
                print("✗")
                error_count += 1
        print()
    
    # Import apps
    if not args.scripts_only and not args.flows_only:
        print("=== Importing Apps ===")
        apps_cfg = manifest.get("apps", {})
        apps_dir = _resolve_source_dir(root, apps_cfg, "apps/devgodzilla")
        apps_prefix = apps_cfg.get("path_prefix", "app/devgodzilla")
        apps_items = apps_cfg.get("items") or []
        if apps_items:
            app_records = []
            for item in apps_items:
                filename = item.get("file", "")
                if not filename:
                    continue
                app_path = item.get("path") or f"{apps_prefix}/{_app_name_from_file(filename)}"
                app_records.append((filename, app_path))
        else:
            app_glob = apps_cfg.get("glob", "*.app.json")
            discovered = sorted([p for p in apps_dir.glob(app_glob) if p.is_file()])
            app_records = [(p.name, f"{apps_prefix}/{_app_name_from_file(p.name)}") for p in discovered]

        for filename, path in app_records:
            app_file = apps_dir / filename
            if not app_file.exists():
                print(f"✗ {path} - file not found ({app_file})")
                error_count += 1
                continue
                
            app_def = json.loads(app_file.read_text())
            print(f"Importing {path}...", end=" ")
            
            if create_app(args.url, token, args.workspace, path, app_def):
                print("✓")
                success_count += 1
            else:
                print("✗")
                error_count += 1
        print()
    
    print("=== Summary ===")
    print(f"Success: {success_count}")
    print(f"Errors: {error_count}")
    
    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
