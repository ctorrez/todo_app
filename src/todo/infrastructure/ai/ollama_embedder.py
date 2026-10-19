"""Ollama local AI adapter implementing TaskEmbeddingPort."""

import json
import urllib.error
import urllib.request

import numpy as np

from todo.application.ports import TaskEmbeddingPort, Vector
from todo.domain.exceptions import TodoDomainError


class OllamaTaskEmbedder(TaskEmbeddingPort):
    """Generates normalized vector embeddings using local Ollama (e.g. all-minilm, nomic-embed-text)."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "all-minilm",
        timeout: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def embed_text(self, text: str) -> Vector:
        """Embed a single text string."""
        clean = text.strip() or "empty"
        results = self.embed_batch([clean])
        return results[0]

    def embed_batch(self, texts: list[str]) -> list[Vector]:
        """Embed a batch of text strings."""
        if not texts:
            return []

        url = f"{self.base_url}/api/embed"
        payload = {
            "model": self.model,
            "input": texts,
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                raw_body = response.read().decode("utf-8")
        except urllib.error.URLError as err:
            raise TodoDomainError(
                f"Could not connect to local Ollama at '{self.base_url}'. "
                "Ensure the Ollama application is running on your machine."
            ) from err

        try:
            data = json.loads(raw_body)
            raw_embeddings = data.get("embeddings", [])
        except (json.JSONDecodeError, KeyError) as err:
            raise TodoDomainError(f"Failed to parse embedding response from Ollama: {err}") from err

        vectors: list[Vector] = []
        for raw in raw_embeddings:
            arr = np.array(raw, dtype=np.float32)
            norm = float(np.linalg.norm(arr))
            if norm > 0:
                arr = arr / norm
            vectors.append(arr)

        return vectors
