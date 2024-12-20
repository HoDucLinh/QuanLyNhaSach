import json
import math
from calendar import error

from flask import render_template, request, redirect, session, url_for, jsonify, flash
from pyexpat.errors import messages
from sqlalchemy import func

from bookstoremanagement import app, dao, db , login
from bookstoremanagement.models import Cart, CartDetail, Book, SaleInvoice, DetailInvoice
from flask_login import login_user, current_user, logout_user, login_required
import cloudinary.uploader

from bookstoremanagement.dao import check_import_conditions, check_min_import_quantity
from bookstoremanagement.tasks import init_scheduler

app.secret_key = "123456"

@app.route('/')
def home_page():
    flag = 0
    books = []
    q = request.args.get("q")
    if q:
        books = dao.load_books(kw=q)
        flag = 1
    return render_template('index.html' , books = books , flag =flag)


@app.route('/popular')
def popular_page():
    # Count the number of favorites for each book, limit to top 4
    popular_books = db.session.query(
        Favorite.book_id,
        func.count(Favorite.book_id).label('favorite_count')
    ).group_by(Favorite.book_id) \
     .order_by(func.count(Favorite.book_id).desc()) \
     .limit(4).all()

    # Now, fetch the book details based on the popular books
    books = []
    for book_id, favorite_count in popular_books:
        book = Book.query.get(book_id)
        books.append({
            'book': book,
            'favorite_count': favorite_count
        })

    return render_template('popularbook.html', books=books)


@app.route('/ourstore')
def our_store_page():
    # Lấy danh mục
    cates = dao.load_categories()

    # Lấy category_id và page từ tham số URL
    cate_id = request.args.get('category_id')
    page = request.args.get("page", 1, type=int)  # Đặt giá trị mặc định cho page là 1 nếu không có tham số

    # Lấy danh sách sách và tổng số sách theo danh mục (hoặc tất cả nếu không có category_id)
    if cate_id:
        books = dao.load_books(cate_id=cate_id, page=page)
        total = dao.count_books(cate_id=cate_id)
    else:
        books = dao.load_books(page=page)
        total = dao.count_books()

    # Tính số trang
    pages = math.ceil(total / app.config["PAGE_SIZE"])

    return render_template(
        'ourstore.html',
        categories=cates,
        books=books,
        active_cate_id=cate_id,
        pages=pages
    )

@app.route('/login',methods=['get','post'])
def user_login_page():
    err_msg = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = dao.auth_user(username, password)
        if user:
            login_user(user)
            # Kiểm tra nếu là admin thì chuyển về trang admin
            if user.user_role == UserRole.ADMIN:
                return redirect('/admin')
            if user.user_role == UserRole.SALE:
                return render_template('sale_employee.html')
            # Nếu không phải admin thì chuyển về trang chủ
            return redirect('/')
        else:
            err_msg = "Tài khoản hoặc mật khẩu không đúng!"
    return render_template('login.html', err_msg = err_msg)

@login.user_loader
def load_user(user_id):
    return dao.load_user_by_id(user_id)


@app.route('/register' , methods = ['GET','POST'])
def register_page():
    msg = None
    if request.method.__eq__('POST'):
        password = request.form.get('password')
        re_password = request.form.get('confirm')
        if re_password.__eq__(password):
            avatar = request.files.get('avatar')
            name = request.form.get('name')
            username = request.form.get('username')
            email = request.form.get('email')
            avatar_path = None
            if avatar:
                res = cloudinary.uploader.upload(avatar)
                avatar_path = res['secure_url']
            dao.add_user(name , username, password, avatar_path, email)
            return  redirect('/login')
        else:
            msg = "Xac nhan mat khau chua dung"
    return render_template("register.html" , err_msg = msg)


# Sale Employee
@app.route('/sale-employee')
@login_required
def sale_employee_page():
    if session.get('user_role') == 'sale':
        return render_template('sale_employee.html')
    return redirect(url_for('user_login_page'))

