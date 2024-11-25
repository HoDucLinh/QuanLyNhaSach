from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship

from bookstoremanagement import app ,db

class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True ,autoincrement=True)
    name = db.Column(db.String(100),nullable=False)
    description = db.Column(db.String(100))
    employees = db.relationship('Employee', backref='role', lazy=True)

    def __str__(self):
        return self.name

class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True ,autoincrement=True)
    name = db.Column(db.String(100),nullable=False)
    phoneNumber = db.Column(db.String(50),nullable=False)
    address = db.Column(db.String(100))
    role_id = Column(Integer, ForeignKey('role.id'), nullable=False)
    reports = db.relationship('Report', backref='employee', lazy=True)
    stockinvoices = db.relationship('StockInvoice', backref='employee', lazy=True)
    saleinvoices = db.relationship('SaleInvoice', backref='employee', lazy=True)

    def __str__(self):
        return self.name

class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True ,autoincrement=True)
    reportDate = db.Column(db.Date)
    reportType = db.Column(db.String(100))
    employee_id = Column(Integer, ForeignKey(Employee.id), nullable=False)

    def __str__(self):
        return self.name

# phai xem lai
class StockInvoice(db.Model):
    id = db.Column(db.Integer, primary_key=True ,autoincrement=True)
    createdDate = db.Column(db.Date)
    totalAmount = db.Column(db.Float)
    totalQuantity = db.Column(db.Integer)
    supplierName = db.Column(db.String(100))
    employee_id = Column(Integer, ForeignKey(Employee.id), nullable=False)

    def __str__(self):
        return self.name

class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True ,autoincrement=True)
    name = db.Column(db.String(100) ,nullable=False)
    price = db.Column(db.Float)
    publisherName = db.Column(db.String(100))
    description = db.Column(db.String(100))
    category_id = Column(Integer, ForeignKey('category.id'), nullable=False)

    def __str__(self):
        return self.name

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True ,autoincrement=True)
    name = db.Column(db.String(100),nullable=False)
    totalBook = db.Column(db.Integer)
    stock_id = Column(Integer, ForeignKey('stock.id'), nullable=False)
    books = relationship(Book, backref='category', lazy=True)

    def __str__(self):
        return self.name

class Stock(db.Model):
    id = db.Column(db.Integer, primary_key=True ,autoincrement=True)
    name = db.Column(db.String(100),nullable=False)
    description = db.Column(db.String(100))
    totalCategory = db.Column(db.Integer)
    categories = relationship('Category' ,backref='Stock', lazy=True)

    def __str__(self):
        return self.name

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True ,autoincrement=True)
    name = db.Column(db.String(100),nullable=False)
    phoneNumber = db.Column(db.String(100),nullable=False)
    address = db.Column(db.String(100))
    paymentInfo = db.Column(db.String(100))
    email = db.Column(db.String(100))
    cart_id = Column(Integer, ForeignKey('cart.id'), nullable=False)
    saleinvoices = relationship('SaleInvoice', backref='customer', lazy=True)

    def __str__(self):
        return self.name

class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True ,autoincrement=True)
    customer_id = Column(Integer, ForeignKey(Customer.id), nullable=False)

    def __str__(self):
        return self.name

class CartDetail(db.Model):
    id = db.Column(db.Integer, primary_key=True ,autoincrement=True)
    book_id = Column(Integer, ForeignKey(Book.id), nullable=False)
    customer_id = Column(Integer, ForeignKey(Customer.id), nullable=False)
    quantity = db.Column(db.Integer , nullable=False)


class PaymentMethod(db.Model):
    id = db.Column(db.Integer, primary_key=True ,autoincrement=True)
    name = db.Column(db.String(100),nullable=False)
    description = db.Column(db.String(100))
    saleinvoices = relationship('SaleInvoice', backref='paymentMethod', lazy=True)

    def __str__(self):
        return self.name
class SaleInvoice(db.Model):
    id = db.Column(db.Integer, primary_key=True ,autoincrement=True)
    paymentStatus = db.Column(db.String(100))
    paymentMethod_id = Column(Integer, ForeignKey(PaymentMethod.id), nullable=False)
    employee_id = Column(Integer, ForeignKey(Employee.id), nullable=False)
    customer_id = Column(Integer, ForeignKey(Customer.id), nullable=False)

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