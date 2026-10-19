# AI Prompt Testing Guide & Test Catalog

This document details the prompt engineering design, test cases, and verification results for the local AI natural language parser in the TODO application.

It specifically addresses how small local models (SLMs) such as Meta's **Llama 3.2 1B** handle entity extraction, title vs. description separation, priority inference, and relative date calculations without hallucinating details.

---

## 1. Architectural Seam & Motivation

In Clean Architecture, natural language parsing is an **infrastructure concern**:

```
Presentation (CLI / JSON)
        │
        ▼
Application (TaskParserPort)  <────── Core Interface
        ▲
        │
Infrastructure (OllamaTaskParser) <── Adapter (llama3.2:1b)
```

The application core depends only on the domain object `ParsedTask` returned by `TaskParserPort`:

```python
@dataclass(frozen=True)
class ParsedTask:
    title: str
    description: str
    due_date: datetime | None
    priority: Priority
```

---

## 2. Key Prompt Engineering Challenges in 1B Models

Small Language Models (SLMs) running on CPU have lower parameter capacity than 70B+ cloud models. When testing `llama3.2:1b`, two key failure modes were identified and solved:

1. **Generative Completion Bias (Hallucination)**:
   * *Problem*: When given a simple prompt like `"take Grace to the Dr at 2:30 pm"` with the instruction `"never repeat title in description"`, the 1B model felt compelled to populate the description field and hallucinated fictional details:
     `Description: Book an appointment with Dr. Smith for Grace's check-up.`
   * *Solution*: Enforce **strict extractive constraints** and provide **few-shot examples** showing that simple tasks must produce an empty string `""` for `description`.

2. **Temporal Grounding**:
   * *Problem*: LLMs have no internal clock; terms like *"tomorrow"* or *"next Friday"* produce arbitrary or stale dates.
   * *Solution*: The application injects the current reference date and weekday (e.g., `2026-10-18 (Sunday)`) into the system prompt at runtime.

---

## 3. Verified Test Catalog

The following test suite was verified against `llama3.2:1b` running locally on `http://localhost:11434`.

### Test 1: Simple Single-Action (Extractive Boundary Test)
Verifies that the model does **not** hallucinate doctor names, reasons, or filler text when no secondary details are present.

* **CLI Command**:
  ```powershell
  .\.venv\scripts\python.exe app.py ai parse "add task to take Grace to the Dr at 2:30 pm"
  ```
* **Expected Output**:
  ```text
  AI Extracted Task Details (Preview - Not Saved):
    Title:       Take Grace to the Dr at 2:30 pm
    Due Date:    2026-10-19
    Priority:    MEDIUM
  ```
* **Validation**:
  * `Title` strips prefix `"add task to"`.
  * `Description` is empty `""` (no `"Dr. Smith"` hallucination).
  * `Due Date` defaults to the appointment date.

---

### Test 2: Task with Explicit Secondary Notes (`Notes:`)
Verifies that secondary instructions or notes are cleanly separated from the action title.

* **CLI Command**:
  ```powershell
  .\.venv\scripts\python.exe app.py ai parse "Pick up car from mechanic tomorrow at 4pm. Notes: Bring spare key and ask about oil leak"
  ```
* **Expected Output**:
  ```text
  AI Extracted Task Details (Preview - Not Saved):
    Title:       Pick up car from mechanic tomorrow at 4pm
    Description: Bring spare key and ask about oil leak
    Due Date:    2026-10-20
    Priority:    MEDIUM
  ```
* **Validation**:
  * `Title` contains the main action.
  * `Description` captures the execution checklist.

---

### Test 3: Action with Items to Bring (`bring ...`)
Verifies natural-language checklist extraction without explicit labels like "Notes:".

* **CLI Command**:
  ```powershell
  .\.venv\scripts\python.exe app.py ai parse "Schedule dentist visit on Friday at 3pm, bring insurance card and records"
  ```
* **Expected Output**:
  ```text
  AI Extracted Task Details (Preview - Not Saved):
    Title:       Dentist visit at 3pm
    Description: Bring insurance card and records
    Due Date:    2026-10-23
    Priority:    HIGH
  ```
* **Validation**:
  * Secondary clause extracted into `Description`.
  * Medical/appointment context sets priority to `HIGH`.

---

### Test 4: Urgency / Emergency Priority
Verifies that critical keywords trigger `Priority.URGENT`.

* **CLI Command**:
  ```powershell
  .\.venv\scripts\python.exe app.py ai parse "Fix production database outage ASAP"
  ```
