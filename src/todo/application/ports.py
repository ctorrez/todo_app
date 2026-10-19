"""Application ports (interfaces for outbound adapters)."""

from abc import ABC, abstractmethod
from datetime import datetime

import numpy as np
import numpy.typing as npt

from todo.domain.models import ParsedTask, Priority, Task, TaskStatus, User

Vector = npt.NDArray[np.float32]


class UserRepository(ABC):
    """Abstract port for User persistence."""

    @abstractmethod
    def save(self, user: User) -> User:
        """Persist a user entity (create or update). Returns saved entity with ID."""

    @abstractmethod
    def get_by_id(self, user_id: int) -> User | None:
        """Find a user by ID."""

    @abstractmethod
    def get_by_email(self, email: str) -> User | None:
        """Find a user by email address."""

    @abstractmethod
    def list_all(self) -> list[User]:
        """Return all registered users."""

    @abstractmethod
    def count(self) -> int:
        """Return the total number of users."""


class TaskRepository(ABC):
    """Abstract port for Task persistence."""

    @abstractmethod
    def save(self, task: Task) -> Task:
        """Persist a task entity (create or update). Returns saved entity with ID."""

    @abstractmethod
    def get_by_id(self, task_id: int) -> Task | None:
        """Find a task by ID."""

    @abstractmethod
    def list_by_user(
        self,
        user_id: int,
        status: TaskStatus | None = None,
        priority: Priority | None = None,
        overdue_only: bool = False,
        due_today_only: bool = False,
    ) -> list[Task]:
        """List tasks belonging to a user, optionally filtered by status, priority, or due dates."""

    @abstractmethod
    def delete(self, task_id: int) -> bool:
        """Delete a task by ID. Returns True if deleted, False if not found."""


class TaskParserPort(ABC):
    """Abstract port for extracting structured task information from natural language."""

    @abstractmethod
    def parse(self, text: str, reference_date: datetime | None = None) -> ParsedTask:
        """Parse raw text into a ParsedTask domain object."""


# --- Application Port 1: Embedding Generator ---
# Adapters: OllamaEmbeddingAdapter, FastEmbedAdapter, OpenAIEmbeddingAdapter


class TaskEmbeddingPort(ABC):
    """Abstract port for converting text into normalized vector embeddings."""

    @abstractmethod
    def embed_text(self, text: str) -> Vector:
        """Convert a single text string into a normalized float32 vector embedding."""

    @abstractmethod
    def embed_batch(self, texts: list[str]) -> list[Vector]:
        """Convert a list of text strings into normalized float32 vector embeddings."""


# --- Application Port 2: Vector Storage & Retrieval ---
# Adapters: SqliteVectorRepository (now), Qdrant / Chroma / Pinecone (later)


class TaskVectorRepository(ABC):
    """Abstract port for storing and performing similarity searches over task embeddings."""

    @abstractmethod
    def upsert_vector(self, task_id: int, user_id: int, vector: Vector) -> None:
        """Store or update the vector embedding for a task."""

    @abstractmethod
    def upsert_batch(self, items: list[tuple[int, int, Vector]]) -> None:
        """Store or update a batch of (task_id, user_id, vector) embeddings."""

    @abstractmethod
    def search_similar(
        self,
        query_vector: Vector,
        user_id: int,
        limit: int = 5,
        threshold: float = 0.5,
    ) -> list[tuple[int, float]]:
        """Find the top-k most similar tasks for a user, returning list of (task_id, score)."""

    @abstractmethod
    def delete_vector(self, task_id: int) -> None:
        """Remove a task's vector embedding from the store."""
