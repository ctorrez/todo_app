"""Domain-specific exceptions."""


class TodoDomainError(Exception):
    """Base exception for all domain errors."""


class ValidationError(TodoDomainError):
    """Raised when domain entity validation fails."""


class UserNotFoundError(TodoDomainError):
    """Raised when a requested user does not exist."""


class UserAlreadyExistsError(TodoDomainError):
    """Raised when attempting to create a user with an existing email."""


class TaskNotFoundError(TodoDomainError):
    """Raised when a requested task does not exist."""
