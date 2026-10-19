import copy

import numpy as np

from todo.application.ports import TaskRepository, TaskVectorRepository, UserRepository, Vector
from todo.domain.models import Priority, Task, TaskStatus, User


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
        self,
        user_id: int,
        status: TaskStatus | None = None,
        priority: Priority | None = None,
        overdue_only: bool = False,
        due_today_only: bool = False,
    ) -> list[Task]:
        tasks = [t for t in self._tasks.values() if t.user_id == user_id]
        if status is not None:
            tasks = [t for t in tasks if t.status == status]
        if priority is not None:
            tasks = [t for t in tasks if t.priority == priority]
        if overdue_only:
            tasks = [t for t in tasks if t.is_overdue]
        if due_today_only:
            tasks = [t for t in tasks if t.is_due_today]
        return [copy.deepcopy(t) for t in tasks]

    def delete(self, task_id: int) -> bool:
        if task_id in self._tasks:
            del self._tasks[task_id]
            return True
        return False


class InMemoryTaskVectorRepository(TaskVectorRepository):
    """In-memory vector store backed by a dictionary for instant, mock-free unit tests."""

    def __init__(self) -> None:
        self._vectors: dict[int, tuple[int, Vector]] = {}

    def upsert_vector(self, task_id: int, user_id: int, vector: Vector) -> None:
        self._vectors[task_id] = (user_id, vector.copy())

    def upsert_batch(self, items: list[tuple[int, int, Vector]]) -> None:
        for task_id, user_id, vector in items:
            self._vectors[task_id] = (user_id, vector.copy())

    def search_similar(
        self,
        query_vector: Vector,
        user_id: int,
        limit: int = 5,
        threshold: float = 0.5,
    ) -> list[tuple[int, float]]:
        user_items = [(tid, vec) for tid, (uid, vec) in self._vectors.items() if uid == user_id]
        if not user_items:
            return []

        task_ids = [tid for tid, _ in user_items]
        matrix = np.vstack([vec for _, vec in user_items])

        q = query_vector.astype(np.float32)
        q_norm = float(np.linalg.norm(q))
        if q_norm == 0.0:
            return []
        q_unit = q / q_norm

        matrix_norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        matrix_norms[matrix_norms == 0.0] = 1.0
        matrix_unit = matrix / matrix_norms

        sims = np.dot(matrix_unit, q_unit)

        results: list[tuple[int, float]] = []
        for tid, score in zip(task_ids, sims.tolist(), strict=True):
            if score >= threshold:
                results.append((tid, float(score)))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]

    def delete_vector(self, task_id: int) -> None:
        self._vectors.pop(task_id, None)
