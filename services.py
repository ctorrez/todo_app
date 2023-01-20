from database import User
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from typing import List

import data


class UserService:
    def __init__(self) -> None:
        pass

    def _get_session(self):
        engine = create_engine('sqlite:///todo.db')
        Session = sessionmaker(bind=engine)
        session = Session()

        return session

    def are_there_users(self) -> bool:

        session = self._get_session()
        result = session.query(User).count()

        if result == 0:
            return False
        else:
            return True

    def add_user(self, user: data.TodoUser) -> None:

        new_user = User(
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email
        )

        session = self._get_session()

        session.add(new_user)
        session.commit()
        session.close()

    def get_users(self) -> List[User]:

        session = self._get_session()
        users = session.query(User).all()

        return users

    def get_user_by_id(self, id) -> User:

        session = self._get_session()
        user = session.query(User).filter(User.id == id).first()

        return user
