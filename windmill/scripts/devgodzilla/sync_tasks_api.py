
import requests

def main(sprint_id: int, spec_path: str):
    """Import tasks from SpecKit markdown into sprint."""
    api_base = "http://devgodzilla-api:8000"
    
    payload = {
        "spec_path": spec_path,
        "overwrite_existing": False 
    }
    
    response = requests.post(
        f"{api_base}/sprints/{sprint_id}/actions/import-tasks",
        json=payload
    )
    response.raise_for_status()
    
    return response.json()
