import hashlib
from sqlalchemy import func
from bookstoremanagement import db
from bookstoremanagement.models import Book, Category, Cart, CartDetail, User, SaleInvoice, DetailInvoice, UserRole


def load_books(cate_id=None, kw=None):
    query = Book.query

    if cate_id:
        query = query.filter(Book.category_id == cate_id)

    if kw:
        query = query.filter(Book.name.contains(kw))

    return query.all()

def load_categories():
    return Category.query.all()

def load_product_by_id(id):
    book = Book.query.filter_by(id=id).first()
    return book

def insert_book_to_cart(user_id , book_id ):
    # Kiểm tra xem người dùng đã có giỏ hàng chưa
    cart = Cart.query.filter_by(user_id=user_id).first()
    if not cart:
        # Tạo mới giỏ hàng nếu chưa có
        cart = Cart(user_id=user_id)
        db.session.add(cart)
        db.session.commit()

    # Kiểm tra xem sản phẩm đã có trong giỏ hàng chưa
    cart_detail = CartDetail.query.filter_by(cart_id=cart.id, book_id=book_id).first()
    if cart_detail:
        # Nếu sản phẩm đã tồn tại, cập nhật số lượng
        cart_detail.quantity += 1
    else:
        # Nếu sản phẩm chưa tồn tại, thêm mới vào chi tiết giỏ hàng
        cart_detail = CartDetail(
            cart_id=cart.id,
            book_id=book_id,
            quantity=1
        )
        db.session.add(cart_detail)

    db.session.commit()

# def add_user(name, username, password, avatar, email):
#     password = str(hashlib.md5(password.strip().encode('utf-8')).hexdigest())
#     u = None
#     if avatar:
#         u = User(name=name, 
#                 username=username, 
#                 password=password, 
#                 avatar=avatar, 
#                 email=email,
#                 user_role=UserRole.USER)  # Thêm user_role mặc định là USER
#     else:
#         u = User(name=name, 
#                 username=username, 
#                 password=password, 
#                 email=email,
#                 user_role=UserRole.USER)  # Thêm user_role mặc định là USER
#     db.session.add(u)
#     db.session.commit()

def add_user(name , username , password , avatar , email ):
    password = str(hashlib.md5(password.strip().encode('utf-8')).hexdigest())
    u = None
    if avatar:
        u = User(name=name, username=username, password=password, avatar=avatar , email = email)
    else:
        u = User(name=name, username=username, password=password , email = email)
    db.session.add(u)
    db.session.commit()


def auth_user(username, password):
    password = str(hashlib.md5(password.strip().encode('utf-8')).hexdigest())
    
    return User.query.filter(User.username.__eq__(username.strip()),
                           User.password.__eq__(password)).first()


def load_user_by_id(user_id):
    return User.query.get(user_id)


def load_invoice(user_id):
    invoices = (
        db.session.query(
            SaleInvoice.id,  # ID hóa đơn
            SaleInvoice.orderDate,  # Ngày đặt hàng
            SaleInvoice.paymentStatus,  # Trạng thái thanh toán
            func.sum(Book.price * DetailInvoice.quantity).label("totalAmount")  # Tổng tiền hóa đơn
        )
        .join(DetailInvoice, SaleInvoice.id == DetailInvoice.saleInvoice_id)
        .join(Book, Book.id == DetailInvoice.book_id)
        .filter(SaleInvoice.customer_id == user_id)  # Chỉ lấy hóa đơn của user hiện tại
        .group_by(SaleInvoice.id)  # Nhóm theo từng hóa đơn
        .all()
    )
    return invoices