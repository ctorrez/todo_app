# Architecture Guide & Design Decisions

This project is a minimal MVP TODO application demonstrating **Light Clean Architecture (Ports & Adapters / Hexagonal)** in Python, combining **Domain-Driven Design (DDD)** and **Local AI Engineering**.

## Core Architectural Principles

### 1. The Dependency Inversion Principle (DIP)
Dependencies strictly point inward toward higher-level business rules:

```
[ Presentation (CLI / Agents) ]  --->  [ Application (Use Cases) ]  --->  [ Domain (Entities) ]
                                                    |
                                                    v (defines ports)
[ Infrastructure (SQLAlchemy / Memory / Ollama) ] implements [ Ports ]
```

- **Domain Layer (`src/todo/domain`)**:
  - Pure Python dataclasses (`User`, `Task`, `ParsedTask`, `Priority`, `TaskStatus`).
  - Contains core validation and business rules (e.g. `task.is_overdue`, state transitions like `task.complete()`, `task.reopen()`).
  - Zero external framework dependencies.
  
- **Application Layer (`src/todo/application`)**:
  - Defines the abstract **Ports**:
    - `UserRepository`, `TaskRepository` for persistence.
    - `TaskParserPort` for AI / natural language extraction.
  - Orchestrates use cases in `UserService` and `TaskService`.
  - Never references database drivers, SQL, AI vendor SDKs, or UI code.

- **Infrastructure Layer (`src/todo/infrastructure`)**:
  - Contains concrete **Adapters** implementing the ports:
    - `SqlAlchemyUserRepository` / `SqlAlchemyTaskRepository`: Production SQLite persistence using SQLAlchemy 2.0.
    - `InMemoryUserRepository` / `InMemoryTaskRepository`: Lightweight in-memory persistence for lightning-fast unit tests.
    - `OllamaTaskParser`: Local privacy-preserving AI adapter communicating with self-hosted Ollama (`llama3.2:1b`).
    - `MockTaskParser`: Deterministic AI mock adapter for unit testing without network/LLM dependencies.
  - ORM entities (`UserModel`, `TaskModel`) are isolated to infrastructure and mapped to/from pure domain entities.

- **Presentation Layer (`src/todo/presentation`)**:
  - Interactive CLI (`TodoCLI`) that only communicates with application services.
  - Non-interactive Command Handler (`run_command`) supporting structured `--json` outputs for AI agents and scripts.
  - Gracefully maps domain errors (`TodoDomainError`) into user-friendly messages.

- **Composition Root (`app.py`)**:
  - The single place at the application entrypoint where concrete dependencies are instantiated and wired together.

---

## Clean Seams & AI Engineering

A common pitfall in AI applications is tightly coupling prompt generation and vendor SDKs directly into business or UI logic.

In this architecture, **AI is treated as an Outbound Adapter**:
1. **The Application defines what it needs** via `TaskParserPort`:
   ```python
   class TaskParserPort(ABC):
       @abstractmethod
       def parse(self, text: str, reference_date: datetime | None = None) -> ParsedTask: ...
   ```
2. **The Infrastructure provides the implementation**:
   - `OllamaTaskParser` sends an HTTP request to `localhost:11434` with structured JSON mode.
   - `MockTaskParser` parses strings instantly during test runs.
3. **Zero Vendor Lock-In**:
   If tomorrow you want to switch from local Ollama to Google Gemini, Anthropic Claude, or OpenAI, you **only write a new adapter class** implementing `TaskParserPort`. The core domain logic and `TaskService` remain 100% untouched.

---

## SOLID Principles in Practice

- **Single Responsibility Principle (SRP)**: Each layer and service has one reason to change. `TaskService` coordinates task operations; `SqlAlchemyTaskRepository` handles SQL queries; `OllamaTaskParser` handles AI prompt formatting; `TodoCLI` handles user interaction.
- **Open/Closed Principle (OCP)**: New storage mechanisms (e.g., MongoDB, DynamoDB) or AI engines (e.g., Gemini, OpenAI) can be added simply by implementing the existing ports without touching application services.
- **Liskov Substitution Principle (LSP)**: `InMemoryTaskRepository` and `SqlAlchemyTaskRepository`, as well as `MockTaskParser` and `OllamaTaskParser`, can be substituted for one another transparently.
- **Interface Segregation Principle (ISP)**: Focused repository and parser interfaces provide only the methods necessary for the domain operations.
- **Dependency Inversion Principle (DIP)**: High-level modules do not depend on low-level modules; both depend on abstractions.
