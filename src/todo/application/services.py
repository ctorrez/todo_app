"""Application use-case services orchestrating domain logic and ports."""
from datetime import datetime

from todo.application.ports import TaskRepository, UserRepository
from todo.domain.exceptions import (
    TaskNotFoundError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from todo.domain.models import Task, TaskStatus, User


class UserService:
    """Use cases related to User management."""

    def __init__(self, user_repo: UserRepository) -> None:
        self._user_repo = user_repo

    def register_user(self, first_name: str, last_name: str, email: str) -> User:
        """Register a new user after verifying email uniqueness."""
        email_clean = email.strip().lower()
        existing = self._user_repo.get_by_email(email_clean)
        if existing:
            raise UserAlreadyExistsError(f"User with email '{email_clean}' already exists.")

        user = User(first_name=first_name, last_name=last_name, email=email_clean)
        return self._user_repo.save(user)

    def get_user(self, user_id: int) -> User:
        """Retrieve user by ID or raise UserNotFoundError."""
        user = self._user_repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundError(f"User with ID {user_id} was not found.")
        return user

    def list_users(self) -> list[User]:
        """Return all registered users."""
        return self._user_repo.list_all()

    def has_users(self) -> bool:
        """Check if any users exist in the system."""
        return self._user_repo.count() > 0


class TaskService:
    """Use cases related to Task management."""

    def __init__(self, task_repo: TaskRepository, user_repo: UserRepository) -> None:
        self._task_repo = task_repo
        self._user_repo = user_repo

    def create_task(
        self,
        user_id: int,
        title: str,
        description: str = "",
        due_date: datetime | None = None,
    ) -> Task:
        """Create a new task for an existing user."""
        # Ensure user exists before creating task
        user = self._user_repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundError(f"Cannot create task: User {user_id} does not exist.")

        task = Task(
            user_id=user_id,
            title=title,
            description=description,
            due_date=due_date,
        )
        return self._task_repo.save(task)

    def get_task(self, task_id: int) -> Task:
        """Retrieve task by ID or raise TaskNotFoundError."""
        task = self._task_repo.get_by_id(task_id)
        if not task:
            raise TaskNotFoundError(f"Task with ID {task_id} was not found.")
        return task

    def list_tasks(
        self, user_id: int, status: TaskStatus | None = None
    ) -> list[Task]:
        """List tasks belonging to a user, optionally filtered by status."""
        user = self._user_repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundError(f"Cannot list tasks: User {user_id} does not exist.")
        return self._task_repo.list_by_user(user_id, status=status)

    def complete_task(self, task_id: int) -> Task:
        """Mark a task as completed."""
        task = self.get_task(task_id)
        task.complete()
        return self._task_repo.save(task)

    def reopen_task(self, task_id: int) -> Task:
        """Reopen a completed task."""
        task = self.get_task(task_id)
        task.reopen()
        return self._task_repo.save(task)

    def delete_task(self, task_id: int) -> None:
        """Delete a task by ID."""
        deleted = self._task_repo.delete(task_id)
        if not deleted:
            raise TaskNotFoundError(f"Cannot delete: Task with ID {task_id} was not found.")
