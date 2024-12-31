import hashlib
import hmac
import json
import urllib
import requests
import uuid
from datetime import datetime, time
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import cloudinary
from flask_mail import Message, Mail

app = Flask(__name__)
app.jinja_env.globals.update(int=int)

app.config["SQLALCHEMY_DATABASE_URI"] ="mysql+pymysql://root:08022004@localhost/bookstoredb?charset=utf8mb4"
app.secret_key = 'ndjdjdkqjiqj@nsansjkaa'
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True
app.config["PAGE_SIZE"] = 16

# Cấu hình cho Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'holinh8241@gmail.com'
app.config['MAIL_PASSWORD'] = 'ccdnzsfvtktyftvr'
mail = Mail(app)
db = SQLAlchemy(app)
login = LoginManager(app)


cloudinary.config(cloud_name='dzwsdpjgi',
                  api_key='693865187219449',
                  api_secret='PtxvcgqYO2dZs7RDWJeNc2DA5Ew')
