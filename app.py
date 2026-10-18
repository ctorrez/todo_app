"""Main application entrypoint and Composition Root.

Wires infrastructure, application use cases, and presentation layers.
"""
import sys
from pathlib import Path

# Ensure src/ is on python search path when running `python app.py`
SRC_DIR = Path(__file__).resolve().parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from todo.application.services import TaskService, UserService
from todo.infrastructure.db import build_engine, build_session_factory, init_database
from todo.infrastructure.sqlite_repos import SqlAlchemyTaskRepository, SqlAlchemyUserRepository
from todo.presentation.cli import TodoCLI


def bootstrap() -> TodoCLI:
    """Composition Root: Wire dependencies together."""
    # 1. Infrastructure setup
    engine = build_engine("sqlite:///todo.db")
    init_database(engine)
    session_factory = build_session_factory(engine)

    # 2. Concrete Repositories (Adapters)
    user_repo = SqlAlchemyUserRepository(session_factory)
    task_repo = SqlAlchemyTaskRepository(session_factory)

    # 3. Application Services (Use Cases)
    user_service = UserService(user_repo=user_repo)
    task_service = TaskService(task_repo=task_repo, user_repo=user_repo)

    # 4. Presentation
    return TodoCLI(user_service=user_service, task_service=task_service)


if __name__ == "__main__":
    cli = bootstrap()
    cli.run()