* **Expected Output**:
  ```text
  AI Extracted Task Details (Preview - Not Saved):
    Title:       Fix production database outage
    Due Date:    None
    Priority:    URGENT
  ```
* **Validation**:
  * `Priority` correctly set to `URGENT`.
  * `Description` remains empty.

---

### Test 5: Casual Errands (Low Priority)
Verifies that everyday errands default to `Priority.LOW`.

* **CLI Command**:
  ```powershell
  .\.venv\scripts\python.exe app.py ai parse "Buy almond milk and sourdough bread on Saturday"
  ```
* **Expected Output**:
  ```text
  AI Extracted Task Details (Preview - Not Saved):
    Title:       Buy almond milk and sourdough bread
    Due Date:    2026-10-24
    Priority:    LOW
  ```
* **Validation**:
  * `Priority` resolves to `LOW`.
  * `Due Date` correctly points to the upcoming Saturday.

---

### Test 6: Machine Agent JSON Output (`--json`)
Verifies that AI agents, background workers, or CI scripts can consume structured JSON output without ANSI or decorative CLI formatting.

* **CLI Command**:
  ```powershell
  .\.venv\scripts\python.exe app.py ai parse "Team sprint planning next Monday at 10am" --json
  ```
* **Expected Output**:
  ```json
  {
    "status": "success",
    "data": {
      "title": "Team sprint planning at 10am",
      "description": "",
      "due_date": "2026-10-26T00:00:00+00:00",
      "priority": "MEDIUM"
    }
  }
  ```
* **Validation**:
  * Valid RFC 8259 JSON format.
  * ISO 8601 formatted datetime with UTC timezone.

---

### Test 7: Direct Ingestion & Persistence (`ai add`)
Verifies end-to-end flow: AI extraction $\rightarrow$ domain validation $\rightarrow$ SQLite database insertion.

* **CLI Command**:
  ```powershell
  .\.venv\scripts\python.exe app.py ai add "Take car to mechanic tomorrow at 4pm. Notes: Bring spare key"
  ```
* **Expected Output**:
  ```text
  AI Task Created: #1 [MEDIUM] - Pick up car from mechanic tomorrow at 4pm (Due: 2026-10-20)
     Description: Bring spare key
  ```
* **Validation**:
  * Task is assigned an auto-incrementing ID.
  * Task is saved to `tasks` table with foreign key to active user.

---

## 4. Prompt Engineering Reference

The active prompt configuration in `src/todo/infrastructure/ai/ollama_parser.py`:

```python
system_prompt = (
    "You are an expert task parser. Extract structured task data from natural language.\n"
    f"Reference Current Date: {ref_str}.\n"
    "Calculate all relative dates (e.g. 'tomorrow', 'next Friday', 'in 3 days') relative to Reference Current Date.\n\n"
    "Rules:\n"
    "1. title: Clean, concise summary. Strip command prefixes like 'add task to', 'remind me to'.\n"
    "2. description: Strictly extractive. ONLY include notes or details explicitly written by the user. "
    "NEVER invent names, reasons, or facts not present in the input. "
    "If no extra details exist beyond the task title, output empty string \"\".\n"
    "3. priority: Default to MEDIUM. Use HIGH for doctor visits, meetings, or important deadlines. Use URGENT for emergencies or ASAP. Use LOW for casual errands.\n"
    "4. due_date: Format as YYYY-MM-DD or null.\n\n"
    "Examples:\n"
    "User: \"Call mom tomorrow at 5pm\"\n"
    'Output: {"title": "Call mom at 5pm", "description": "", "due_date": "YYYY-MM-DD", "priority": "MEDIUM"}\n\n'
    "User: \"Schedule dentist visit on Friday at 3pm, bring insurance card and records\"\n"
    'Output: {"title": "Dentist visit at 3pm", "description": "Bring insurance card and records", "due_date": "YYYY-MM-DD", "priority": "HIGH"}\n\n'
    "Return ONLY a JSON object:\n"
    "{\n"
    '  "title": "string",\n'
    '  "description": "string",\n'
    '  "due_date": "YYYY-MM-DD or null",\n'
    '  "priority": "LOW | MEDIUM | HIGH | URGENT"\n'
    "}"
)
```

### Key Parameters:
* **`format: "json"`**: Forces Ollama's grammar-constrained decoding engine to guarantee syntactically valid JSON.
* **`temperature: 0.1`**: Low entropy ensures deterministic field extraction across repetitive executions.
