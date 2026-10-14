"""Release local inference memory after extraction; never remove model files."""
import httpx
from .config import OLLAMA_URL, MODEL


def release_model(model=MODEL):
    try:
        response=httpx.post(OLLAMA_URL+'/api/generate',json={'model':model,'keep_alive':0},timeout=5)
        response.raise_for_status()
        return True
    except httpx.HTTPError:
        # Extraction evidence must still be saved when the model server fails.
        return False
