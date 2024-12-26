import math
from flask import render_template, request, redirect, session, url_for, jsonify, flash
from sqlalchemy import func
from bookstoremanagement import app, dao, db, login
from bookstoremanagement.models import Cart, CartDetail, Book, SaleInvoice, DetailInvoice
from flask_login import login_user, current_user, logout_user, login_required
import cloudinary.uploader
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
    return render_template('index.html', books=books, flag=flag)


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


@app.route('/login', methods=['get', 'post'])
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
                return redirect('/create-invoice')
            # Nếu không phải admin thì chuyển về trang chủ
            return redirect('/')
        else:
            err_msg = "Tài khoản hoặc mật khẩu không đúng!"
    return render_template('login.html', err_msg=err_msg)


@login.user_loader
def load_user(user_id):
    return dao.load_user_by_id(user_id)


@app.route('/register', methods=['GET', 'POST'])
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
            dao.add_user(name, username, password, avatar_path, email)
            return redirect('/login')
        else:
            msg = "Xac nhan mat khau chua dung"
    return render_template("register.html", err_msg=msg)


# Sale Employee
@app.route('/sale-employee')
# @login_required()
def sale_employee_page():
    if session.get('user_role') == 'sale':
        return render_template('create_invoice.html')
    return redirect(url_for('user_login_page'))


# Quản lý sách
@app.route('/view-books', methods=['GET'])
def view_books():
    #Load toàn bộ danh mục và sách
    books = dao.load_books()
    categories = dao.load_categories()

    # Lưu thể loại được chọn
    selected_category_name = None

    # Lấy giá trị từ tham số
    category_id = request.args.get('category_id', type=int)
    search_book = request.args.get('search_book', '')

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

    return render_template('view_books.html', books=books, categories=categories,
                           selected_category_name=selected_category_name)


# Tạo hóa đơn
@app.route('/create-invoice', methods=['GET', 'POST'])
def create_invoice():
    books = dao.load_books()
    err_msg = None
    print(books)
    if request.method == 'POST':
        customer_name = request.form.get('customer_name')  # Lấy tên khách hàng từ form
        order_date = request.form.get('orderDate')  # Lấy ngày đặt hàng từ form
        sale_id = current_user.id  # Lấy ID người bán từ người dùng hiện tại

        # Lấy dữ liệu sách và số lượng từ form
        customer_name = request.form.get('customer_name')
        book_ids = request.form.getlist('books[]')
        quantities = request.form.getlist('quantities[]')
        prices = request.form.getlist('prices[]')

        # Kiểm tra số lượng sách mua
        for book_id, quantity in zip(book_ids,quantities):
            book = dao.load_books(book_id==book_id)
            if book_id and int(quantity)>book.quantity:
                err_msg = f"Số lượng sách '{book.name}' yêu cầu vượt quá số lượng tồn kho ({book.quantity})."
                return render_template("create_invoice.html", books=books, err_msg=err_msg)

        # Tạo hóa đơn mới
        invoice = SaleInvoice(
            customer_name=customer_name,
            orderDate=order_date,
            sale_id=sale_id,
            paymentStatus='Paid'
        )
        db.session.add(invoice)
        db.session.flush()

        # Tạo các chi tiết hóa đơn cho từng sách
        for book_id, quantity, price in zip(book_ids, quantities, prices):
            if book_id and quantity:
                item = DetailInvoice(
                    saleInvoice_id=invoice.id,
                    book_id=int(book_id),
                    quantity=int(quantity)
                )
                db.session.add(item)

                dao.updateQuantityBook(int(book_id), int(quantity))

        db.session.commit()
        return redirect(url_for('view_invoice', saleInvoice_id=invoice.id))
    return render_template("create_invoice.html", books=books)


# Danh sách các hóa đơn
@app.route('/invoice/view/<int:saleInvoice_id>', methods=['GET'])
@login_required
def view_invoice(saleInvoice_id):
    sale_invoice, details, total_amount = dao.view_invoice(saleInvoice_id)

    # Trả về kết quả cho view (template)
    return render_template('view_invoice.html', saleInvoice_id=saleInvoice_id, sale_invoice=sale_invoice,
                           details=details, total_amount=total_amount)


