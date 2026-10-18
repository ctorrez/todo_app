"""Unit tests for TaskService using InMemory repositories."""
import pytest

from todo.application.services import TaskService, UserService
from todo.domain.exceptions import TaskNotFoundError, UserNotFoundError
from todo.domain.models import TaskStatus
from todo.infrastructure.memory_repos import InMemoryTaskRepository, InMemoryUserRepository


@pytest.fixture
def services():
    user_repo = InMemoryUserRepository()
    task_repo = InMemoryTaskRepository()
    user_service = UserService(user_repo=user_repo)
    task_service = TaskService(task_repo=task_repo, user_repo=user_repo)
    return user_service, task_service


def test_create_task_success(services):
    user_service, task_service = services
    user = user_service.register_user("Alice", "Smith", "alice@example.com")

    task = task_service.create_task(
        user_id=user.id,
        title="Write tests",
        description="Verify clean seams",
    )
    assert task.id == 1
    assert task.user_id == user.id
    assert task.title == "Write tests"
    assert task.status == TaskStatus.PENDING


def test_create_task_user_not_found(services):
    _, task_service = services
    with pytest.raises(UserNotFoundError):
        task_service.create_task(user_id=999, title="Invalid User Task")


def test_complete_and_reopen_task(services):
    user_service, task_service = services
    user = user_service.register_user("Alice", "Smith", "alice@example.com")
    task = task_service.create_task(user_id=user.id, title="Refactor code")

    completed = task_service.complete_task(task.id)
    assert completed.is_completed
    assert completed.status == TaskStatus.COMPLETED

    reopened = task_service.reopen_task(task.id)
    assert not reopened.is_completed
    assert reopened.status == TaskStatus.PENDING


def test_list_tasks_filtering(services):
    user_service, task_service = services
    user = user_service.register_user("Alice", "Smith", "alice@example.com")

    t1 = task_service.create_task(user_id=user.id, title="Task 1")
    t2 = task_service.create_task(user_id=user.id, title="Task 2")
    task_service.complete_task(t1.id)

    all_tasks = task_service.list_tasks(user_id=user.id)
    pending_tasks = task_service.list_tasks(user_id=user.id, status=TaskStatus.PENDING)
    completed_tasks = task_service.list_tasks(user_id=user.id, status=TaskStatus.COMPLETED)

    assert len(all_tasks) == 2
    assert len(pending_tasks) == 1
    assert pending_tasks[0].id == t2.id
    assert len(completed_tasks) == 1
    assert completed_tasks[0].id == t1.id


def test_delete_task(services):
    user_service, task_service = services
    user = user_service.register_user("Alice", "Smith", "alice@example.com")
    task = task_service.create_task(user_id=user.id, title="To be deleted")

    task_service.delete_task(task.id)

    with pytest.raises(TaskNotFoundError):
        task_service.get_task(task.id)


def test_delete_nonexistent_task_raises_error(services):
    _, task_service = services
    with pytest.raises(TaskNotFoundError):
        task_service.delete_task(999)
