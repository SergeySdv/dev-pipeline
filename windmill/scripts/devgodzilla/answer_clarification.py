"""
Answer Clarification Script

Submits an answer to a pending clarification via DevGodzilla API.
"""

import os
import urllib.request
import json
from typing import Dict, Any


def main(
    clarification_id: int,
    answer: str
) -> Dict[str, Any]:
    """Answer a pending clarification.
    
    Args:
        clarification_id: Clarification ID to answer
        answer: The answer text or selected option
    """
    try:
        base_url = os.environ.get("DEVGODZILLA_API_URL", "http://devgodzilla-api:8000")

        data = {"answer": answer}

        req = urllib.request.Request(
            f"{base_url}/clarifications/{clarification_id}/answer",
            data=json.dumps(data).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            clarification = json.loads(response.read().decode())
        
        return {
            "success": True,
            "clarification": {
                "id": clarification.get("id"),
                "question": clarification.get("question"),
                "answer": clarification.get("answer"),
                "status": clarification.get("status"),
            }
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
