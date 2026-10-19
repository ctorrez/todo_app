"""Non-interactive CLI and Agent command router with JSON support."""
import argparse
import json
import sys
from datetime import datetime
from typing import Any

from todo.application.ports import TaskParserPort
from todo.application.services import TaskService, UserService
from todo.domain.exceptions import TodoDomainError
from todo.domain.models import Priority, Task, TaskStatus, User
from todo.infrastructure.ai.ollama_parser import OllamaTaskParser


def parse_date(date_str: str | None) -> datetime | None:
    """Parse date from common formats."""
    if not date_str:
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    raise ValueError(f"Invalid date format '{date_str}'. Expected YYYY-MM-DD or MM/DD/YYYY.")


def parse_priority(priority_str: str | None) -> Priority | None:
    """Parse priority from case-insensitive string."""
    if not priority_str:
        return None
    try:
        return Priority(priority_str.strip().upper())
    except ValueError:
        raise ValueError(
            f"Invalid priority '{priority_str}'. Choose from: low, medium, high, urgent."
        )


def user_to_dict(user: User) -> dict[str, Any]:
    return {
        "id": user.id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "full_name": user.full_name,
    }


def task_to_dict(task: Task) -> dict[str, Any]:
    return {
        "id": task.id,
        "user_id": task.user_id,
        "title": task.title,
        "description": task.description,
        "priority": task.priority.value,
        "status": task.status.value,
        "is_completed": task.is_completed,
        "is_overdue": task.is_overdue,
        "is_due_today": task.is_due_today,
        "due_date": task.due_date.isoformat() if task.due_date else None,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
    }


