from datetime import datetime

from todo.application.ports import (
    TaskEmbeddingPort,
    TaskParserPort,
    TaskRepository,
    TaskVectorRepository,
    UserRepository,
    Vector,
)
from todo.domain.exceptions import (
    TaskNotFoundError,
    TodoDomainError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from todo.domain.models import Priority, ScoredTask, Task, TaskStatus, User


class UserService:
    """Use cases related to User management."""

    def __init__(self, user_repo: UserRepository) -> None:
        self._user_repo = user_repo

    def register_user(self, first_name: str, last_name: str, email: str) -> User:
        """Register a new user after verifying email uniqueness."""
        email_clean = email.strip().lower()
        existing = self._user_repo.get_by_email(email_clean)
        if existing:
            raise UserAlreadyExistsError(f"User with email '{email_clean}' already exists.")

        user = User(first_name=first_name, last_name=last_name, email=email_clean)
        return self._user_repo.save(user)

    def get_user(self, user_id: int) -> User:
        """Retrieve user by ID or raise UserNotFoundError."""
        user = self._user_repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundError(f"User with ID {user_id} was not found.")
        return user

    def list_users(self) -> list[User]:
        """Return all registered users."""
        return self._user_repo.list_all()

    def has_users(self) -> bool:
        """Check if any users exist in the system."""
        return self._user_repo.count() > 0


class TaskService:
    """Use cases related to Task management."""

    def __init__(
        self,
        task_repo: TaskRepository,
        user_repo: UserRepository,
        vector_repo: TaskVectorRepository | None = None,
        embedding_port: TaskEmbeddingPort | None = None,
    ) -> None:
        self._task_repo = task_repo
        self._user_repo = user_repo
        self._vector_repo = vector_repo
        self._embedding_port = embedding_port

    def create_task(
        self,
        user_id: int,
        title: str,
        description: str = "",
        due_date: datetime | None = None,
        priority: Priority = Priority.MEDIUM,
    ) -> Task:
        """Create a new task for an existing user."""
        user = self._user_repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundError(f"Cannot create task: User {user_id} does not exist.")

        task = Task(
            user_id=user_id,
            title=title,
            description=description,
            due_date=due_date,
            priority=priority,
        )
        saved = self._task_repo.save(task)
        if self._vector_repo and self._embedding_port and saved.id is not None:
            try:
                vec = self._embedding_port.embed_text(saved.to_search_text())
                self._vector_repo.upsert_vector(saved.id, saved.user_id, vec)
            except (TodoDomainError, OSError, RuntimeError):
                # Do not block task creation if optional vector indexing encounters a transient error
                pass
        return saved

    def create_task_from_text(
        self,
        user_id: int,
        text: str,
        parser: TaskParserPort,
        reference_date: datetime | None = None,
    ) -> Task:
        """Create a task by parsing natural language using a TaskParserPort."""
        parsed = parser.parse(text, reference_date=reference_date)
        return self.create_task(
            user_id=user_id,
            title=parsed.title,
            description=parsed.description,
            due_date=parsed.due_date,
            priority=parsed.priority,
        )

    def get_task(self, task_id: int) -> Task:
        """Retrieve task by ID or raise TaskNotFoundError."""
        task = self._task_repo.get_by_id(task_id)
        if not task:
            raise TaskNotFoundError(f"Task with ID {task_id} was not found.")
        return task

    def list_tasks(
        self,
        user_id: int,
        status: TaskStatus | None = None,
        priority: Priority | None = None,
        overdue_only: bool = False,
        due_today_only: bool = False,
    ) -> list[Task]:
        """List tasks belonging to a user, optionally filtered."""
        user = self._user_repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundError(f"Cannot list tasks: User {user_id} does not exist.")
        return self._task_repo.list_by_user(
            user_id=user_id,
            status=status,
            priority=priority,
            overdue_only=overdue_only,
            due_today_only=due_today_only,
        )

    def complete_task(self, task_id: int) -> Task:
        """Mark a task as completed."""
        task = self.get_task(task_id)
        task.complete()
        return self._task_repo.save(task)

    def reopen_task(self, task_id: int) -> Task:
        """Reopen a completed task."""
        task = self.get_task(task_id)
        task.reopen()
        return self._task_repo.save(task)

    def delete_task(self, task_id: int) -> None:
        """Delete a task by ID."""
        deleted = self._task_repo.delete(task_id)
        if not deleted:
            raise TaskNotFoundError(f"Cannot delete: Task with ID {task_id} was not found.")
        if self._vector_repo:
            self._vector_repo.delete_vector(task_id)

    def search_tasks_semantic(
        self,
        user_id: int,
        query: str,
        limit: int = 5,
        threshold: float = 0.15,
    ) -> list[ScoredTask]:
        """Perform semantic search across user tasks using vector embeddings."""
        user = self._user_repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundError(f"Cannot search tasks: User {user_id} does not exist.")

        if not self._vector_repo or not self._embedding_port:
            raise TodoDomainError(
                "Semantic search is not enabled (missing vector store or embedder)."
            )

        query_clean = query.strip()
        if not query_clean:
            return []

        query_vec = self._embedding_port.embed_text(query_clean)
        matches = self._vector_repo.search_similar(
            query_vector=query_vec,
            user_id=user_id,
            limit=limit,
            threshold=threshold,
        )

        results: list[ScoredTask] = []
        for task_id, score in matches:
            task = self._task_repo.get_by_id(task_id)
            if task:
                results.append(ScoredTask(task=task, score=score))
        return results

    def reindex_user_tasks(self, user_id: int) -> int:
        """Backfill / re-index all tasks for a user in the vector repository."""
        user = self._user_repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundError(f"Cannot reindex: User {user_id} does not exist.")

        if not self._vector_repo or not self._embedding_port:
            raise TodoDomainError("Cannot reindex: Vector store or embedder not configured.")

        tasks = self._task_repo.list_by_user(user_id)
        if not tasks:
            return 0

        valid_tasks = [t for t in tasks if t.id is not None]
        texts = [t.to_search_text() for t in valid_tasks]
        vectors = self._embedding_port.embed_batch(texts)

        items: list[tuple[int, int, Vector]] = []
        for t, vec in zip(valid_tasks, vectors, strict=True):
            if t.id is not None:
                items.append((t.id, t.user_id, vec))

        self._vector_repo.upsert_batch(items)
        return len(items)
