"""SQLAlchemy database models and session setup."""

from datetime import UTC, datetime

from sqlalchemy import DateTime, Engine, ForeignKey, Integer, LargeBinary, String, create_engine
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    relationship,
    sessionmaker,
)

from todo.domain.models import Priority, Task, TaskStatus, User


class Base(DeclarativeBase):
    pass


class UserModel(Base):
    """SQLAlchemy model for users table."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    first_name: Mapped[str] = mapped_column(String(50), nullable=False)
    last_name: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    tasks: Mapped[list["TaskModel"]] = relationship(
        "TaskModel", back_populates="user", cascade="all, delete-orphan"
    )

    def to_domain(self) -> User:
        return User(
            id=self.id,
            first_name=self.first_name,
            last_name=self.last_name,
            email=self.email,
        )

    @classmethod
    def from_domain(cls, user: User) -> "UserModel":
        return cls(
            id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email,
        )


class TaskModel(Base):
    """SQLAlchemy model for tasks table."""

    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), default="", nullable=False)
    due_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    priority: Mapped[str] = mapped_column(String(20), default=Priority.MEDIUM.value, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default=TaskStatus.PENDING.value, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped[UserModel] = relationship("UserModel", back_populates="tasks")

    def to_domain(self) -> Task:
        return Task(
            id=self.id,
            user_id=self.user_id,
            title=self.title,
            description=self.description,
            due_date=self.due_date,
            priority=Priority(self.priority),
            status=TaskStatus(self.status),
            created_at=self.created_at,
            completed_at=self.completed_at,
        )

    @classmethod
    def from_domain(cls, task: Task) -> "TaskModel":
        return cls(
            id=task.id,
            user_id=task.user_id,
            title=task.title,
            description=task.description,
            due_date=task.due_date,
            priority=task.priority.value,
            status=task.status.value,
            created_at=task.created_at,
            completed_at=task.completed_at,
        )


class TaskEmbeddingModel(Base):
    """SQLAlchemy model for task_embeddings table."""

    __tablename__ = "task_embeddings"

    task_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    vector_data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    dimensions: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), nullable=False
    )


def build_engine(database_url: str = "sqlite:///todo.db", echo: bool = False) -> Engine:
    """Build SQLAlchemy engine."""
    return create_engine(database_url, echo=echo)


def build_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Build sessionmaker bound to engine."""
    return sessionmaker(bind=engine, expire_on_commit=False)


def init_database(engine: Engine) -> None:
    """Create all tables in database if not present."""
    Base.metadata.create_all(engine)
