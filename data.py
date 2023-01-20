"""
Business Entities

DDD - Domain Driven Design
ORM - Object Relational Model
CRUD operations

"""
import datetime
from typing import List


class TodoItem:
    def __init__(self, id: int, user_id: int,
        name: str, completed: bool, last_updated: datetime.datetime) -> None:
        self.id = id
        self.user_id = user_id
        self.name = name
        self.completed = completed
        self.last_updated = last_updated

class TodoUser:
    def __init__(self, first_name: str, last_name: str, email: str) -> None:
        self.first_name = first_name
        self.last_name = last_name
        self.email = email

