"""Mock AI task parser for fast, deterministic unit testing."""

import re
from datetime import datetime

from todo.application.ports import TaskParserPort
from todo.domain.models import ParsedTask, Priority


class MockTaskParser(TaskParserPort):
    """Deterministic, mock parser that parses simple strings without calling LLMs."""

    def __init__(self, default_priority: Priority = Priority.MEDIUM) -> None:
        self.default_priority = default_priority

    def parse(self, text: str, reference_date: datetime | None = None) -> ParsedTask:
        clean = text.strip()
        lower = clean.lower()

        priority = self.default_priority
        if "urgent" in lower or "asap" in lower:
            priority = Priority.URGENT
        elif "high" in lower or "important" in lower:
            priority = Priority.HIGH
        elif "low" in lower:
            priority = Priority.LOW

        # Simple title cleanup: remove leading urgency prefixes
        title = re.sub(
            r"^(urgent|high priority|important)[:\s-]*", "", clean, flags=re.IGNORECASE
        ).strip()
        if not title:
            title = clean

        return ParsedTask(
            title=title,
            description="Extracted by MockTaskParser",
            due_date=reference_date,
            priority=priority,
        )
