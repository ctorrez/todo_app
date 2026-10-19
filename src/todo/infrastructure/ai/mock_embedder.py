"""Mock embedding adapter for fast, deterministic, offline unit testing."""

import hashlib

import numpy as np

from todo.application.ports import TaskEmbeddingPort, Vector


class MockTaskEmbedder(TaskEmbeddingPort):
    """Deterministic, mock embedder that converts text into pseudo-vectors without calling external services."""

    def __init__(self, dimensions: int = 16) -> None:
        self.dimensions = dimensions

    def embed_text(self, text: str) -> Vector:
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: list[str]) -> list[Vector]:
        vectors: list[Vector] = []
        for text in texts:
            words = text.lower().split()
            arr = np.zeros(self.dimensions, dtype=np.float32)
            for word in words:
                h = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16)
                slot = h % self.dimensions
                arr[slot] += 1.0
            norm = float(np.linalg.norm(arr))
            if norm > 0:
                arr = arr / norm
            else:
                arr[0] = 1.0
            vectors.append(arr)
        return vectors