# Quản lý sách
@app.route('/view-books', methods = ['GET'])
def view_books():

    #Load toàn bộ danh mục và sách
    books = dao.load_books()
    categories = dao.load_categories()

    # Lưu thể loại được chọn
    selected_category_name = None

    # Lấy giá trị từ tham số
    category_id = request.args.get('category_id', type=int)
    search_book = request.args.get('search_book','')

    # Lọc sách theo thể loại
    if category_id:
        books = Book.query.filter_by(category_id=category_id).all()
        selected_category = Category.query.get(category_id)
        if selected_category:
            selected_category_name = selected_category.name
    else:
        books = Book.query.all()

    # Tìm sách theo từ khóa
    if search_book:
        books = [book for book in books if search_book.lower() in book.name.lower()]

    return render_template('view_books.html', books=books, categories=categories, selected_category_name=selected_category_name)

# Tạo hóa đơn
@app.route('/create-invoice', methods=['GET', 'POST'])
def create_invoice():
    books = dao.load_books()

    if request.method == 'POST':
        customer_name = request.form.get('customer_name')  # Lấy tên khách hàng từ form
        order_date = request.form.get('orderDate')  # Lấy ngày đặt hàng từ form
        sale_id = current_user.id  # Lấy ID người bán từ người dùng hiện tại

        # Tạo hóa đơn mới
        invoice = SaleInvoice(
            customer_name=customer_name,
            orderDate=order_date,
            sale_id=sale_id
        )
        db.session.add(invoice)
        db.session.flush()

        # Lấy dữ liệu sách và số lượng từ form
        customer_name = request.form.get('customer_name')
        book_ids = request.form.getlist('books[]')
        quantities = request.form.getlist('quantities[]')
        prices = request.form.getlist('prices[]')

        # Tạo các chi tiết hóa đơn cho từng sách
        for book_id, quantity, price in zip(book_ids, quantities, prices):
            if book_id and quantity:
                item = DetailInvoice(
                    saleInvoice_id=invoice.id,
                    book_id=int(book_id),
                    quantity=int(quantity)
                )
                db.session.add(item)

        db.session.commit()
        flash('Tạo hóa đơn thành công', 'success')
        return redirect(url_for('invoice_list'))
    return render_template('create_invoice.html', books=books)

# Danh sách các hóa đơn
@app.route('/create-invoice/list')
@login_required
def invoice_list():
    invoices = dao.load_invoice(current_user.id)
    return render_template('invoice_list.html', invoices=invoices)

# Nhập sách vào kho
@app.route('/import-book', methods = ['GET', 'POST'])
def import_books():
    if request.method == 'POST':
        book_id = request.form.get('book_id')
        quantity_to_import = int(request.form.get('quantity'))

        # Kiểm tra điều kiện nhập hàng
        is_valid, message = check_import_conditions(book_id)

        if not is_valid:
            flash(message, 'danger')
            return redirect(url_for('import_books'))

        is_valid_min_quantity, message_min_quantity = check_min_import_quantity(quantity_to_import)
        if not is_valid_min_quantity:
            flash(message_min_quantity, 'danger')
            return redirect(url_for('import_books'))

        # Nếu điều kiện nhập hàng hợp lệ
        book = dao.load_books(book_id)  # Tải sách từ cơ sở dữ liệu
        if not book:
            flash("Sách không tồn tại", 'danger')
            return redirect(url_for('import_books'))

        # Cập nhật số lượng sách
        book.quantity += quantity_to_import
        db.session.commit()

        flash(f"Đã nhập {quantity_to_import} cuốn {book.name} vào kho", 'success')
        return redirect(url_for('import_books'))

    books = dao.load_books()
    return render_template('import_book.html', books=books)

# Các đơn hàng Online và nhận tại Store
@app.route('/orders')
def show_orders():
    orders = SaleInvoice.query.all()
    overdue_orders = dao.check_order_cancellation()

    for order in orders:
        if order in overdue_orders:
            order.paymentStatus = 'Cancelled'

    db.session.commit()
    return render_template('orders.html', orders=orders)


