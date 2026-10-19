"""Ollama local AI adapter implementing TaskParserPort."""

import json
import urllib.error
import urllib.request
from datetime import UTC, datetime

from todo.application.ports import TaskParserPort
from todo.domain.exceptions import TodoDomainError
from todo.domain.models import ParsedTask, Priority


class OllamaTaskParser(TaskParserPort):
    """Parses natural language task inputs into structured domain objects using local Ollama."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3.2:1b",
        timeout: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def parse(self, text: str, reference_date: datetime | None = None) -> ParsedTask:
        ref = reference_date or datetime.now(UTC)
        ref_str = ref.strftime("%Y-%m-%d (%A)")

        system_prompt = (
            "You are an expert task parser. Extract structured task data from natural language.\n"
            f"Reference Current Date: {ref_str}.\n"
            "Calculate all relative dates (e.g. 'tomorrow', 'next Friday', 'in 3 days') relative to Reference Current Date.\n\n"
            "Rules:\n"
            "1. title: Clean, concise summary. Strip command prefixes like 'add task to', 'remind me to'.\n"
            "2. description: Strictly extractive. ONLY include notes or details explicitly written by the user. "
            "NEVER rephrase, explain, or duplicate the task title. NEVER invent words or facts. "
            'If the input is just a single task with no separate notes, description MUST be empty string "".\n'
            "3. priority: Default to MEDIUM. Use HIGH for doctor visits, meetings, or important deadlines. Use URGENT for emergencies or ASAP. Use LOW for casual errands.\n"
            "4. due_date: If a specific time of day is mentioned (e.g. '2pm', '2:30 pm', '14:00'), format as 'YYYY-MM-DD HH:MM' in 24-hour time. "
            "If only a date is mentioned, format as 'YYYY-MM-DD'. If no date or time is mentioned, format as null.\n\n"
            "Examples:\n"
            'User: "Dentist appointment tomorrow at 2:30pm"\n'
            'Output: {"title": "Dentist appointment", "description": "", "due_date": "YYYY-MM-DD 14:30", "priority": "HIGH"}\n\n'
            'User: "Schedule team sync on Friday at 3:30pm, bring insurance card and records"\n'
            'Output: {"title": "Team sync", "description": "Bring insurance card and records", "due_date": "YYYY-MM-DD 15:30", "priority": "HIGH"}\n\n'
            'User: "Buy almond milk on Saturday"\n'
            'Output: {"title": "Buy almond milk", "description": "", "due_date": "YYYY-MM-DD", "priority": "LOW"}\n\n'
            "Return ONLY a JSON object:\n"
            "{\n"
            '  "title": "string",\n'
            '  "description": "string",\n'
            '  "due_date": "YYYY-MM-DD HH:MM or YYYY-MM-DD or null",\n'
            '  "priority": "LOW | MEDIUM | HIGH | URGENT"\n'
            "}"
        )

        payload = {
            "model": self.model,
            "prompt": text,
            "system": system_prompt,
            "format": "json",
            "stream": False,
            "options": {
                "temperature": 0.1,  # Low temperature for deterministic JSON extraction
            },
        }

        url = f"{self.base_url}/api/generate"
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                raw_body = response.read().decode("utf-8")
        except urllib.error.URLError as err:
            raise TodoDomainError(
                f"Could not connect to local Ollama at '{self.base_url}'. "
                "Ensure the Ollama application is running on your machine."
            ) from err

        try:
            data = json.loads(raw_body)
            result = json.loads(data.get("response", "{}"))
        except (json.JSONDecodeError, KeyError) as err:
            raise TodoDomainError(f"Failed to parse JSON response from Ollama: {err}") from err

        title = str(result.get("title", "")).strip() or text.strip()
        description = str(result.get("description", "")).strip()
        # Avoid redundant descriptions that just duplicate the title
        if description.lower() == title.lower():
            description = ""

        # Parse due date (date and optional time)
        due_date: datetime | None = None
        due_date_str = result.get("due_date")
        if due_date_str and isinstance(due_date_str, str) and due_date_str.lower() != "null":
            due_clean = due_date_str.strip()
            for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
                try:
                    due_date = datetime.strptime(due_clean, fmt).replace(tzinfo=UTC)
                    break
                except ValueError:
                    continue
            if due_date is None:
                try:
                    parsed_iso = datetime.fromisoformat(due_clean)
                    due_date = parsed_iso if parsed_iso.tzinfo else parsed_iso.replace(tzinfo=UTC)
                except ValueError:
                    due_date = None

        # Parse priority
        priority_raw = str(result.get("priority", "MEDIUM")).strip().upper()
        try:
            priority = Priority(priority_raw)
        except ValueError:
            priority = Priority.MEDIUM

        return ParsedTask(
            title=title,
            description=description,
            due_date=due_date,
            priority=priority,
        )
