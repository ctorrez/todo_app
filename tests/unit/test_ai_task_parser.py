"""Unit tests for AI natural language task parsing and ports."""
import json
from datetime import UTC, datetime

import pytest

from todo.application.services import TaskService, UserService
from todo.domain.exceptions import TodoDomainError
from todo.domain.models import Priority
from todo.infrastructure.ai.mock_parser import MockTaskParser
from todo.infrastructure.ai.ollama_parser import OllamaTaskParser
from todo.infrastructure.memory_repos import InMemoryTaskRepository, InMemoryUserRepository
from todo.presentation.command_handler import run_command


def setup_services():
    user_repo = InMemoryUserRepository()
    task_repo = InMemoryTaskRepository()
    user_service = UserService(user_repo=user_repo)
    task_service = TaskService(task_repo=task_repo, user_repo=user_repo)
    return user_service, task_service


def test_mock_task_parser_urgency():
    parser = MockTaskParser()
    ref = datetime(2026, 10, 19, tzinfo=UTC)

    parsed = parser.parse("Urgent: finish tax return", reference_date=ref)
    assert parsed.title == "finish tax return"
    assert parsed.priority == Priority.URGENT
    assert parsed.due_date == ref

    parsed_normal = parser.parse("Buy groceries")
    assert parsed_normal.title == "Buy groceries"
    assert parsed_normal.priority == Priority.MEDIUM


def test_task_service_create_from_text():
    user_service, task_service = setup_services()
    user = user_service.register_user("Ada", "Lovelace", "ada@example.com")
    parser = MockTaskParser()

    task = task_service.create_task_from_text(
        user_id=user.id,
        text="Urgent meeting with client",
        parser=parser,
    )
    assert task.id == 1
    assert task.title == "meeting with client"
    assert task.priority == Priority.URGENT


def test_cli_ai_add_and_parse_with_mock(capsys):
    user_service, task_service = setup_services()
    user_service.register_user("Ada", "Lovelace", "ada@example.com")
    parser = MockTaskParser()

    # Test ai parse
    code = run_command(
        ["ai", "parse", "Important finish dissertation", "--json"],
        user_service,
        task_service,
        parser_override=parser,
    )
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "success"
    assert out["data"]["priority"] == "HIGH"
    assert out["data"]["title"] == "finish dissertation"

    # Test ai add
    code = run_command(
        ["ai", "add", "Urgent deploy new release", "--json"],
        user_service,
        task_service,
        parser_override=parser,
    )
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "success"
    assert out["data"]["priority"] == "URGENT"
    assert out["data"]["title"] == "deploy new release"


def test_ollama_parser_unreachable_raises_domain_error():
    # Point to an invalid local port to verify graceful error handling
    parser = OllamaTaskParser(base_url="http://localhost:59999", timeout=0.5)
    with pytest.raises(TodoDomainError) as exc_info:
        parser.parse("Call doctor tomorrow")
    assert "Could not connect to local Ollama" in str(exc_info.value)