@app.route('/order_detail/orderNO_<int:saleInvoice_id>', methods=['GET', 'POST'])
def order_detail(saleInvoice_id):
    sale_invoice = SaleInvoice.query.get_or_404(saleInvoice_id)
    details = DetailInvoice.query.filter_by(saleInvoice_id=saleInvoice_id).all()

    if request.method == 'POST':
        if sale_invoice.paymentStatus == 'Pending':
            sale_invoice.paymentStatus = 'Paid'
            db.session.commit()
            flash('Thanh toán đã được xác nhận!', 'success')  # Thông báo thành công
            return redirect(url_for('show_orders'))  # Chuyển hướng về danh sách đơn hàng sau khi cập nhật

    return render_template('order_detail.html', sale_invoice=sale_invoice, details=details)

@app.route('/customers', methods = ['GET'])
def customers():
    orders = SaleInvoice.query.filter(SaleInvoice.customer_id==None).all()
    return render_template('customers.html', orders=orders)

@app.route('/customers_detail/<int:saleInvoice_id>', methods = ['GET'])
def customer_detail(saleInvoice_id):
    sale_invoice = SaleInvoice.query.get(saleInvoice_id)
    details = db.session.query(
        Book.name,
        DetailInvoice.quantity,
        (DetailInvoice.quantity * Book.price).label('total_price')
    ).join(DetailInvoice, Book.id == DetailInvoice.book_id) \
    .filter(DetailInvoice.saleInvoice_id == saleInvoice_id).all()
    return render_template('customers_detail.html', sale_invoice=sale_invoice, details=details)

@app.route('/invoice/view/<int:invoice_id>')
@login_required
def view_invoice(invoice_id):
    invoice = SaleInvoice.query.get_or_404(invoice_id)
    return render_template('view_invoice.html', invoice=invoice)

@app.route('/payment' , methods=['POST'])
def payment_page():
    totalAmount = 0
    cart = Cart.query.filter_by(user_id=current_user.id).first()
    cart_details = CartDetail.query.filter_by(cart_id=cart.id).all()  # Ensure you're querying by cart_id
    books = []  # Will hold full book objects

    for b in cart_details:
        book = Book.query.filter_by(id=b.book_id).first()
        if book:
            books.append({
                'book': book,
                'quantity': b.quantity
            })
            totalAmount += b.quantity * book.price

    return render_template('payment.html', books=books, totalAmount=totalAmount)

@app.route('/checkout' , methods=['POST'])
@login_required
def check_out():
    if request.method == 'POST':
        shipping_method = request.form.get('shippingMethod')
        selection = request.form.get('selection')
        if shipping_method == 'homeDelivery' or (shipping_method == 'storePickup' and selection == 'payOnline'):
            invoice = SaleInvoice(
                paymentStatus='Paid',
                customer_name=current_user.name,
                customer_id=current_user.id,
                sale_id=None,
                orderDate=datetime.utcnow()
            )
            db.session.add(invoice)
            db.session.commit()
            cart = Cart.query.filter_by(user_id=current_user.id).first()
            cart_details = CartDetail.query.filter_by(cart_id=cart.id).all()
            for c in cart_details:
                detail_invoice = DetailInvoice(
                    book_id=c.book_id,
                    saleInvoice_id=invoice.id,
                    quantity=c.quantity
                )
                db.session.add(detail_invoice)
            db.session.commit()
            cart = Cart.query.filter_by(user_id=current_user.id).first()
            cart_detail = CartDetail.query.filter_by(cart_id=cart.id).all()
            for c in cart_detail:
                db.session.delete(c)
            db.session.commit()
            return redirect('/account')
        elif shipping_method == 'storePickup' and selection == 'payAtStore':
            invoice = SaleInvoice(
                paymentStatus='Pending',
                customer_name=current_user.name,
                customer_id=current_user.id,
                sale_id=None,
                orderDate=datetime.utcnow()
            )
            db.session.add(invoice)
            db.session.commit()
            cart = Cart.query.filter_by(user_id=current_user.id).first()
            cart_details = CartDetail.query.filter_by(cart_id=cart.id).all()
            for c in cart_details:
                detail_invoice = DetailInvoice(
                    book_id=c.book_id,
                    saleInvoice_id=invoice.id,
                    quantity=c.quantity
                )
                db.session.add(detail_invoice)
            db.session.commit()
            cart = Cart.query.filter_by(user_id=current_user.id).first()
            cart_detail = CartDetail.query.filter_by(cart_id=cart.id).all()
            for c in cart_detail:
                db.session.delete(c)
            db.session.commit()
            return redirect('/account')
    return render_template('payment.html')


