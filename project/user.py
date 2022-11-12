from flask_login import UserMixin
from project import login_manager
import project.routes as routes
from project.routes import g

@login_manager.user_loader
def load_user(user_id):
    if routes.is_student:
        user = g.conn.execute("SELECT * FROM Students WHERE id='{}'".format(user_id))
    else:
        user = g.conn.execute("SELECT * FROM Instructors WHERE id='{}'".format(user_id))
    user = user.fetchone()
    user = User(user.username,routes.is_student)
    return user


class User(UserMixin):
    def __init__(self,username, is_student):
        self.username = username
        self.is_student = is_student
        
    def get_id(self):
        if not isinstance(self, int):
            if self.is_student:
                user = g.conn.execute("SELECT * FROM Students WHERE username='{}'".format(self.username))
            else:
                user = g.conn.execute("SELECT * FROM Instructors WHERE username='{}'".format(self.username))
            user = user.fetchone()
            user_id = user[0]
            if user_id:
                return user_id

    def check_password(self, input_password):
        if self.is_student:
            user = g.conn.execute("SELECT * FROM Students WHERE username='{}'".format(self.username))
        else:
            user = g.conn.execute("SELECT * FROM Instructors WHERE username='{}'".format(self.username))
        user = user.fetchone()
        user_password = user.password
        if user_password==input_password:
            return True
        else:
            return False
