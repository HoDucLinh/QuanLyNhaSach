import hashlib
from datetime import date, datetime
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

    @classmethod
    def choices(cls):
        return [(choice.value, choice.name) for choice in cls]


class User(db.Model , UserMixin):
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
    #1 customer có thể có nhiều sách yêu thích
    favorites = relationship('Favorite', backref='customer', lazy=True)

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
    quantity = db.Column(db.Integer)
    category_id = Column(Integer, ForeignKey('category.id'), nullable=False)
    favorites = relationship('Favorite', backref='book', lazy=True)

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
    name = db.Column(db.String(100), nullable=False)  # Thêm cột name
    categories = relationship('Category' ,backref='stock', lazy=True)

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
    #nếu mua onl thì lấy tên thông qua customer_id , nếu mua off thì điền thẳng tên
    customer_name = db.Column(db.String(100) , nullable = False)
    #lưu id của khách hang , nếu = null thì là mua off , nếu c giá trị là mua onl
    customer_id = Column(Integer, ForeignKey('user.id'), nullable=True)
    #lưu id của sale , neu null là mua onl ,neeseu có gia trị là mua off
    sale_id = Column(Integer, ForeignKey('user.id'), nullable=True)
    orderDate = db.Column(db.Date,default=datetime.utcnow())

    def __str__(self):
        return self.name


class DetailInvoice(db.Model):
    id = db.Column(db.Integer, primary_key=True ,autoincrement=True)
    book_id = Column(Integer, ForeignKey(Book.id), nullable=False)
    saleInvoice_id = Column(Integer, ForeignKey(SaleInvoice.id), nullable=False)
    quantity = db.Column(db.Integer)

    def __str__(self):
        return self.name


class Favorite(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    book_id = Column(Integer, ForeignKey(Book.id), nullable=False)
    customer_id = Column(Integer, ForeignKey('user.id'), nullable=False)

class Regulation(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    min_import_quantity = db.Column(db.Integer, default=150)  # Số lượng nhập tối thiểu
    min_stock_before_import = db.Column(db.Integer, default=300)  # Số lượng tồn tối thiểu trước khi nhập
    order_cancel_time = db.Column(db.Integer, default=48)  # Thời gian hủy đơn (giờ)
    updated_date = db.Column(db.DateTime, default=datetime.now())
    updated_by = db.Column(db.Integer, ForeignKey(User.id), nullable=False)

if __name__ == "__main__":
    with app.app_context():
         db.create_all()
         stock = Stock(name = "Kho sach chinh")
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
         new_user1 = User(name='Ho Duc Linh',username='HDL',password= str(hashlib.md5("hdl".encode('utf-8')).hexdigest()),email='hdl@gmail.com')
         new_user2 = User(name='Nguyen Quang Khanh',username='NQK',password= str(hashlib.md5("nqk".encode('utf-8')).hexdigest()),email='nqk@gmail.com')
         new_user3 = User(name='Sale1', username='sale12',
                          password=str(hashlib.md5("123".encode('utf-8')).hexdigest()), email='sale@gmail.com',
                          user_role=UserRole.SALE)
         # Thêm đối tượng vào cơ sở dữ liệu
         db.session.add_all([new_user1,new_user2,new_user3])
         db.session.commit()
         sale_invoices = [
             SaleInvoice(id=1, paymentStatus="Paid",customer_name ="Ho Duc Linh", customer_id=1, sale_id=None, orderDate=date(2024, 12, 1)),
             SaleInvoice(id=2, paymentStatus="Pending",customer_name ="Ho Duc Linh", customer_id=1, sale_id=None, orderDate=date(2024, 12, 2)),
             SaleInvoice(id=3, paymentStatus="Paid",customer_name ="Nguyen Quang Khanh", customer_id=2, sale_id=None, orderDate=date(2024, 12, 3)),
         ]

         db.session.add_all(sale_invoices)
         db.session.commit()
         detail_invoices = [
             DetailInvoice(id=1, book_id=1, saleInvoice_id=1, quantity=2),
             DetailInvoice(id=2, book_id=2, saleInvoice_id=1, quantity=1),
             DetailInvoice(id=3, book_id=3, saleInvoice_id=2, quantity=3),
         ]

         db.session.add_all(detail_invoices)
         db.session.commit()
         favorites = [
             Favorite(book_id=1, customer_id=1),
             Favorite(book_id=8, customer_id=1),
             Favorite(book_id=3, customer_id=2),
             Favorite(book_id=5, customer_id=2),
         ]
         db.session.add_all(favorites)
         db.session.commit()
         admin_user = User(name='Admin', username='admin', password=str(hashlib.md5('123'.encode('utf-8')).hexdigest()),
                           user_role=UserRole.ADMIN)

         db.session.add(admin_user)
         db.session.commit()

