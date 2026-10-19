"""Integration tests for SqlAlchemyTaskVectorRepository against SQLite."""

import numpy as np
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from todo.domain.models import Task, User
from todo.infrastructure.db import Base
from todo.infrastructure.sqlite_repos import (
    SqlAlchemyTaskRepository,
    SqlAlchemyTaskVectorRepository,
    SqlAlchemyUserRepository,
)


@pytest.fixture
def session_factory():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    yield factory
    engine.dispose()


def test_sqlite_vector_repository_upsert_and_search(session_factory):
    user_repo = SqlAlchemyUserRepository(session_factory)
    task_repo = SqlAlchemyTaskRepository(session_factory)
    vector_repo = SqlAlchemyTaskVectorRepository(session_factory)

    user = user_repo.save(User(first_name="Ada", last_name="Lovelace", email="ada@example.com"))
    assert user.id is not None

    t1 = task_repo.save(Task(user_id=user.id, title="Dentist visit"))
    t2 = task_repo.save(Task(user_id=user.id, title="Buy milk"))
    assert t1.id is not None and t2.id is not None

    v1 = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)
    v2 = np.array([0.0, 1.0, 0.0, 0.0], dtype=np.float32)

    vector_repo.upsert_vector(task_id=t1.id, user_id=user.id, vector=v1)
    vector_repo.upsert_vector(task_id=t2.id, user_id=user.id, vector=v2)

    # Search for v1
    results = vector_repo.search_similar(query_vector=v1, user_id=user.id, limit=5, threshold=0.5)
    assert len(results) == 1
    assert results[0][0] == t1.id
    assert pytest.approx(results[0][1], abs=1e-5) == 1.0

    # Batch upsert overwrite
    v1_updated = np.array([0.0, 0.0, 1.0, 0.0], dtype=np.float32)
    vector_repo.upsert_batch([(t1.id, user.id, v1_updated)])
    results_after_update = vector_repo.search_similar(
        query_vector=v1, user_id=user.id, limit=5, threshold=0.5
    )
    assert len(results_after_update) == 0

    # Delete vector
    vector_repo.delete_vector(t1.id)
    vector_repo.delete_vector(t2.id)
    assert (
        len(vector_repo.search_similar(query_vector=v2, user_id=user.id, limit=5, threshold=0.0))
        == 0
    )


def test_sqlite_vector_repository_user_isolation(session_factory):
    user_repo = SqlAlchemyUserRepository(session_factory)
    task_repo = SqlAlchemyTaskRepository(session_factory)
    vector_repo = SqlAlchemyTaskVectorRepository(session_factory)

    u1 = user_repo.save(User(first_name="User", last_name="One", email="u1@example.com"))
    u2 = user_repo.save(User(first_name="User", last_name="Two", email="u2@example.com"))
    assert u1.id is not None and u2.id is not None

    t1 = task_repo.save(Task(user_id=u1.id, title="U1 Secret Task"))
    assert t1.id is not None

    v = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)
    vector_repo.upsert_vector(task_id=t1.id, user_id=u1.id, vector=v)

    # U1 can find it
    assert (
        len(vector_repo.search_similar(query_vector=v, user_id=u1.id, limit=5, threshold=0.5)) == 1
    )

    # U2 cannot find it (isolated)
    assert (
        len(vector_repo.search_similar(query_vector=v, user_id=u2.id, limit=5, threshold=0.0)) == 0
    )
