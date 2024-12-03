from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import cloudinary
app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] ="mysql+pymysql://root:08022004@localhost/bookstoredb?charset=utf8mb4"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True

db = SQLAlchemy(app)
login = LoginManager(app)

cloudinary.config(cloud_name='dzwsdpjgi',
                  api_key='693865187219449',
                  api_secret='PtxvcgqYO2dZs7RDWJeNc2DA5Ew')
