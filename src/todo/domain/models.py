"""Domain models (Entities and Value Objects) for the Todo App."""
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum

from todo.domain.exceptions import ValidationError

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"


class Priority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"


@dataclass
class User:
    """User entity."""
    first_name: str
    last_name: str
    email: str
    id: int | None = None

    def __post_init__(self) -> None:
        self.first_name = self.first_name.strip()
        self.last_name = self.last_name.strip()
        self.email = self.email.strip().lower()

        if not self.first_name:
            raise ValidationError("First name cannot be empty.")
        if not self.last_name:
            raise ValidationError("Last name cannot be empty.")
        if not self.email or not EMAIL_REGEX.match(self.email):
            raise ValidationError(f"Invalid email address: '{self.email}'.")

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


@dataclass
class Task:
    """Task entity representing a todo item belonging to a User."""
    user_id: int
    title: str
    description: str = ""
    due_date: datetime | None = None
    priority: Priority = Priority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING
    id: int | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None

    def __post_init__(self) -> None:
        self.title = self.title.strip()
        self.description = self.description.strip()
        if not self.title:
            raise ValidationError("Task title cannot be empty.")

    @property
    def is_completed(self) -> bool:
        return self.status == TaskStatus.COMPLETED

    @property
    def is_overdue(self) -> bool:
        """Return True if pending and due date has passed.

        If due_date is date-only (00:00:00), it is overdue after the due day has ended.
        """
        if self.is_completed or self.due_date is None:
            return False
        now_utc = datetime.now(UTC)
        due_utc = self.due_date if self.due_date.tzinfo else self.due_date.replace(tzinfo=UTC)
        if due_utc.hour == 0 and due_utc.minute == 0 and due_utc.second == 0 and due_utc.microsecond == 0:
            return due_utc.date() < now_utc.date()
        return due_utc < now_utc

    @property
    def is_due_today(self) -> bool:
        """Return True if pending and due date matches today (UTC)."""
        if self.is_completed or self.due_date is None:
            return False
        now_date = datetime.now(UTC).date()
        due_date = self.due_date.date()
        return due_date == now_date

    def complete(self, at: datetime | None = None) -> None:
        """Mark task as completed."""
        self.status = TaskStatus.COMPLETED
        self.completed_at = at or datetime.now(UTC)

    def reopen(self) -> None:
        """Reopen task back to pending."""
        self.status = TaskStatus.PENDING
        self.completed_at = None