# Nhập sách vào kho
@app.route('/import-book', methods=['GET', 'POST'])
def import_books():
    regulations = dao.get_current_regulations()
    err_msg = None  # Khai báo err_msg ở ngoài vòng lặp
    if request.method == 'POST':
        book_ids = request.form.getlist('book_id[]')
        quantities = request.form.getlist('quantity[]')
        import_details = []

        for book_id, quantity in zip(book_ids, quantities):
            if book_id and quantity:
                quantity = int(quantity)

                # Kiểm tra điều kiện nhập hàng
                is_valid, message = dao.check_import_conditions(book_id)
                if not is_valid:
                    book = dao.load_books(book_id)
                    if book:
                        err_msg = f"Số lượng tồn ({book.quantity}) vẫn còn nhiều hơn mức cho phép nhập ({regulations.min_stock_before_import})"
                    break  # Dừng lại nếu có lỗi

                is_valid_min_quantity, message_min_quantity = dao.check_min_import_quantity(quantity)
                if not is_valid_min_quantity:
                    err_msg = f"Số lượng nhập ({quantity}) phải lớn hơn hoặc bằng số lượng tối thiểu ({regulations.min_import_quantity})"
                    break  # Dừng lại nếu có lỗi

                book = dao.load_books(book_id)
                if not book:
                    err_msg = "Sách với ID {book_id} không tồn tại"
                    break  # Dừng lại nếu có lỗi

                # Cập nhật số lượng sách
                book.quantity += quantity
                import_details.append({
                    'book': book,
                    'quantity': quantity
                })

        if import_details:
            db.session.commit()
            # Tạo hóa đơn nhập
            import_invoice = {
                'date': datetime.now(),
                'staff_name': current_user.name,
                'details': import_details
            }
            return render_template('import_invoice.html', invoice=import_invoice)

        return render_template('import_book.html', books=dao.load_books(), err_msg=err_msg)  # Trả err_msg vào template

    books = dao.load_books()
    return render_template('import_book.html', books=books, err_msg=err_msg)



# Các đơn hàng Online và nhận tại Store
@app.route('/orders')
def show_orders():
    orders = SaleInvoice.query.filter(SaleInvoice.sale_id == None).all()
    overdue_orders = dao.check_order_cancellation()

    for order in orders:
        if order in overdue_orders:
            order.paymentStatus = 'Cancelled'

    db.session.commit()
    return render_template('orders.html', orders=orders)


@app.route('/order_detail/<int:saleInvoice_id>', methods=['GET', 'POST'])
def order_detail(saleInvoice_id):
    # Lấy hóa đơn và chi tiết hóa đơn từ dao (giả sử bạn đã có phương thức `view_invoice` trong dao)
    sale_invoice, details, total_amount = dao.view_invoice(saleInvoice_id)

    if request.method == 'POST':
        if sale_invoice.paymentStatus == 'Pending':
            sale_invoice.paymentStatus = 'Paid'
            # Cập nhật số lượng sách sau khi thanh toán
            for detail in details:
                book_id = detail.book_id  # Lấy book_id từ chi tiết hóa đơn
                quantity = detail.quantity  # Lấy số lượng sách từ chi tiết
                dao.updateQuantityBook(book_id, quantity)  # Gọi hàm updateQuantityBook để cập nhật số lượng sách
            db.session.commit()
            return redirect(url_for('show_orders'))

    return render_template('order_detail.html', sale_invoice=sale_invoice, details=details, total_amount=total_amount)


@app.route('/customers', methods=['GET'])
def customers():
    orders = SaleInvoice.query.filter(SaleInvoice.customer_id == None).all()
    return render_template('customers.html', orders=orders)


@app.route('/customers_detail/<int:saleInvoice_id>', methods=['GET'])
def customer_detail(saleInvoice_id):
    sale_invoice, details, total_amount = dao.view_invoice(saleInvoice_id)
    return render_template('customers_detail.html', sale_invoice=sale_invoice, details=details,
                           total_amount=total_amount)


@app.route('/payment', methods=['POST'])
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

    return render_template('accountcustomer.html', invoices=invoices, favorites=favorites,
                           invoice_details=invoice_details)


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
    else:
        return redirect('/login')

    return render_template('cart.html', books=books_in_cart, total_price=total_price)


@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    # Lấy dữ liệu từ form
    book_id = request.form.get('book_id')

    if current_user.is_authenticated:  # Nếu không có user_id, yêu cầu đăng nhập
        user_id = current_user.id  # Lấy ID người dùng
        dao.insert_book_to_cart(user_id, book_id)
        return {'status': 'success', 'message': 'Thêm vào giỏ hàng thành công!'}

    return {'status': 'error', 'message': 'Bạn cần đăng nhập để thêm sách vào giỏ hàng.'}, 401


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

    # Tìm sách trong kho
    book = Book.query.filter_by(id=book_id).first()
    if not book:
        return jsonify({'status': 'error', 'message': 'Sách không tồn tại.'}), 400

    # Kiểm tra số lượng sách trong kho
    if new_quantity > book.quantity:
        return jsonify({
            'status': 'error',
            'message': f'Số lượng yêu cầu vượt quá số lượng sách trong kho ({book.quantity}).'
        }), 400

    # Tìm sản phẩm trong giỏ hàng và cập nhật số lượng
    cart_detail = CartDetail.query.filter_by(book_id=book_id, cart_id=cart.id).first()
    if cart_detail:
        cart_detail.quantity = new_quantity
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Cập nhật số lượng thành công.'}), 200

    return jsonify({'status': 'error', 'message': 'Không tìm thấy sản phẩm trong giỏ hàng.'}), 400


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
                flash("Mật khẩu không đúng.")

        # Kiểm tra và cập nhật avatar
        if avatar:
            try:
                res = cloudinary.uploader.upload(avatar)
                avatar_path = res['secure_url']  # Lấy URL của ảnh đã upload
                current_user.avatar = avatar_path  # Cập nhật avatar cho người dùng
                updated = True
            except Exception as e:
                flash(f"Không thể tải ảnh lên: {e}", "error")

        # Nếu có thay đổi, lưu vào cơ sở dữ liệu
        if updated:
            db.session.commit()
            flash("Cập nhật thành công.", "success")
        else:
            flash("Không có thay đổi nào được thực hiện.", "info")

    # Phương thức GET: hiển thị form
    return render_template('editprofile.html')


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


