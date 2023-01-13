from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import relationship

from datetime import datetime

Base = declarative_base()

class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True)
    title = Column(String)
    description = Column(String)
    due_date = Column(DateTime)
    is_completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    list_id = Column(Integer, ForeignKey('lists.id'))
    list = relationship("TodoList", back_populates="tasks")

class TodoList(Base):
    __tablename__ = "lists"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    user_id = Column(Integer, ForeignKey('users.id'))
    user = relationship("User")
    tasks = relationship("Task", order_by=Task.due_date, back_populates="list")
    created_at = Column(DateTime, default=datetime.utcnow)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String)


# create a session
engine = create_engine('sqlite:///todo.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

# test case
# create a new user
new_user = User(name="John Smith", email="johnsmith@example.com")
session.add(new_user)
session.commit()

# create a new to-do list for the user
new_list = TodoList(name="Shopping List", user=new_user)
session.add(new_list)
session.commit()

# add a task to the to-do list
new_task = Task(title="Buy milk", description="Pick up a carton of milk from the store", due_date=datetime.now(), list=new_list)
session.add(new_task)
session.commit()
session.close()


class UserService:
    def create_user(self, user: User):
        db_user = UserEntity(name=user.name, email=user.email)
        session.add(db_user)
        session.commit()
        session.refresh(db_user)
        user.id = db_user.id
        return user

    def get_user(self, user_id: int):
        db_user = session.query(UserEntity).get(user_id)
        return User(name=db_user)

    def create_todo_list(self, name: str, user_id: int):
        user = self.get_user(user_id)
        new_list = TodoList(name=name, user=user)
        db_list = TodoListDb(name=new_list.name, user_id=user_id)
        session.add(db_list)
        session.commit()
        session.refresh(db_list)
        new_list.id = db_list.id
        return new_list

    def add_task(self, task: Task, todo_list_id: int):
        todo_list = self.get_todo_list(todo_list_id)
        db_task = TaskDb(title=task.title, description=task.description, due_date=task.due_date, list_id=todo_list_id)
        session.add(db_task)
        session.commit()
        session.refresh(db_task)
        task.id = db_task.id
        todo_list.tasks

