"""Main application entrypoint and Composition Root.

Wires infrastructure, application use cases, and presentation layers.
Supports both interactive CLI for humans and non-interactive/JSON commands for AI agents.
"""

import sys
from pathlib import Path

# Ensure src/ is on python search path when running `python app.py`
SRC_DIR = Path(__file__).resolve().parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from todo.application.services import TaskService, UserService
from todo.infrastructure.ai.ollama_embedder import OllamaTaskEmbedder
from todo.infrastructure.db import build_engine, build_session_factory, init_database
from todo.infrastructure.sqlite_repos import (
    SqlAlchemyTaskRepository,
    SqlAlchemyTaskVectorRepository,
    SqlAlchemyUserRepository,
)
from todo.presentation.cli import TodoCLI
from todo.presentation.command_handler import run_command


def bootstrap_services() -> tuple[UserService, TaskService]:
    """Composition Root: Wire domain, infrastructure, and application services."""
    # 1. Infrastructure setup
    engine = build_engine("sqlite:///todo.db")
    init_database(engine)
    session_factory = build_session_factory(engine)

    # 2. Concrete Repositories & Adapters
    user_repo = SqlAlchemyUserRepository(session_factory)
    task_repo = SqlAlchemyTaskRepository(session_factory)
    vector_repo = SqlAlchemyTaskVectorRepository(session_factory)
    embedder = OllamaTaskEmbedder(model="all-minilm")

    # 3. Application Services (Use Cases)
    user_service = UserService(user_repo=user_repo)
    task_service = TaskService(
        task_repo=task_repo,
        user_repo=user_repo,
        vector_repo=vector_repo,
        embedding_port=embedder,
    )

    return user_service, task_service


def bootstrap() -> TodoCLI:
    """Convenience helper returning the interactive CLI."""
    user_service, task_service = bootstrap_services()
    return TodoCLI(user_service=user_service, task_service=task_service)


def main() -> None:
    """Application main entrypoint."""
    user_service, task_service = bootstrap_services()
    if len(sys.argv) > 1:
        sys.exit(run_command(sys.argv[1:], user_service, task_service))
    else:
        cli = TodoCLI(user_service=user_service, task_service=task_service)
        cli.run()


if __name__ == "__main__":
    main()
