"""Unit tests for Domain Models."""
from datetime import UTC, datetime, timedelta

import pytest

from todo.domain.exceptions import ValidationError
from todo.domain.models import Priority, Task, TaskStatus, User


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
    task = Task(user_id=1, title=" Buy milk ", description="2% milk", priority=Priority.HIGH)
    assert task.title == "Buy milk"
    assert task.description == "2% milk"
    assert task.priority == Priority.HIGH
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


def test_task_overdue_and_due_today():
    now = datetime.now(UTC)
    yesterday = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

    overdue_task = Task(user_id=1, title="Overdue task", due_date=yesterday)
    assert overdue_task.is_overdue
    assert not overdue_task.is_due_today

    # Completed task should not be overdue
    overdue_task.complete()
    assert not overdue_task.is_overdue

    today_task = Task(user_id=1, title="Today task", due_date=today)
    assert today_task.is_due_today
    assert not today_task.is_overdue

    future_task = Task(user_id=1, title="Future task", due_date=tomorrow)
    assert not future_task.is_overdue
    assert not future_task.is_due_today

    no_due_date_task = Task(user_id=1, title="No due date")
    assert not no_due_date_task.is_overdue
    assert not no_due_date_task.is_due_today