def build_parser() -> argparse.ArgumentParser:
    """Build argument parser for non-interactive and agent usage."""
    parser = argparse.ArgumentParser(
        prog="python app.py",
        description="Clean Architecture Todo App - Command Line Interface for Humans & AI Agents",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # --- tasks subcommands ---
    tasks_parser = subparsers.add_parser("tasks", help="Manage tasks")
    tasks_sub = tasks_parser.add_subparsers(dest="subcommand", required=True)

    # tasks list
    t_list = tasks_sub.add_parser("list", help="List tasks")
    t_list.add_argument("--user-id", type=int, default=None, help="User ID (defaults to first user)")
    t_list.add_argument(
        "--status",
        choices=["all", "pending", "completed"],
        default="all",
        help="Filter by status (default: all)",
    )
    t_list.add_argument(
        "--priority",
        choices=["low", "medium", "high", "urgent"],
        default=None,
        help="Filter by priority (low, medium, high, urgent)",
    )
    t_list.add_argument("--overdue", action="store_true", help="Filter pending tasks that are overdue")
    t_list.add_argument("--due-today", action="store_true", help="Filter pending tasks due today")
    t_list.add_argument("--json", action="store_true", help="Output result as JSON")

    # tasks add
    t_add = tasks_sub.add_parser("add", help="Add a new task")
    t_add.add_argument("--title", required=True, help="Task title")
    t_add.add_argument("--desc", "--description", dest="desc", default="", help="Task description")
    t_add.add_argument("--due", default=None, help="Due date (YYYY-MM-DD or MM/DD/YYYY)")
    t_add.add_argument(
        "--priority",
        choices=["low", "medium", "high", "urgent"],
        default="medium",
        help="Task priority (default: medium)",
    )
    t_add.add_argument("--user-id", type=int, default=None, help="User ID (defaults to first user)")
    t_add.add_argument("--json", action="store_true", help="Output result as JSON")

    # tasks complete
    t_complete = tasks_sub.add_parser("complete", help="Mark a task as completed")
    t_complete.add_argument("task_id", type=int, help="Task ID")
    t_complete.add_argument("--json", action="store_true", help="Output result as JSON")

    # tasks reopen
    t_reopen = tasks_sub.add_parser("reopen", help="Reopen a completed task")
    t_reopen.add_argument("task_id", type=int, help="Task ID")
    t_reopen.add_argument("--json", action="store_true", help="Output result as JSON")

    # tasks delete
    t_del = tasks_sub.add_parser("delete", help="Delete a task")
    t_del.add_argument("task_id", type=int, help="Task ID")
    t_del.add_argument("--json", action="store_true", help="Output result as JSON")

    # --- users subcommands ---
    users_parser = subparsers.add_parser("users", help="Manage users")
    users_sub = users_parser.add_subparsers(dest="subcommand", required=True)

    # users list
    u_list = users_sub.add_parser("list", help="List users")
    u_list.add_argument("--json", action="store_true", help="Output result as JSON")

    # users add
    u_add = users_sub.add_parser("add", help="Register a new user")
    u_add.add_argument("--first", required=True, help="First name")
    u_add.add_argument("--last", required=True, help="Last name")
    u_add.add_argument("--email", required=True, help="Email address")
    u_add.add_argument("--json", action="store_true", help="Output result as JSON")

    # --- ai subcommands ---
    ai_parser = subparsers.add_parser("ai", help="AI-assisted features (natural language task ingestion)")
    ai_sub = ai_parser.add_subparsers(dest="subcommand", required=True)

    # ai add "Prompt"
    ai_add = ai_sub.add_parser("add", help="Add a task using natural language and local Ollama")
    ai_add.add_argument("prompt", help="Natural language description of the task")
    ai_add.add_argument("--user-id", type=int, default=None, help="User ID (defaults to first user)")
    ai_add.add_argument("--model", default="llama3.2:1b", help="Ollama model to use (default: llama3.2:1b)")
    ai_add.add_argument("--json", action="store_true", help="Output result as JSON")

    # ai parse "Prompt"
    ai_parse = ai_sub.add_parser("parse", help="Preview AI extraction without saving to database")
    ai_parse.add_argument("prompt", help="Natural language description of the task")
    ai_parse.add_argument("--model", default="llama3.2:1b", help="Ollama model to use (default: llama3.2:1b)")
    ai_parse.add_argument("--json", action="store_true", help="Output result as JSON")

    return parser


def run_command(
    argv: list[str],
    user_service: UserService,
    task_service: TaskService,
    parser_override: TaskParserPort | None = None,
) -> int:
    """Execute command line arguments. Returns exit code (0 success, 1 error)."""
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 1

    is_json = getattr(args, "json", False)

    try:
        if args.command == "users":
            return _handle_users_command(args, user_service, is_json)
        elif args.command == "tasks":
            return _handle_tasks_command(args, user_service, task_service, is_json)
        elif args.command == "ai":
            return _handle_ai_command(
                args, user_service, task_service, is_json, parser_override=parser_override
            )
        else:
            parser.print_help()
            return 1
    except (TodoDomainError, ValueError) as err:
        if is_json:
            print(json.dumps({"status": "error", "message": str(err)}, indent=2))
        else:
            print(f"Error: {err}", file=sys.stderr)
        return 1


def _resolve_user_id(requested_id: int | None, user_service: UserService) -> int:
    if requested_id is not None:
        return requested_id
    users = user_service.list_users()
    if not users or users[0].id is None:
        raise TodoDomainError("No registered users found. Please create a user first via 'users add'.")
    return users[0].id


def _handle_users_command(args: argparse.Namespace, user_service: UserService, is_json: bool) -> int:
    if args.subcommand == "list":
        users = user_service.list_users()
        if is_json:
            print(json.dumps({"status": "success", "data": [user_to_dict(u) for u in users]}, indent=2))
        else:
            if not users:
                print("No users found.")
            else:
                print("Registered Users:")
                for u in users:
                    print(f"  [{u.id}] {u.full_name} <{u.email}>")
        return 0

    elif args.subcommand == "add":
        user = user_service.register_user(args.first, args.last, args.email)
        if is_json:
            print(json.dumps({"status": "success", "data": user_to_dict(user)}, indent=2))
        else:
            print(f"User created successfully: {user.full_name} (ID: {user.id})")
        return 0

    return 1


def _handle_tasks_command(
    args: argparse.Namespace,
    user_service: UserService,
    task_service: TaskService,
    is_json: bool,
) -> int:
    if args.subcommand == "list":
        user_id = _resolve_user_id(args.user_id, user_service)
        status_filter: TaskStatus | None = None
        if args.status == "pending":
            status_filter = TaskStatus.PENDING
        elif args.status == "completed":
            status_filter = TaskStatus.COMPLETED

        priority_filter = parse_priority(args.priority)

        tasks = task_service.list_tasks(
            user_id=user_id,
            status=status_filter,
            priority=priority_filter,
            overdue_only=args.overdue,
            due_today_only=args.due_today,
        )
        if is_json:
            print(json.dumps({"status": "success", "data": [task_to_dict(t) for t in tasks]}, indent=2))
        else:
            if not tasks:
                print(f"No tasks found for user #{user_id}.")
            else:
                print(f"Tasks for User #{user_id}:")
                for t in tasks:
                    badge = "[X]" if t.is_completed else "[ ]"
                    prio_badge = f"[{t.priority.value}]"
                    due = f" (Due: {t.due_date.strftime('%Y-%m-%d')})" if t.due_date else ""
                    alert = " [OVERDUE!]" if t.is_overdue else (" [DUE TODAY]" if t.is_due_today else "")
                    print(f"  {badge} #{t.id} {prio_badge} - {t.title}{due}{alert}")
                    if t.description:
                        print(f"       {t.description}")
        return 0

    elif args.subcommand == "add":
        user_id = _resolve_user_id(args.user_id, user_service)
        due_date = parse_date(args.due)
        priority = parse_priority(args.priority) or Priority.MEDIUM
        task = task_service.create_task(
            user_id=user_id,
            title=args.title,
            description=args.desc,
            due_date=due_date,
            priority=priority,
        )
        if is_json:
            print(json.dumps({"status": "success", "data": task_to_dict(task)}, indent=2))
        else:
            print(f"Task created successfully: #{task.id} [{task.priority.value}] - {task.title}")
        return 0

    elif args.subcommand == "complete":
        task = task_service.complete_task(args.task_id)
        if is_json:
            print(json.dumps({"status": "success", "data": task_to_dict(task)}, indent=2))
        else:
            print(f"Task #{task.id} marked as COMPLETED.")
        return 0

    elif args.subcommand == "reopen":
        task = task_service.reopen_task(args.task_id)
        if is_json:
            print(json.dumps({"status": "success", "data": task_to_dict(task)}, indent=2))
        else:
            print(f"Task #{task.id} reopened to PENDING.")
        return 0

    elif args.subcommand == "delete":
        task_service.delete_task(args.task_id)
        if is_json:
            print(json.dumps({"status": "success", "data": {"deleted_id": args.task_id}}, indent=2))
        else:
            print(f"Task #{args.task_id} deleted successfully.")
        return 0

    return 1


def _handle_ai_command(
    args: argparse.Namespace,
    user_service: UserService,
    task_service: TaskService,
    is_json: bool,
    parser_override: TaskParserPort | None = None,
) -> int:
    parser = parser_override or OllamaTaskParser(model=args.model)

    if args.subcommand == "parse":
        parsed = parser.parse(args.prompt)
        data = {
            "title": parsed.title,
            "description": parsed.description,
            "due_date": parsed.due_date.isoformat() if parsed.due_date else None,
            "priority": parsed.priority.value,
        }
        if is_json:
            print(json.dumps({"status": "success", "data": data}, indent=2))
        else:
            print("AI Extracted Task Details (Preview - Not Saved):")
            print(f"  Title:       {parsed.title}")
            if parsed.description:
                print(f"  Description: {parsed.description}")
            due_str = parsed.due_date.strftime("%Y-%m-%d") if parsed.due_date else "None"
            print(f"  Due Date:    {due_str}")
            print(f"  Priority:    {parsed.priority.value}")
        return 0

    elif args.subcommand == "add":
        user_id = _resolve_user_id(args.user_id, user_service)
        task = task_service.create_task_from_text(
            user_id=user_id,
            text=args.prompt,
            parser=parser,
        )
        if is_json:
            print(json.dumps({"status": "success", "data": task_to_dict(task)}, indent=2))
        else:
            prio = f"[{task.priority.value}]"
            due = f" (Due: {task.due_date.strftime('%Y-%m-%d')})" if task.due_date else ""
            print(f"AI Task Created: #{task.id} {prio} - {task.title}{due}")
            if task.description:
                print(f"   Description: {task.description}")
        return 0

    return 1
