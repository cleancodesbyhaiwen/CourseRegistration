import os
from flask import Flask
from flask_login import LoginManager
from sqlalchemy import *


tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)
app.config['SECRET_KEY'] = 'ec9439cfc6c796ae2029594d'
login_manager = LoginManager(app)


DB_USER = "hl3645"
DB_PASSWORD = "0331"
DB_SERVER = "w4111.cisxo09blonu.us-east-1.rds.amazonaws.com"
DATABASEURI = "postgresql://"+DB_USER+":"+DB_PASSWORD+"@"+DB_SERVER+"/proj1part2"

engine = create_engine(DATABASEURI)

from project import routes