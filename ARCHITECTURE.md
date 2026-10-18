# Architecture Guide & Design Decisions

This project is a minimal MVP TODO application demonstrating **Light Clean Architecture (Ports & Adapters / Hexagonal)** in Python.

## Core Architectural Principles

### 1. The Dependency Inversion Principle (DIP)
Dependencies strictly point inward toward higher-level business rules:

```
[ Presentation (CLI) ]  --->  [ Application (Use Cases) ]  --->  [ Domain (Entities) ]
                                            |
                                            v (defines interface)
[ Infrastructure (SQLAlchemy / Memory) ] implements [ Ports ]
```

- **Domain Layer (`src/todo/domain`)**:
  - Pure Python dataclasses (`User`, `Task`, `TaskStatus`).
  - Contains core validation and business rules (e.g. state transitions like `task.complete()`, `task.reopen()`).
  - Zero external framework dependencies.
  
- **Application Layer (`src/todo/application`)**:
  - Defines the abstract **Ports** (`UserRepository`, `TaskRepository`).
  - Orchestrates use cases in `UserService` and `TaskService`.
  - Never references database drivers, SQL, or UI code.

- **Infrastructure Layer (`src/todo/infrastructure`)**:
  - Contains concrete **Adapters** implementing the ports:
    - `SqlAlchemyUserRepository` / `SqlAlchemyTaskRepository`: Production SQLite persistence using SQLAlchemy 2.0.
    - `InMemoryUserRepository` / `InMemoryTaskRepository`: Lightweight in-memory persistence for lightning-fast unit tests.
  - ORM entities (`UserModel`, `TaskModel`) are isolated to infrastructure and mapped to/from pure domain entities.

- **Presentation Layer (`src/todo/presentation`)**:
  - Interactive CLI (`TodoCLI`) that only communicates with application services.
  - Gracefully maps domain errors (`TodoDomainError`) into user-friendly messages.

- **Composition Root (`app.py`)**:
  - The single place at the application entrypoint where concrete dependencies are instantiated and wired together.

---

## Clean Seams: Why In-Memory Repositories Matter

A **seam** is an architectural boundary that allows swapping implementations without modifying business logic.

Because `TaskService` only depends on the abstract `TaskRepository` interface:
1. **Unit Tests** run with `InMemoryTaskRepository`:
   - 0 database setup or migrations.
   - 0 mock objects.
   - Execution time: ~0.1 seconds for 20+ tests.
2. **Production App** runs with `SqlAlchemyTaskRepository`:
   - Persists data reliably to `todo.db`.
   - Swap to PostgreSQL or MySQL simply by changing the connection string in the Composition Root.

---

## SOLID Principles in Practice

- **Single Responsibility Principle (SRP)**: Each layer and service has one reason to change. `TaskService` handles task coordination; `SqlAlchemyTaskRepository` handles SQL queries; `TodoCLI` handles user interaction.
- **Open/Closed Principle (OCP)**: New storage mechanisms (e.g., MongoDB, DynamoDB) can be added by implementing `TaskRepository` without touching existing application services.
- **Liskov Substitution Principle (LSP)**: `InMemoryTaskRepository` and `SqlAlchemyTaskRepository` can be substituted for one another transparently in `TaskService`.
- **Interface Segregation Principle (ISP)**: Focused repository interfaces provide only the methods necessary for the domain operations.
- **Dependency Inversion Principle (DIP)**: High-level modules do not depend on low-level modules; both depend on abstractions.
