"""AI Infrastructure adapters."""

from todo.infrastructure.ai.mock_parser import MockTaskParser
from todo.infrastructure.ai.ollama_parser import OllamaTaskParser

__all__ = ["MockTaskParser", "OllamaTaskParser"]
