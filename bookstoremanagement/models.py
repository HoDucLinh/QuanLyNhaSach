from email.policy import default
from flask import json
from sqlalchemy import Column, Integer, ForeignKey, String
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum
from sqlalchemy import Enum as SQLEnum
from bookstoremanagement import app ,db
from flask_login import UserMixin



class UserRole(PyEnum):
    ADMIN = 1
    SALE = 2
    USER = 3


class User(db.Model, UserMixin):
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(100), nullable=False, unique=True)
    password = db.Column(db.String(100), nullable=False)
    avatar = db.Column(db.String(2083), default="https://res.cloudinary.com/dzwsdpjgi/image/upload/v1733196994/default-avatar-profile-icon-vector-social-media-user-photo-700-205577532_tfbwxm.jpg")
    email = db.Column(db.String(200) , nullable=True)
    user_role = db.Column(SQLEnum(UserRole), default=UserRole.USER)
    # 1 nhân viên sale có thể tạo nhiều hóa đơn bán hàng
    sale_invoices = relationship('SaleInvoice', backref='sale_user', lazy=True,foreign_keys='SaleInvoice.sale_id')
    # 1 khách hàng có thể có nhiều hóa đơn
    customer_invoices = relationship('SaleInvoice', backref='customer', lazy=True,foreign_keys='SaleInvoice.customer_id')
    # 1 admin có thể tạo nhiều report
    reports = relationship('Report', backref='report', lazy=True)
    # 1 nhân viên có the tạo nhiều hóa đơn nhập kho
    stock_invoices = relationship('StockInvoice' , backref='stockInvoice' , lazy=True)

    def __str__(self):
        return self.name


class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True ,autoincrement=True)
    reportDate = db.Column(db.Date)
    reportType = db.Column(db.String(100))
    #lưu admin tạo report
    user_id = Column(Integer, ForeignKey(User.id), nullable=False)

    def __str__(self):
        return self.name


class StockInvoice(db.Model):
    id = db.Column(db.Integer, primary_key=True ,autoincrement=True)
    createdDate = db.Column(db.Date)
    totalAmount = db.Column(db.Float)
    totalQuantity = db.Column(db.Integer)
    supplierName = db.Column(db.String(100))
    #lưu nhân viên tạo report
    user_id = Column(Integer, ForeignKey(User.id), nullable=False)

    def __str__(self):
        return self.name


class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True ,autoincrement=True)
    name = db.Column(db.String(100) ,nullable=False)
    price = db.Column(db.Float)
    publisherName = db.Column(db.String(100))
    image = Column(db.String(200), nullable=True)
    description = db.Column(db.String(300))
    category_id = Column(Integer, ForeignKey('category.id'), nullable=False)

    def __str__(self):
        return self.name


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True ,autoincrement=True)
    name = db.Column(db.String(100),nullable=False)
    stock_id = Column(Integer, ForeignKey('stock.id'), nullable=False)
    books = relationship(Book, backref='category', lazy=True)

    def __str__(self):
        return self.name


class Stock(db.Model):
    id = db.Column(db.Integer, primary_key=True ,autoincrement=True)
    categories = relationship('Category' ,backref='Stock', lazy=True)

    def __str__(self):
        return self.name


class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True ,autoincrement=True)
    user_id = Column(Integer, ForeignKey(User.id), nullable=False)

    def __str__(self):
        return self.name

class CartDetail(db.Model):
    id = db.Column(db.Integer, primary_key=True ,autoincrement=True)
    book_id = Column(Integer, ForeignKey(Book.id), nullable=False)
    cart_id = Column(Integer, ForeignKey(Cart.id), nullable=False)
    quantity = db.Column(db.Integer , nullable=False)

    def __str__(self):
        return self.name


class SaleInvoice(db.Model):
    id = db.Column(db.Integer, primary_key=True ,autoincrement=True)
    paymentStatus = db.Column(db.String(100))
    customer_id = Column(Integer, ForeignKey('user.id'), nullable=False)  # Khóa ngoại tới khách hàng
    sale_id = Column(Integer, ForeignKey('user.id'), nullable=True)  # Khóa ngoại tới nhân viên bán hàng

    def __str__(self):
        return self.name


class DetailInvoice(db.Model):
    id = db.Column(db.Integer, primary_key=True ,autoincrement=True)
    book_id = Column(Integer, ForeignKey(Book.id), nullable=False)
    saleInvoice_id = Column(Integer, ForeignKey(SaleInvoice.id), nullable=False)
    orderDate = db.Column(db.Date)
    totalAmount = db.Column(db.Float)
    quantity = db.Column(db.Integer)

    def __str__(self):
        return self.name

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        stock = Stock()
        db.session.add(stock)
        db.session.commit()
        c1 = Category(name="Lap trinh", stock_id=1)
        c2 = Category(name="Ngon tinh", stock_id=1)
        c3 = Category(name="Thieu nhi", stock_id=1)
        db.session.add_all([c1, c2, c3])
        db.session.commit()
        with open('data/books.json', encoding='utf-8') as f:
            books = json.load(f)
            for b in books:
                book = Book(**b)
                db.session.add(book)
        db.session.commit()
        new_user = User(
            name='Nguyen Van A',
            username='nva',
            password='123',
            email='customer@gmail.com',
            address='123 Đường ABC, Thành phố XYZ',
        )
        # Thêm đối tượng vào cơ sở dữ liệu
        db.session.add(new_user)
        db.session.commit()