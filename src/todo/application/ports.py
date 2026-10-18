"""Application ports (interfaces for outbound adapters)."""
from abc import ABC, abstractmethod

from todo.domain.models import Priority, Task, TaskStatus, User


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
