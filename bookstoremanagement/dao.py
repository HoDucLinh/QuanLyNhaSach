
from bookstoremanagement import db, app
import hashlib
from sqlalchemy import func
from bookstoremanagement.models import Book, Category, Cart, CartDetail, User, SaleInvoice, DetailInvoice, UserRole, \
    Regulation, Favorite
from sqlalchemy.sql import extract
from datetime import datetime, timedelta


def load_books(book_id=None,cate_id=None, kw=None , page = None):
    query = Book.query

    if book_id:  # Kiểm tra nếu book_id có giá trị
        return query.filter(Book.id == book_id).first()

    if cate_id:
        query = query.filter(Book.category_id == cate_id)

    if kw:
        query = query.filter(Book.name.contains(kw))

    if page:
        page_size = app.config["PAGE_SIZE"]
        start = (int(page) - 1) * page_size
        query = query.slice(start, start + page_size)

    return query.all()


def load_categories():
    return Category.query.all()


def count_books(cate_id=None):
    query = Book.query
    if cate_id:
        query = query.filter(Book.category_id == cate_id)
    return query.count()


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

    password = str(hashlib.md5(password.encode('utf-8')).hexdigest())

    return User.query.filter(User.username.__eq__(username),User.password.__eq__(password)).first()


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


def load_favorite(user_id):
    # Truy vấn các sản phẩm yêu thích của người dùng
    favorites = Favorite.query.filter(Favorite.customer_id == user_id).all()

    # Trả về thông tin sách từ bảng Book thông qua mối quan hệ
    favorite_books = [favorite.book for favorite in favorites]
    return favorite_books

# dem so luong sp trong tung cate ghi de len trang chu
def category_stats():
    return db.session.query(Category.id, Category.name, func.count(Book.id))\
                     .join(Book, Category.id.__eq__(Book.category_id), isouter=True)\
                     .group_by(Category.id, Category.name).all()

# thong ke doanh thu theo tung cate (loc theo name + khoang thoi gian)
def category_revenue_stats(kw=None, from_date=None, to_date=None):
    p = (db.session.query(
        Category.id,
        Category.name,
        func.sum(DetailInvoice.quantity * Book.price).label('revenue'))\
         .join(Book, Category.id.__eq__(Book.category_id))\
         .join(DetailInvoice, DetailInvoice.book_id.__eq__(Book.id), isouter=True)\
         .join(SaleInvoice, SaleInvoice.id.__eq__(DetailInvoice.saleInvoice_id), isouter=True)\
         .group_by(Category.id, Category.name))

    if kw:
        p = p.filter(Category.name.contains(kw))

    if from_date:
        p = p.filter(SaleInvoice.orderDate.__ge__(from_date))

    if to_date:
        p = p.filter(SaleInvoice.orderDate.__le__(to_date))

    return p.all()

# thong ke doanh thu theo cate loc theo nam
def category_revenue_month(year):
    return db.session.query(extract('month', SaleInvoice.orderDate), func.sum(DetailInvoice.quantity * Book.price))\
                     .join(DetailInvoice, DetailInvoice.saleInvoice_id.__eq__(SaleInvoice.id))\
                     .join(Book, DetailInvoice.book_id == Book.id)\
                     .filter(extract('year', SaleInvoice.orderDate) == year)\
                     .group_by(extract('month', SaleInvoice.orderDate)).all()

def book_quantity_month(year, month=None):
    query = db.session.query(
        extract('month', SaleInvoice.orderDate),
        Book.name,
        func.sum(DetailInvoice.quantity)
    ).join(DetailInvoice, DetailInvoice.saleInvoice_id == SaleInvoice.id)\
     .join(Book, Book.id == DetailInvoice.book_id)\
     .filter(extract('year', SaleInvoice.orderDate) == year)\
     .filter(SaleInvoice.paymentStatus == 'Paid')

    if month:
        query = query.filter(extract('month', SaleInvoice.orderDate) == month)

    return query.group_by(extract('month', SaleInvoice.orderDate), Book.name).all()

# ========================= KIỂM TRA QUY ĐỊNH
def get_current_regulations():
    return Regulation.query.order_by(Regulation.updated_date.desc()).first()

# kiểm tra điều kiện nhập hàng
def check_import_conditions(book_id):
    regulations = get_current_regulations()
    book = Book.query.get(book_id)

    if book.quantity >= regulations.min_stock_before_import:
        return False, f"Số lượng tồn ({book.quantity}) vẫn còn nhiều hơn mức cho phép nhập ({regulations.min_stock_before_import})"

    return True, None

def check_min_import_quantity(quantity):
    regulations = get_current_regulations()

    if quantity < regulations.min_import_quantity:
        return False, f"Số lượng nhập ({quantity}) phải lớn hơn hoặc bằng số lượng tối thiểu ({regulations.min_import_quantity})"

    return True, None

# kiểm tra hủy đơn tự động
def check_order_cancellation():
    regulations = get_current_regulations()
    cancel_time = regulations.order_cancel_time

    # Tìm các đơn hàng quá hạn
    overdue_orders = SaleInvoice.query.filter(
        SaleInvoice.orderDate <= datetime.now() - timedelta(hours=cancel_time),
        SaleInvoice.paymentStatus == 'Pending'
    ).all()

    return overdue_orders

def get_cart_details(sale_invoice_id):
    # Truy vấn chi tiết giỏ hàng của một đơn hàng
    return db.session.query(CartDetail, Book).join(Book).filter(CartDetail.saleInvoice_id == sale_invoice_id).all()
