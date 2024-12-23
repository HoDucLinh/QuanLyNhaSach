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

app = Flask(__name__)
app.jinja_env.globals.update(int=int)

app.config["SQLALCHEMY_DATABASE_URI"] ="mysql+pymysql://root:nguyenhung@localhost/bookstoredb?charset=utf8mb4"
app.secret_key = 'ndjdjdkqjiqj@nsansjkaa'
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True
app.config["PAGE_SIZE"] = 16

db = SQLAlchemy(app)
login = LoginManager(app)


cloudinary.config(cloud_name='dzwsdpjgi',
                  api_key='693865187219449',
                  api_secret='PtxvcgqYO2dZs7RDWJeNc2DA5Ew')
