
import requests

def main(sprint_id: int):
    """Complete a sprint and finalize metrics."""
    api_base = "http://devgodzilla-api:8000"
    
    response = requests.post(f"{api_base}/sprints/{sprint_id}/actions/complete")
    response.raise_for_status()
    
    return response.json()
