"""Integration tests for SQLAlchemy repositories against SQLite."""
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from todo.domain.models import Priority, Task, TaskStatus, User
from todo.infrastructure.db import Base
from todo.infrastructure.sqlite_repos import SqlAlchemyTaskRepository, SqlAlchemyUserRepository


@pytest.fixture
def session_factory():
    # Use SQLite in-memory database for integration testing
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    yield factory
    engine.dispose()


def test_sqlalchemy_user_repository_crud(session_factory):
    repo = SqlAlchemyUserRepository(session_factory)
    assert repo.count() == 0

    user = User(first_name="Jane", last_name="Doe", email="jane@example.com")
    saved = repo.save(user)
    assert saved.id is not None
    assert saved.email == "jane@example.com"
    assert repo.count() == 1

    by_id = repo.get_by_id(saved.id)
    assert by_id is not None
    assert by_id.full_name == "Jane Doe"

    by_email = repo.get_by_email("jane@example.com")
    assert by_email is not None
    assert by_email.id == saved.id

    all_users = repo.list_all()
    assert len(all_users) == 1


def test_sqlalchemy_task_repository_crud_and_filter(session_factory):
    user_repo = SqlAlchemyUserRepository(session_factory)
    task_repo = SqlAlchemyTaskRepository(session_factory)

    user = user_repo.save(User(first_name="John", last_name="Doe", email="john@example.com"))

    now = datetime.now(UTC)
    yesterday = now - timedelta(days=2)

    task1 = task_repo.save(Task(user_id=user.id, title="Task 1", priority=Priority.LOW))
    task2 = task_repo.save(
        Task(user_id=user.id, title="Task 2", priority=Priority.URGENT, due_date=yesterday)
    )
    assert task1.id is not None
    assert task2.id is not None
    assert task2.priority == Priority.URGENT

    # Update task1 to completed
    task1.complete()
    task_repo.save(task1)

    # Filter by status
    all_tasks = task_repo.list_by_user(user.id)
    assert len(all_tasks) == 2

    completed = task_repo.list_by_user(user.id, status=TaskStatus.COMPLETED)
    assert len(completed) == 1
    assert completed[0].id == task1.id

    pending = task_repo.list_by_user(user.id, status=TaskStatus.PENDING)
    assert len(pending) == 1
    assert pending[0].id == task2.id

    # Filter by priority
    urgent_tasks = task_repo.list_by_user(user.id, priority=Priority.URGENT)
    assert len(urgent_tasks) == 1
    assert urgent_tasks[0].id == task2.id

    # Filter overdue
    overdue_tasks = task_repo.list_by_user(user.id, overdue_only=True)
    assert len(overdue_tasks) == 1
    assert overdue_tasks[0].id == task2.id

    # Delete
    deleted = task_repo.delete(task1.id)
    assert deleted is True
    assert task_repo.get_by_id(task1.id) is None
