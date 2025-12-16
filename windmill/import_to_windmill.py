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
import urllib.request
import urllib.error

SCRIPTS_DIR = Path(__file__).parent / "scripts" / "devgodzilla"
FLOWS_DIR = Path(__file__).parent / "flows" / "devgodzilla"


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


def create_script(base_url: str, token: str, workspace: str, path: str, content: str, summary: str) -> bool:
    """Create or update a script in Windmill."""
    
    # Check if script exists
    check = api_request(base_url, f"/w/{workspace}/scripts/get/p/{path}", token)
    
    if "error" not in check or check.get("code") != 404:
        # Script exists, we need to create a new version
        print(f"  Script exists, creating new version...")
        # For existing scripts, we use the scripts/create endpoint with force
        payload = {
            "path": path,
            "summary": summary,
            "description": f"DevGodzilla: {summary}",
            "content": content,
            "language": "python3",
            "is_template": False,
        }
        result = api_request(base_url, f"/w/{workspace}/scripts/create", token, "POST", payload)
    else:
        # Create new script
        payload = {
            "path": path,
            "summary": summary,
            "description": f"DevGodzilla: {summary}",
            "content": content,
            "language": "python3",
            "is_template": False,
        }
        result = api_request(base_url, f"/w/{workspace}/scripts/create", token, "POST", payload)
    
    return "error" not in result


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
    
    if "error" not in check or check.get("code") != 404:
        # Flow exists, update it
        print(f"  Flow exists, updating...")
        result = api_request(base_url, f"/w/{workspace}/flows/update/{path}", token, "POST", payload)
    else:
        # Create new flow
        result = api_request(base_url, f"/w/{workspace}/flows/create", token, "POST", payload)
    
    return "error" not in result


def main():
    parser = argparse.ArgumentParser(description="Import DevGodzilla to Windmill")
    parser.add_argument("--url", default="http://192.168.1.227", help="Windmill base URL")
    parser.add_argument("--token", required=True, help="Windmill API token")
    parser.add_argument("--workspace", default="demo1", help="Windmill workspace")
    parser.add_argument("--scripts-only", action="store_true", help="Only import scripts")
    parser.add_argument("--flows-only", action="store_true", help="Only import flows")
    args = parser.parse_args()
    
    print(f"Importing DevGodzilla to {args.url} (workspace: {args.workspace})")
    print()
    
    # Test connection
    version = api_request(args.url, "/version", args.token)
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
        scripts = [
            ("clone_repo", "Clone a GitHub repository"),
            ("analyze_project", "Analyze project structure"),
            ("initialize_speckit", "Initialize .specify/ directory"),
            ("generate_spec", "Generate feature specification"),
            ("generate_plan", "Generate implementation plan"),
            ("generate_tasks", "Generate task breakdown"),
            ("execute_step", "Execute step with AI agent"),
            ("run_qa", "Run QA checks"),
            ("handle_feedback", "Handle feedback loop"),
        ]
        
        for script_name, summary in scripts:
            path = f"u/devgodzilla/{script_name}"
            script_file = SCRIPTS_DIR / f"{script_name}.py"
            
            if not script_file.exists():
                print(f"✗ {path} - file not found")
                error_count += 1
                continue
            
            content = read_script_content(script_file)
            print(f"Importing {path}...", end=" ")
            
            if create_script(args.url, args.token, args.workspace, path, content, summary):
                print("✓")
                success_count += 1
            else:
                print("✗")
                error_count += 1
        print()
    
    # Import flows
    if not args.scripts_only:
        print("=== Importing Flows ===")
        flows = [
            ("project_onboarding", "f/devgodzilla/project_onboarding"),
            ("spec_to_tasks", "f/devgodzilla/spec_to_tasks"),
            ("execute_protocol", "f/devgodzilla/execute_protocol"),
        ]
        
        for flow_name, path in flows:
            flow_file = FLOWS_DIR / f"{flow_name}.flow.json"
            
            if not flow_file.exists():
                print(f"✗ {path} - file not found")
                error_count += 1
                continue
            
            flow_def = json.loads(flow_file.read_text())
            print(f"Importing {path}...", end=" ")
            
            if create_flow(args.url, args.token, args.workspace, path, flow_def):
                print("✓")
                success_count += 1
            else:
                print("✗")
                error_count += 1
        print()
    
    print(f"=== Summary ===")
    print(f"Success: {success_count}")
    print(f"Errors: {error_count}")
    
    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
