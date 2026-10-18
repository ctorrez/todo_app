"""Unit tests for Domain Models."""
import pytest

from todo.domain.exceptions import ValidationError
from todo.domain.models import Task, TaskStatus, User


def test_user_creation_valid():
    user = User(first_name=" Alice ", last_name=" Smith ", email=" Alice@Example.com ")
    assert user.first_name == "Alice"
    assert user.last_name == "Smith"
    assert user.email == "alice@example.com"
    assert user.full_name == "Alice Smith"
    assert user.id is None


@pytest.mark.parametrize(
    "first,last,email",
    [
        ("", "Smith", "alice@example.com"),
        ("Alice", "", "alice@example.com"),
        ("Alice", "Smith", ""),
        ("Alice", "Smith", "invalid-email"),
        ("Alice", "Smith", "alice@"),
    ],
)
def test_user_validation_failures(first: str, last: str, email: str):
    with pytest.raises(ValidationError):
        User(first_name=first, last_name=last, email=email)


def test_task_creation_and_state_transitions():
    task = Task(user_id=1, title=" Buy milk ", description="2% milk")
    assert task.title == "Buy milk"
    assert task.description == "2% milk"
    assert task.status == TaskStatus.PENDING
    assert not task.is_completed
    assert task.completed_at is None

    # Complete task
    task.complete()
    assert task.is_completed
    assert task.status == TaskStatus.COMPLETED
    assert task.completed_at is not None

    # Reopen task
    task.reopen()
    assert not task.is_completed
    assert task.status == TaskStatus.PENDING
    assert task.completed_at is None


def test_task_empty_title_raises_validation_error():
    with pytest.raises(ValidationError):
        Task(user_id=1, title="   ")