@app.route('/account')
@login_required
def account_page():
    invoices = dao.load_invoice(current_user.id)  # Lấy hóa đơn cho user hiện tại
    favorites = dao.load_favorite(current_user.id)  # Lấy danh sách sách yêu thích của người dùng
    invoice_details = {}  # Sử dụng dictionary để chứa chi tiết hóa đơn

    # Lấy chi tiết hóa đơn cho mỗi hóa đơn
    for invoice in invoices:
        details = dao.load_invoice_details(invoice.id)  # Truy vấn chi tiết hóa đơn
        invoice_details[invoice.id] = details  # Lưu chi tiết hóa đơn vào dictionary theo ID của hóa đơn

    return render_template('accountcustomer.html', invoices=invoices, favorites=favorites, invoice_details=invoice_details)


@app.route('/cart')
def cart_page():
    books_in_cart = []
    total_price = 0
    if current_user.is_authenticated:
        user_id = current_user.id
        cart = Cart.query.filter_by(user_id=user_id).first()  # Assuming cart_id is 1
        if not cart:
            return render_template('cart.html', books=[], total_price=0)  # Return empty cart if no cart is found

        # Get the cart details (products in the cart)
        cart_details = CartDetail.query.filter_by(cart_id=cart.id).all()

        for detail in cart_details:
            book = Book.query.get(detail.book_id)
            if book:
                books_in_cart.append({
                    'name': book.name,
                    'price': book.price,
                    'quantity': detail.quantity,
                    'total': book.price * detail.quantity,
                    'book_id': book.id,
                    'image': book.image,
                    'description': book.description
                })
        for b in books_in_cart:
            total_price += b['total']
    else :
        return redirect('/login')

    return render_template('cart.html', books=books_in_cart, total_price=total_price)


@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    # Lấy dữ liệu từ form
    book_id = request.form.get('book_id')

    if current_user.is_authenticated:  # Nếu không có user_id, yêu cầu đăng nhập
        user_id = current_user.id  # Lấy ID người dùng
        dao.insert_book_to_cart(user_id , book_id)
        flash('Them vao gio hang thanh cong!!!')
        return redirect('/ourstore')

    return redirect('/ourstore')


@app.route('/remove_from_cart', methods=['POST'])
def remove_from_cart():
    user_id = current_user.id
    if not user_id:
        return redirect('/login')  # Nếu chưa đăng nhập, chuyển hướng tới trang login

    book_id = request.form.get('book_id')

    # Truy vấn giỏ hàng của người dùng
    cart = Cart.query.filter_by(user_id=user_id).first()
    if not cart:
        return redirect('/cart')  # Nếu không có giỏ hàng, quay lại trang giỏ hàng

    # Xóa sản phẩm khỏi giỏ hàng
    cart_detail = CartDetail.query.filter_by(cart_id=cart.id, book_id=book_id).first()
    if cart_detail:
        db.session.delete(cart_detail)
        db.session.commit()

    return redirect('/cart')  # Quay lại trang giỏ hàng sau khi xóa


@app.route('/delete_from_favorite', methods=['POST'])
def delete_from_favorite():
    user_id = current_user.id
    if not user_id:
        return redirect('/login')  # Nếu chưa đăng nhập, chuyển hướng tới trang login

    book_id = request.form.get('book_id')

    # Truy vấn favorite của người dùng và tìm sản phẩm yêu thích theo book_id
    favorite_detail = Favorite.query.filter_by(customer_id=user_id, book_id=book_id).first()
    # Xóa sản phẩm khỏi danh sách yêu thích
    db.session.delete(favorite_detail)
    db.session.commit()
    return redirect('/account')  # Quay lại trang tài khoản sau khi xóa


