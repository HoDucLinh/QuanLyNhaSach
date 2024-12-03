from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] ="mysql+pymysql://root:123456@localhost/bookstoredb?charset=utf8mb4"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True

db = SQLAlchemy(app)

admin = Admin(app=app, name='BookStore Admin', template_mode='bootstrap3', url='/admin')

# Import các model 
from bookstoremanagement.models import User, Book, Category, Stock, Cart, CartDetail, SaleInvoice, DetailInvoice, Report, StockInvoice

# Thêm các model vào admin interface
admin.add_view(ModelView(User, db.session))
admin.add_view(ModelView(Book, db.session))
admin.add_view(ModelView(Category, db.session))
admin.add_view(ModelView(Stock, db.session))
admin.add_view(ModelView(Cart, db.session))
admin.add_view(ModelView(CartDetail, db.session))
admin.add_view(ModelView(SaleInvoice, db.session))
admin.add_view(ModelView(DetailInvoice, db.session))
admin.add_view(ModelView(Report, db.session))
admin.add_view(ModelView(StockInvoice, db.session))
