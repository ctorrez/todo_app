"""In-memory implementation of repository ports for blazing-fast unit tests."""
import copy

from todo.application.ports import TaskRepository, UserRepository
from todo.domain.models import Task, TaskStatus, User


class InMemoryUserRepository(UserRepository):
    """In-memory User repository backed by a dictionary."""

    def __init__(self) -> None:
        self._users: dict[int, User] = {}
        self._next_id: int = 1

    def save(self, user: User) -> User:
        user_copy = copy.deepcopy(user)
        if user_copy.id is None:
            user_copy.id = self._next_id
            self._next_id += 1
        self._users[user_copy.id] = user_copy
        return copy.deepcopy(user_copy)

    def get_by_id(self, user_id: int) -> User | None:
        user = self._users.get(user_id)
        return copy.deepcopy(user) if user else None

    def get_by_email(self, email: str) -> User | None:
        email_clean = email.strip().lower()
        for user in self._users.values():
            if user.email == email_clean:
                return copy.deepcopy(user)
        return None

    def list_all(self) -> list[User]:
        return [copy.deepcopy(u) for u in self._users.values()]

    def count(self) -> int:
        return len(self._users)


class InMemoryTaskRepository(TaskRepository):
    """In-memory Task repository backed by a dictionary."""

    def __init__(self) -> None:
        self._tasks: dict[int, Task] = {}
        self._next_id: int = 1

    def save(self, task: Task) -> Task:
        task_copy = copy.deepcopy(task)
        if task_copy.id is None:
            task_copy.id = self._next_id
            self._next_id += 1
        self._tasks[task_copy.id] = task_copy
        return copy.deepcopy(task_copy)

    def get_by_id(self, task_id: int) -> Task | None:
        task = self._tasks.get(task_id)
        return copy.deepcopy(task) if task else None

    def list_by_user(
        self, user_id: int, status: TaskStatus | None = None
    ) -> list[Task]:
        tasks = [t for t in self._tasks.values() if t.user_id == user_id]
        if status is not None:
            tasks = [t for t in tasks if t.status == status]
        return [copy.deepcopy(t) for t in tasks]

    def delete(self, task_id: int) -> bool:
        if task_id in self._tasks:
            del self._tasks[task_id]
            return True
        return False
