"""Ollama models management."""

import httpx
from typing import List, Dict, Optional
from app.config import OLLAMA_BASE_URL


class ModelsManager:
    """Manage available Ollama models."""

    @staticmethod
    async def list_models() -> List[Dict[str, str]]:
        """List all available models from Ollama."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    return [
                        {"name": m["name"], "size": m.get("size", 0)}
                        for m in data.get("models", [])
                    ]
        except Exception as e:
            print(f"Error listing models: {e}")
        return []

    @staticmethod
    async def is_model_available(model_name: str) -> bool:
        """Check if a specific model is available."""
        models = await ModelsManager.list_models()
        return any(m["name"].startswith(model_name.split(":")[0]) for m in models)

    @staticmethod
    async def pull_model(model_name: str) -> bool:
        """Pull a model from Ollama registry."""
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    f"{OLLAMA_BASE_URL}/api/pull",
                    json={"name": model_name},
                    timeout=600.0
                )
                return response.status_code == 200
        except Exception as e:
            print(f"Error pulling model {model_name}: {e}")
            return False

    @staticmethod
    def get_default_models() -> List[str]:
        """Get list of recommended models."""
        return [
            "llama3.1:8b",
            "llama2:13b",
            "phi:latest",
            "tinyllama:latest",
            "neural-chat:latest",
        ]
