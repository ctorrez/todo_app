"""Interactive CLI presentation layer."""
import sys
from datetime import datetime

from todo.application.services import TaskService, UserService
from todo.domain.exceptions import TodoDomainError
from todo.domain.models import Priority, TaskStatus, User


class TodoCLI:
    """Console user interface for the Todo application."""

    def __init__(self, user_service: UserService, task_service: TaskService) -> None:
        self._user_service = user_service
        self._task_service = task_service
        self._current_user: User | None = None

    def run(self) -> None:
        """Main CLI loop."""
        print("=" * 45)
        print("       WELCOME TO CLEAN TODO APP")
        print("=" * 45)

        self._ensure_user()

        while True:
            self._display_menu()
            choice = input("\nSelect an option [1-8]: ").strip()
            print()

            if choice == "1":
                self._switch_user()
            elif choice == "2":
                self._register_user()
            elif choice == "3":
                self._list_tasks()
            elif choice == "4":
                self._create_task()
            elif choice == "5":
                self._complete_task()
            elif choice == "6":
                self._reopen_task()
            elif choice == "7":
                self._delete_task()
            elif choice == "8":
                print("Goodbye!")
                sys.exit(0)
            else:
                print("Invalid option. Please choose a number between 1 and 8.")

    def _ensure_user(self) -> None:
        """Prompt to create or select a user if none is active."""
        if not self._user_service.has_users():
            print("\nNo users found in the system. Let's register the first user:")
            self._register_user()
        else:
            self._switch_user()

    def _display_menu(self) -> None:
        user_display = (
            f"{self._current_user.full_name} (ID: {self._current_user.id})"
            if self._current_user
            else "None"
        )
        print("\n" + "-" * 45)
        print(f"Active User: {user_display}")
        print("-" * 45)
        print("1. Select / Switch User")
        print("2. Register New User")
        print("3. List Tasks (All / Pending / Completed / Overdue)")
        print("4. Add New Task")
        print("5. Mark Task as Completed")
        print("6. Reopen Completed Task")
        print("7. Delete Task")
        print("8. Exit")

    def _register_user(self) -> None:
        print("\n--- Register User ---")
        first_name = input("First Name: ").strip()
        last_name = input("Last Name: ").strip()
        email = input("Email: ").strip()

        try:
            user = self._user_service.register_user(first_name, last_name, email)
            print(f"User created successfully! Welcome, {user.full_name} (ID: {user.id})")
            self._current_user = user
        except TodoDomainError as err:
            print(f"Error: {err}")

    def _switch_user(self) -> None:
        users = self._user_service.list_users()
        if not users:
            print("No users available.")
            return

        print("\n--- Available Users ---")
        for u in users:
            print(f"  [{u.id}] {u.full_name} <{u.email}>")

        user_id = self._read_int("Enter user ID to select: ")
        if user_id is None:
            return

        try:
            self._current_user = self._user_service.get_user(user_id)
            print(f"Active user switched to: {self._current_user.full_name}")
        except TodoDomainError as err:
            print(f"Error: {err}")

    def _list_tasks(self) -> None:
        if not self._current_user or self._current_user.id is None:
            print("Please select a user first.")
            return

        print("\nFilter tasks:")
        print("1. All")
        print("2. Pending only")
        print("3. Completed only")
        print("4. Overdue only")
        print("5. Due today only")
        filter_choice = input("Choice [1-5, default=1]: ").strip()

        status: TaskStatus | None = None
        overdue_only = False
        due_today_only = False

        if filter_choice == "2":
            status = TaskStatus.PENDING
        elif filter_choice == "3":
            status = TaskStatus.COMPLETED
        elif filter_choice == "4":
            overdue_only = True
        elif filter_choice == "5":
            due_today_only = True

        try:
            tasks = self._task_service.list_tasks(
                self._current_user.id,
                status=status,
                overdue_only=overdue_only,
                due_today_only=due_today_only,
            )
            if not tasks:
                print("No tasks found matching criteria.")
                return

            print(f"\n--- Tasks ({len(tasks)}) ---")
            for t in tasks:
                badge = "[X]" if t.is_completed else "[ ]"
                prio_badge = f"[{t.priority.value}]"
                due = ""
                if t.due_date:
                    due_fmt = "%Y-%m-%d %H:%M" if (t.due_date.hour != 0 or t.due_date.minute != 0) else "%Y-%m-%d"
                    due = f" (Due: {t.due_date.strftime(due_fmt)})"
                alert = " [OVERDUE!]" if t.is_overdue else (" [DUE TODAY]" if t.is_due_today else "")
                print(f"  {badge} #{t.id} {prio_badge} - {t.title}{due}{alert}")
                if t.description:
                    print(f"       Description: {t.description}")
        except TodoDomainError as err:
            print(f"Error: {err}")

    def _create_task(self) -> None:
        if not self._current_user or self._current_user.id is None:
            print("Please select a user first.")
            return

        print("\n--- Add Task ---")
        title = input("Task Title: ").strip()
        description = input("Description (optional): ").strip()
        due_date_str = input("Due Date (YYYY-MM-DD [HH:MM] or MM/DD/YYYY [HH:MM], optional): ").strip()

        due_date: datetime | None = None
        if due_date_str:
            for fmt in (
                "%Y-%m-%d %H:%M",
                "%m/%d/%Y %H:%M",
                "%Y-%m-%d",
                "%m/%d/%Y",
                "%m-%d-%Y",
                "%Y/%m/%d",
            ):
                try:
                    due_date = datetime.strptime(due_date_str, fmt)
                    break
                except ValueError:
                    continue
            if due_date is None:
                print("Invalid date format. Expected YYYY-MM-DD [HH:MM] or MM/DD/YYYY [HH:MM].")
                return

        print("Priority: 1=Low, 2=Medium, 3=High, 4=Urgent [default: 2]")
        prio_choice = input("Choice [1-4]: ").strip()
        priority_map = {
            "1": Priority.LOW,
            "2": Priority.MEDIUM,
            "3": Priority.HIGH,
            "4": Priority.URGENT,
        }
        priority = priority_map.get(prio_choice, Priority.MEDIUM)

        try:
            task = self._task_service.create_task(
                user_id=self._current_user.id,
                title=title,
                description=description,
                due_date=due_date,
                priority=priority,
            )
            print(f"Task created successfully! (ID: #{task.id}, Priority: {task.priority.value})")
        except TodoDomainError as err:
            print(f"Error: {err}")

    def _complete_task(self) -> None:
        task_id = self._read_int("Enter Task ID to mark completed: ")
        if task_id is None:
            return

        try:
            task = self._task_service.complete_task(task_id)
            print(f"Task #{task.id} marked as COMPLETED!")
        except TodoDomainError as err:
            print(f"Error: {err}")

    def _reopen_task(self) -> None:
        task_id = self._read_int("Enter Task ID to reopen: ")
        if task_id is None:
            return

        try:
            task = self._task_service.reopen_task(task_id)
            print(f"Task #{task.id} reopened to PENDING.")
        except TodoDomainError as err:
            print(f"Error: {err}")

    def _delete_task(self) -> None:
        task_id = self._read_int("Enter Task ID to delete: ")
        if task_id is None:
            return

        try:
            self._task_service.delete_task(task_id)
            print(f"Task #{task_id} deleted successfully.")
        except TodoDomainError as err:
            print(f"Error: {err}")

    def _read_int(self, prompt: str) -> int | None:
        """Safely read integer input with retry/cancel."""
        raw = input(prompt).strip()
        if not raw:
            return None
        try:
            return int(raw)
        except ValueError:
            print("Invalid input: must be an integer number.")
            return None
