from sqlalchemy.orm import relationship

from bookstoremanagement import app ,db

class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True ,autoincrement=True)
    name = db.Column(db.String(100),nullable=False)
    phoneNumber = db.Column(db.String(50),nullable=False)
    address = db.Column(db.String(100))
    role_ID = relationship('Role' ,backref='Employee', lazy=True)

    def __str__(self):
        return self.name


class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True ,autoincrement=True)
    name = db.Column(db.String(100),nullable=False)
    description = db.Column(db.String(100))

    def __str__(self):
        return self.name

class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True ,autoincrement=True)
    reportDate = db.Column(db.Date)
    reportType = db.Column(db.String(100))
    employee_ID = relationship(Employee, backref='Report', lazy=True)

    def __str__(self):
        return self.name

# phai xem lai
class StockInvoice(db.Model):
    id = db.Column(db.Integer, primary_key=True ,autoincrement=True)
    createdDate = db.Column(db.Date)
    totalAmount = db.Column(db.Float)
    totalQuantity = db.Column(db.Integer)
    supplierName = db.Column(db.String(100))
    employee_ID = relationship(Employee, backref='StockInvoice', lazy=True)

    def __str__(self):
        return self.name

class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True ,autoincrement=True)
    name = db.Column(db.String(100) ,nullable=False)
    price = db.Column(db.Float)
    publisherName = db.Column(db.String(100))
    description = db.Column(db.String(100))
    category_ID = relationship('Category' ,backref='Book', lazy=True)

    def __str__(self):
        return self.name

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True ,autoincrement=True)
    name = db.Column(db.String(100),nullable=False)
    totalBook = db.Column(db.Integer)
    stock_ID = relationship('Stock' ,backref='Category', lazy=True)

    def __str__(self):
        return self.name

class Stock(db.Model):
    id = db.Column(db.Integer, primary_key=True ,autoincrement=True)
    name = db.Column(db.String(100),nullable=False)
    description = db.Column(db.String(100))
    totalCategory = db.Column(db.Integer)

    def __str__(self):
        return self.name

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True ,autoincrement=True)
    name = db.Column(db.String(100),nullable=False)
    phoneNumber = db.Column(db.String(100),nullable=False)
    address = db.Column(db.String(100))
    paymentInfo = db.Column(db.String(100))
    email = db.Column(db.String(100))

    def __str__(self):
        return self.name

class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True ,autoincrement=True)
    customer_ID = relationship(Customer , backref='Cart', lazy=True)

    def __str__(self):
        return self.name

class SaleInvoice(db.Model):
    id = db.Column(db.Integer, primary_key=True ,autoincrement=True)
    paymentStatus = db.Column(db.String(100))
    paymentMethod_ID = relationship('PaymentMethod' , backref='SaleInvoice', lazy=True)
    employee_ID = relationship(Employee , backref='SaleInvoice', lazy=True)
    customer_ID = relationship(Customer , backref='SaleInvoice', lazy=True)

    def __str__(self):
        return self.name

class PaymentMethod(db.Model):
    id = db.Column(db.Integer, primary_key=True ,autoincrement=True)
    name = db.Column(db.String(100),nullable=False)
    description = db.Column(db.String(100))

    def __str__(self):
        return self.name

class DetailInvoice(db.Model):
    id = db.Column(db.Integer, primary_key=True ,autoincrement=True)
    book_ID = relationship(Book , backref='DetailInvoice', lazy=True)
    saleInvoice_ID = relationship(SaleInvoice , backref='DetailInvoice')
    orderDate = db.Column(db.Date)
    totalAmount = db.Column(db.Float)
    quantity = db.Column(db.Integer)

    def __str__(self):
        return self.name

if __name__ == "__main__":
    with app.app_context():
        db.create_all()