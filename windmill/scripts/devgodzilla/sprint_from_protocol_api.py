
import requests
from typing import Optional

def main(protocol_id: int, sprint_name: Optional[str] = None, auto_sync: bool = True):
    """Create a sprint from a protocol run."""
    # Internal API address in docker-compose
    api_base = "http://devgodzilla-api:8000"
    
    payload = {
        "sprint_name": sprint_name,
        "auto_sync": auto_sync
    }
    
    # Send POST request to create sprint
    response = requests.post(
        f"{api_base}/protocols/{protocol_id}/actions/create-sprint",
        json=payload
    )
    
    # Raise exception for bad status codes
    response.raise_for_status()
    
    return response.json()
