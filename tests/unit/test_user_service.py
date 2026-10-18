"""Unit tests for UserService using InMemoryUserRepository."""
import pytest

from todo.application.services import UserService
from todo.domain.exceptions import UserAlreadyExistsError, UserNotFoundError
from todo.infrastructure.memory_repos import InMemoryUserRepository


@pytest.fixture
def user_service() -> UserService:
    repo = InMemoryUserRepository()
    return UserService(user_repo=repo)


def test_register_user_successfully(user_service: UserService):
    user = user_service.register_user("Bob", "Martin", "bob@example.com")
    assert user.id == 1
    assert user.full_name == "Bob Martin"
    assert user.email == "bob@example.com"
    assert user_service.has_users()


def test_register_user_duplicate_email_raises_error(user_service: UserService):
    user_service.register_user("Bob", "Martin", "bob@example.com")
    with pytest.raises(UserAlreadyExistsError):
        user_service.register_user("Robert", "Martin", "bob@example.com")


def test_get_user_not_found(user_service: UserService):
    with pytest.raises(UserNotFoundError):
        user_service.get_user(999)


def test_list_users(user_service: UserService):
    assert not user_service.has_users()
    user_service.register_user("Alice", "Wonder", "alice@example.com")
    user_service.register_user("Bob", "Builder", "bob@example.com")
    users = user_service.list_users()
    assert len(users) == 2
    assert [u.first_name for u in users] == ["Alice", "Bob"]
