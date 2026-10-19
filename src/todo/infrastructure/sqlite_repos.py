from collections.abc import Callable
from datetime import UTC, datetime

import numpy as np
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from todo.application.ports import TaskRepository, TaskVectorRepository, UserRepository, Vector
from todo.domain.exceptions import TaskNotFoundError, UserNotFoundError
from todo.domain.models import Priority, Task, TaskStatus, User
from todo.infrastructure.db import TaskEmbeddingModel, TaskModel, UserModel


class SqlAlchemyUserRepository(UserRepository):
    """SQLAlchemy implementation of UserRepository."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def save(self, user: User) -> User:
        with self._session_factory() as session, session.begin():
            if user.id is None:
                db_user = UserModel.from_domain(user)
                session.add(db_user)
                session.flush()
                user.id = db_user.id
            else:
                existing_user = session.get(UserModel, user.id)
                if existing_user is None:
                    raise UserNotFoundError(f"User with ID {user.id} not found.")
                existing_user.first_name = user.first_name
                existing_user.last_name = user.last_name
                existing_user.email = user.email
                db_user = existing_user
            return db_user.to_domain()

    def get_by_id(self, user_id: int) -> User | None:
        with self._session_factory() as session:
            db_user = session.get(UserModel, user_id)
            return db_user.to_domain() if db_user else None

    def get_by_email(self, email: str) -> User | None:
        with self._session_factory() as session:
            stmt = select(UserModel).where(UserModel.email == email.strip().lower())
            db_user = session.execute(stmt).scalar_one_or_none()
            return db_user.to_domain() if db_user else None

    def list_all(self) -> list[User]:
        with self._session_factory() as session:
            stmt = select(UserModel).order_by(UserModel.id)
            db_users = session.execute(stmt).scalars().all()
            return [u.to_domain() for u in db_users]

    def count(self) -> int:
        with self._session_factory() as session:
            stmt = select(func.count(UserModel.id))
            return session.execute(stmt).scalar_one()


class SqlAlchemyTaskRepository(TaskRepository):
    """SQLAlchemy implementation of TaskRepository."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def save(self, task: Task) -> Task:
        with self._session_factory() as session, session.begin():
            if task.id is None:
                db_task = TaskModel.from_domain(task)
                session.add(db_task)
                session.flush()
                task.id = db_task.id
            else:
                existing_task = session.get(TaskModel, task.id)
                if existing_task is None:
                    raise TaskNotFoundError(f"Task with ID {task.id} not found.")
                existing_task.title = task.title
                existing_task.description = task.description
                existing_task.due_date = task.due_date
                existing_task.priority = task.priority.value
                existing_task.status = task.status.value
                existing_task.completed_at = task.completed_at
                db_task = existing_task
            return db_task.to_domain()

    def get_by_id(self, task_id: int) -> Task | None:
        with self._session_factory() as session:
            db_task = session.get(TaskModel, task_id)
            return db_task.to_domain() if db_task else None

    def list_by_user(
        self,
        user_id: int,
        status: TaskStatus | None = None,
        priority: Priority | None = None,
        overdue_only: bool = False,
        due_today_only: bool = False,
    ) -> list[Task]:
        with self._session_factory() as session:
            stmt = select(TaskModel).where(TaskModel.user_id == user_id)
            if status is not None:
                stmt = stmt.where(TaskModel.status == status.value)
            if priority is not None:
                stmt = stmt.where(TaskModel.priority == priority.value)
            stmt = stmt.order_by(TaskModel.created_at.desc())
            db_tasks = session.execute(stmt).scalars().all()
            domain_tasks = [t.to_domain() for t in db_tasks]
            if overdue_only:
                domain_tasks = [t for t in domain_tasks if t.is_overdue]
            if due_today_only:
                domain_tasks = [t for t in domain_tasks if t.is_due_today]
            return domain_tasks

    def delete(self, task_id: int) -> bool:
        with self._session_factory() as session, session.begin():
            db_task = session.get(TaskModel, task_id)
            if db_task:
                session.delete(db_task)
                return True
            return False


class SqlAlchemyTaskVectorRepository(TaskVectorRepository):
    """SQLAlchemy adapter implementing TaskVectorRepository using SQLite BLOB storage and NumPy cosine math."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def upsert_vector(self, task_id: int, user_id: int, vector: Vector) -> None:
        self.upsert_batch([(task_id, user_id, vector)])

    def upsert_batch(self, items: list[tuple[int, int, Vector]]) -> None:
        if not items:
            return
        with self._session_factory() as session, session.begin():
            for task_id, user_id, vector in items:
                raw_bytes = vector.astype(np.float32).tobytes()
                dims = len(vector)
                existing = session.get(TaskEmbeddingModel, task_id)
                if existing:
                    existing.user_id = user_id
                    existing.vector_data = raw_bytes
                    existing.dimensions = dims
                    existing.updated_at = datetime.now(UTC)
                else:
                    new_emb = TaskEmbeddingModel(
                        task_id=task_id,
                        user_id=user_id,
                        vector_data=raw_bytes,
                        dimensions=dims,
                    )
                    session.add(new_emb)

    def search_similar(
        self,
        query_vector: Vector,
        user_id: int,
        limit: int = 5,
        threshold: float = 0.5,
    ) -> list[tuple[int, float]]:
        with self._session_factory() as session:
            stmt = select(TaskEmbeddingModel).where(TaskEmbeddingModel.user_id == user_id)
            rows = session.execute(stmt).scalars().all()
            if not rows:
                return []

            task_ids: list[int] = []
            vectors_list: list[Vector] = []
            for r in rows:
                task_ids.append(r.task_id)
                v = np.frombuffer(r.vector_data, dtype=np.float32)
                vectors_list.append(v)

            matrix = np.vstack(vectors_list)
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
        with self._session_factory() as session, session.begin():
            emb = session.get(TaskEmbeddingModel, task_id)
            if emb:
                session.delete(emb)
