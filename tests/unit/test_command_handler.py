"""Unit tests for the non-interactive CLI / Agent command handler."""

import json
from datetime import UTC, datetime, timedelta

from todo.application.services import TaskService, UserService
from todo.infrastructure.memory_repos import InMemoryTaskRepository, InMemoryUserRepository
from todo.presentation.command_handler import parse_date, parse_priority, run_command


def setup_services():
    user_repo = InMemoryUserRepository()
    task_repo = InMemoryTaskRepository()
    user_service = UserService(user_repo=user_repo)
    task_service = TaskService(task_repo=task_repo, user_repo=user_repo)
    return user_service, task_service


def test_parse_date():
    dt1 = parse_date("2026-10-18")
    assert dt1 is not None and dt1.year == 2026 and dt1.month == 10 and dt1.day == 18

    dt2 = parse_date("10/18/2026")
    assert dt2 is not None and dt2.year == 2026 and dt2.month == 10 and dt2.day == 18

    assert parse_date(None) is None


def test_parse_priority():
    assert parse_priority("urgent").value == "URGENT"
    assert parse_priority("LOW").value == "LOW"
    assert parse_priority(None) is None


def test_users_add_and_list_json(capsys):
    user_service, task_service = setup_services()

    # Add user
    code = run_command(
        [
            "users",
            "add",
            "--first",
            "Ada",
            "--last",
            "Lovelace",
            "--email",
            "ada@example.com",
            "--json",
        ],
        user_service,
        task_service,
    )
    assert code == 0
    captured = capsys.readouterr().out
    data = json.loads(captured)
    assert data["status"] == "success"
    assert data["data"]["email"] == "ada@example.com"
    assert data["data"]["id"] == 1

    # List users
    code = run_command(["users", "list", "--json"], user_service, task_service)
    assert code == 0
    captured = capsys.readouterr().out
    data = json.loads(captured)
    assert data["status"] == "success"
    assert len(data["data"]) == 1


def test_tasks_crud_lifecycle_json(capsys):
    user_service, task_service = setup_services()
    user_service.register_user("Ada", "Lovelace", "ada@example.com")

    # Add task with MM/DD/YYYY date and priority
    code = run_command(
        [
            "tasks",
            "add",
            "--title",
            "Publish clean arch",
            "--due",
            "10/18/2026",
            "--priority",
            "urgent",
            "--json",
        ],
        user_service,
        task_service,
    )
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "success"
    task_id = out["data"]["id"]
    assert task_id == 1
    assert out["data"]["priority"] == "URGENT"
    assert out["data"]["status"] == "PENDING"

    # Complete task
    code = run_command(["tasks", "complete", str(task_id), "--json"], user_service, task_service)
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["data"]["status"] == "COMPLETED"
    assert out["data"]["is_completed"] is True

    # Reopen task
    code = run_command(["tasks", "reopen", str(task_id), "--json"], user_service, task_service)
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["data"]["status"] == "PENDING"

    # List tasks with priority filter
    code = run_command(
        ["tasks", "list", "--status", "pending", "--priority", "urgent", "--json"],
        user_service,
        task_service,
    )
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert len(out["data"]) == 1

    # Delete task
    code = run_command(["tasks", "delete", str(task_id), "--json"], user_service, task_service)
    assert code == 0
    del_out = json.loads(capsys.readouterr().out)
    assert del_out["status"] == "success"

    # Verify task deleted
    code = run_command(["tasks", "complete", str(task_id), "--json"], user_service, task_service)
    assert code == 1
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "error"


def test_tasks_overdue_cli_filter(capsys):
    user_service, task_service = setup_services()
    user = user_service.register_user("Ada", "Lovelace", "ada@example.com")

    task_service.create_task(
        user_id=user.id, title="Past task", due_date=datetime.now(UTC) - timedelta(days=5)
    )

    code = run_command(["tasks", "list", "--overdue", "--json"], user_service, task_service)
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert len(out["data"]) == 1
    assert out["data"][0]["is_overdue"] is True