@app.route("/order", methods=["POST"])
def order():
    if request.method == 'POST':
        if request.form.get('shippingMethod') == 'storePickup' and request.form.get('selection') == 'payAtStore':
            user_id = current_user.id
            # Lấy giỏ hàng của người dùng
            cart = Cart.query.filter_by(user_id=user_id).first()
            # Lấy chi tiết giỏ hàng
            cart_details = CartDetail.query.filter_by(cart_id=cart.id).all()
            sale_invoice = SaleInvoice(
                paymentStatus="Pending",
                customer_name=current_user.name,
                customer_id=user_id,
                orderDate=datetime.utcnow()
            )
            db.session.add(sale_invoice)
            db.session.commit()  # Lưu SaleInvoice để có ID
            # Lưu chi tiết hóa đơn từ giỏ hàng vào bảng DetailInvoice
            for detail in cart_details:
                detail_invoice = DetailInvoice(
                    book_id=detail.book_id,
                    saleInvoice_id=sale_invoice.id,
                    quantity=detail.quantity
                )
                db.session.add(detail_invoice)
            CartDetail.query.filter_by(cart_id=cart.id).delete()
            db.session.delete(cart)
            db.session.commit()
            return redirect("account")
        total = request.form.get('total')
        amount = round(float(total))

        # Tạo một instance của ZaloPayDAO
        zalopay_dao = dao.ZaloPayDAO()

        # Tạo đơn hàng và lấy URL thanh toán
        pay_url = zalopay_dao.create_order(amount)

        if "Error" not in pay_url:
            return redirect(pay_url)  # Chuyển hướng đến ZaloPay thanh toán
        else:
            return pay_url  # Trả về thông báo lỗi nếu có


@app.route("/callback", methods=["GET", "POST"])
def callback():
    status = request.args.get("status")
    user_id = current_user.id
    # Lấy giỏ hàng của người dùng
    cart = Cart.query.filter_by(user_id=user_id).first()
    # Lấy chi tiết giỏ hàng
    cart_details = CartDetail.query.filter_by(cart_id=cart.id).all()
    if status == "1":

        sale_invoice = SaleInvoice(
            paymentStatus="Paid",
            customer_name=current_user.name,
            customer_id=user_id,
            orderDate=datetime.utcnow()
        )
        db.session.add(sale_invoice)
        db.session.commit()  # Lưu SaleInvoice để có ID

        # Lưu chi tiết hóa đơn từ giỏ hàng vào bảng DetailInvoice
        for detail in cart_details:
            detail_invoice = DetailInvoice(
                book_id=detail.book_id,
                saleInvoice_id=sale_invoice.id,
                quantity=detail.quantity
            )
            db.session.add(detail_invoice)
            dao.updateQuantityBook(book_id=detail_invoice.book_id, quantity=detail_invoice.quantity)
        CartDetail.query.filter_by(cart_id=cart.id).delete()
        db.session.delete(cart)
        db.session.commit()
        return redirect("account")
    else:
        sale_invoice = SaleInvoice(
            paymentStatus="Cancelled",
            customer_name=current_user.name,
            customer_id=user_id,
            orderDate=datetime.utcnow()
        )
        db.session.add(sale_invoice)
        db.session.commit()  # Lưu SaleInvoice để có ID

        # Lưu chi tiết hóa đơn từ giỏ hàng vào bảng DetailInvoice
        for detail in cart_details:
            detail_invoice = DetailInvoice(
                book_id=detail.book_id,
                saleInvoice_id=sale_invoice.id,
                quantity=detail.quantity
            )
            db.session.add(detail_invoice)
        db.session.commit()
        return redirect("account")



@app.route('/book_revenue-report')
@login_required
def revenue_report():
    year = request.args.get('year', datetime.now().year)
    month = request.args.get('month')

    if month:
        month = int(month)

    book_stats = dao.book_quantity_month(year=year, month=month)

    return render_template('book_revenue_report.html',
                           book_stats=book_stats,
                           year=year,
                           month=month)


@app.route('/category-revenue-report')
@login_required
def category_revenue_report():
    kw = request.args.get('kw')
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')

    stats = dao.category_revenue_detail(kw=kw, from_date=from_date, to_date=to_date)

    return render_template('category_revenue_report.html',
                           stats=stats,
                           from_date=from_date,
                           to_date=to_date)


if __name__ == '__main__':
    from bookstoremanagement.admin import *

    init_scheduler()
    app.run(debug=True)