@app.route('/logout')
def logout_my_user():
    logout_user()
    return redirect('/login')


@app.route('/update_quantity', methods=['POST'])
def update_quantity():
    book_id = request.form.get('book_id')
    new_quantity = int(request.form.get('quantity'))
    cart = Cart.query.filter_by(user_id=current_user.id).first()

    # Tìm sản phẩm và cập nhật số lượng
    cart_detail = CartDetail.query.filter_by(book_id=book_id, cart_id=cart.id).first()
    if cart_detail:
        cart_detail.quantity = new_quantity
        db.session.commit()
        flash('Cập nhật số lượng thành công!', 'success')
    # Redirect về trang giỏ hàng
    return redirect('/cart')


@app.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    err_msg = None
    if request.method == 'POST':
        # Lấy thông tin từ form
        name = request.form.get('name')
        email = request.form.get('email')
        old_password = request.form.get('old_password')
        new_password = request.form.get('new_password')
        avatar = request.files.get('new_avatar')
        avatar_path = None

        # Cờ để theo dõi nếu có thay đổi
        updated = False

        # Kiểm tra và cập nhật tên
        if name and name != current_user.name:
            current_user.name = name
            updated = True

        # Kiểm tra và cập nhật email
        if email and email != current_user.email:
            current_user.email = email
            updated = True

        # Kiểm tra và cập nhật mật khẩu
        if old_password and new_password:
            old_password = str(hashlib.md5(old_password.encode('utf-8')).hexdigest())
            if current_user.password.__eq__(old_password):
                new_password = str(hashlib.md5(new_password.encode('utf-8')).hexdigest())
                current_user.password = new_password
                updated = True
            else:
                err_msg = "Mat khau khong dung!!!"
                return render_template('editprofile.html' , msg = err_msg)
        if avatar:
            res = cloudinary.uploader.upload(avatar)
            avatar_path = res['secure_url']
            current_user.avatar = avatar_path
            updated = True
        # Nếu có thay đổi, lưu vào cơ sở dữ liệu
        if updated:
            db.session.commit()
            err_msg = "Cap nhat thanh cong"

    # Phương thức GET: hiển thị form
    return render_template('editprofile.html' , msg = err_msg)


@app.route('/toggle_favorite', methods=['POST'])
@login_required
def toggle_favorite():
    data = request.get_json()
    book_id = data['book_id']
    user_id = data['user_id']
    action = data['action']

    if action == 'add':
        # Kiểm tra xem sản phẩm đã có trong bảng yêu thích chưa
        existing_favorite = Favorite.query.filter_by(book_id=book_id, customer_id=user_id).first()
        if not existing_favorite:
            new_favorite = Favorite(book_id=book_id, customer_id=user_id)
            db.session.add(new_favorite)
            db.session.commit()
            return jsonify({'success': True})
        return jsonify({'success': False, 'message': 'Book already in favorites'})

    elif action == 'remove':
        # Xóa sản phẩm khỏi bảng yêu thích
        favorite = Favorite.query.filter_by(book_id=book_id, customer_id=user_id).first()
        if favorite:
            db.session.delete(favorite)
            db.session.commit()
            return jsonify({'success': True})
        return jsonify({'success': False, 'message': 'Favorite not found'})

    return jsonify({'success': False, 'message': 'Invalid action'})

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated and current_user.user_role == UserRole.ADMIN:
        return redirect('/admin')

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = dao.auth_user(username, password)

        if user and user.user_role == UserRole.ADMIN:
            login_user(user)
            return redirect('/admin')
        else:
            flash('Invalid username or password or not admin role', 'error')

    return render_template('login.html')

if __name__ == '__main__':
    from bookstoremanagement.admin import *
    init_scheduler()
    app.run(debug=True)
