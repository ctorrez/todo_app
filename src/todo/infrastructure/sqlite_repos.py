"""Concrete SQLAlchemy implementations of UserRepository and TaskRepository."""
from collections.abc import Callable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from todo.application.ports import TaskRepository, UserRepository
from todo.domain.models import Task, TaskStatus, User
from todo.infrastructure.db import TaskModel, UserModel


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
                db_user = session.get(UserModel, user.id)
                if db_user:
                    db_user.first_name = user.first_name
                    db_user.last_name = user.last_name
                    db_user.email = user.email
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
                db_task = session.get(TaskModel, task.id)
                if db_task:
                    db_task.title = task.title
                    db_task.description = task.description
                    db_task.due_date = task.due_date
                    db_task.status = task.status.value
                    db_task.completed_at = task.completed_at
            return db_task.to_domain()

    def get_by_id(self, task_id: int) -> Task | None:
        with self._session_factory() as session:
            db_task = session.get(TaskModel, task_id)
            return db_task.to_domain() if db_task else None

    def list_by_user(
        self, user_id: int, status: TaskStatus | None = None
    ) -> list[Task]:
        with self._session_factory() as session:
            stmt = select(TaskModel).where(TaskModel.user_id == user_id)
            if status is not None:
                stmt = stmt.where(TaskModel.status == status.value)
            stmt = stmt.order_by(TaskModel.created_at.desc())
            db_tasks = session.execute(stmt).scalars().all()
            return [t.to_domain() for t in db_tasks]

    def delete(self, task_id: int) -> bool:
        with self._session_factory() as session, session.begin():
            db_task = session.get(TaskModel, task_id)
            if db_task:
                session.delete(db_task)
                return True
            return False
