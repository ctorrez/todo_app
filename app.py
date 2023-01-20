"""
TODO App
Following a Multilayer Architecture
* Data Layer
* Business Layer
* Presentation Layer
"""
import services
from data import TodoUser

userService = services.UserService()


def get_int_from_user():
    # todo: handle invalid numbers
    value = int(input("Type your user id: "))

    return value

def setup_user_name(userService):
    if userService.are_there_users() == False:
        print("Please you need sign up to access app")

        first_name = input("Firt Name: ")
        last_name = input("Last Name: ")
        email = input("Email: ")

        user = TodoUser(first_name, last_name, email)
        userService.add_user(user)

def select_your_user():

    # print users
    users = userService.get_users()

    for user in users:
        print("Id, First Name, Last Name, email")
        print((user.id, user.first_name, user.last_name, user.email))

    id = int(input("Type your user id: "))

    user = userService.get_user_by_id(id)

    print("User selected:")
    print((user.id, user.first_name, user.last_name, user.email))

def add_task():
    # todo: implement this method
    pass


setup_user_name(userService)

select_your_user()

add_task()

if __name__ == "__main__":
    pass