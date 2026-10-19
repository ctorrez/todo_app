"""Unit tests for semantic vector search and ports."""

import numpy as np
import pytest

from todo.application.services import TaskService, UserService
from todo.domain.exceptions import TodoDomainError
from todo.infrastructure.ai.mock_embedder import MockTaskEmbedder
from todo.infrastructure.memory_repos import (
    InMemoryTaskRepository,
    InMemoryTaskVectorRepository,
    InMemoryUserRepository,
)


@pytest.fixture
def user_repo() -> InMemoryUserRepository:
    return InMemoryUserRepository()


@pytest.fixture
def task_repo() -> InMemoryTaskRepository:
    return InMemoryTaskRepository()


@pytest.fixture
def vector_repo() -> InMemoryTaskVectorRepository:
    return InMemoryTaskVectorRepository()


@pytest.fixture
def embedder() -> MockTaskEmbedder:
    return MockTaskEmbedder(dimensions=16)


@pytest.fixture
def services(
    user_repo: InMemoryUserRepository,
    task_repo: InMemoryTaskRepository,
    vector_repo: InMemoryTaskVectorRepository,
    embedder: MockTaskEmbedder,
) -> tuple[UserService, TaskService]:
    user_service = UserService(user_repo=user_repo)
    task_service = TaskService(
        task_repo=task_repo,
        user_repo=user_repo,
        vector_repo=vector_repo,
        embedding_port=embedder,
    )
    return user_service, task_service


def test_mock_embedder_generates_normalized_vectors(embedder: MockTaskEmbedder) -> None:
    vec = embedder.embed_text("Doctor visit")
    assert vec.shape == (16,)
    assert vec.dtype == np.float32
    assert pytest.approx(float(np.linalg.norm(vec)), abs=1e-5) == 1.0


def test_mock_embedder_batch(embedder: MockTaskEmbedder) -> None:
    vecs = embedder.embed_batch(["Task 1", "Task 2"])
    assert len(vecs) == 2
    for v in vecs:
        assert v.shape == (16,)
        assert pytest.approx(float(np.linalg.norm(v)), abs=1e-5) == 1.0


def test_in_memory_vector_repo_crud(vector_repo: InMemoryTaskVectorRepository) -> None:
    v1 = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)
    v2 = np.array([0.0, 1.0, 0.0, 0.0], dtype=np.float32)

    vector_repo.upsert_vector(task_id=1, user_id=10, vector=v1)
    vector_repo.upsert_vector(task_id=2, user_id=10, vector=v2)

    # Search with v1 exact match
    results = vector_repo.search_similar(query_vector=v1, user_id=10, limit=5, threshold=0.5)
    assert len(results) == 1
    assert results[0][0] == 1
    assert pytest.approx(results[0][1], abs=1e-5) == 1.0

    # User isolation: user 20 should get 0 results
    res_user20 = vector_repo.search_similar(query_vector=v1, user_id=20, limit=5, threshold=0.0)
    assert len(res_user20) == 0

    # Delete
    vector_repo.delete_vector(task_id=1)
    results_after_del = vector_repo.search_similar(
        query_vector=v1, user_id=10, limit=5, threshold=0.5
    )
    assert len(results_after_del) == 0


def test_task_creation_auto_indexes_vector(
    services: tuple[UserService, TaskService],
    vector_repo: InMemoryTaskVectorRepository,
) -> None:
    user_service, task_service = services
    user = user_service.register_user("Marie", "Curie", "marie@example.com")
    assert user.id is not None

    task = task_service.create_task(
        user_id=user.id,
        title="Schedule radiation lab tests",
        description="Verify isotope containment",
    )
    assert task.id is not None

    # Vector should have been automatically indexed
    assert task.id in vector_repo._vectors


def test_semantic_search_ranks_relevant_tasks(
    services: tuple[UserService, TaskService],
) -> None:
    user_service, task_service = services
    user = user_service.register_user("Ada", "Lovelace", "ada@example.com")
    assert user.id is not None

    t1 = task_service.create_task(user_id=user.id, title="Dentist appointment tomorrow")
    task_service.create_task(user_id=user.id, title="Buy groceries at supermarket")

    results = task_service.search_tasks_semantic(
        user_id=user.id,
        query="Dentist appointment",
        limit=5,
        threshold=0.3,
    )
    assert len(results) >= 1
    assert results[0].task.id == t1.id
    assert results[0].score > 0.5


def test_task_deletion_removes_vector(
    services: tuple[UserService, TaskService],
    vector_repo: InMemoryTaskVectorRepository,
) -> None:
    user_service, task_service = services
    user = user_service.register_user("Grace", "Hopper", "grace@example.com")
    assert user.id is not None

    task = task_service.create_task(user_id=user.id, title="Compiler optimization")
    assert task.id is not None
    assert task.id in vector_repo._vectors

    task_service.delete_task(task.id)
    assert task.id not in vector_repo._vectors


def test_reindex_user_tasks(
    services: tuple[UserService, TaskService],
    vector_repo: InMemoryTaskVectorRepository,
) -> None:
    user_service, task_service = services
    user = user_service.register_user("Alan", "Turing", "alan@example.com")
    assert user.id is not None

    task_service.create_task(user_id=user.id, title="Enigma decryption")
    task_service.create_task(user_id=user.id, title="Turing machine design")

    # Clear vectors
    vector_repo._vectors.clear()
    assert len(vector_repo._vectors) == 0

    count = task_service.reindex_user_tasks(user.id)
    assert count == 2
    assert len(vector_repo._vectors) == 2


def test_search_semantic_unconfigured_raises_domain_error(
    task_repo: InMemoryTaskRepository,
    user_repo: InMemoryUserRepository,
) -> None:
    # Service without vector_repo or embedding_port
    svc = TaskService(task_repo=task_repo, user_repo=user_repo)
    user_svc = UserService(user_repo=user_repo)
    user = user_svc.register_user("Test", "User", "test@example.com")
    assert user.id is not None

    with pytest.raises(TodoDomainError, match="Semantic search is not enabled"):
        svc.search_tasks_semantic(user_id=user.id, query="anything")
