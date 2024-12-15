import hashlib
import math

from flask import render_template, request, redirect, session, url_for, jsonify, flash
from sqlalchemy import func

from bookstoremanagement import app, dao, db , login
from bookstoremanagement.models import Cart, CartDetail, Book, SaleInvoice, DetailInvoice, Favorite
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
            return redirect('/')
        else:
            err_msg = "Tài khoản hoặc mật khẩu không đúng!"
    return render_template('login.html' , err_msg = err_msg)


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


@app.route('/sale-employee')
def sale_employee_page():
    if session.get('user_role') == 'sale':
        return render_template('sale_employee.html')
    return redirect(url_for('user_login_page'))


@app.route('/payment', methods=['POST'])
@login_required
def payment_page():
    totalAmount = 0
    cart_id = Cart.query.filter_by(user_id=current_user.id).first()
    cart_details = CartDetail.query.filter_by(cart_id=cart_id.id).all()  # Ensure you're querying by cart_id
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
    favorites = dao.load_favorite(current_user.id) #lấy danh sách sách yêu thích của người dùng
    return render_template('accountcustomer.html', invoices=invoices , favorites= favorites)


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
        return jsonify({'message': 'Added to cart successfully'}), 200

    return jsonify({'error': 'Bạn phải đăng nhập'}), 401


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

    if not favorite_detail:
        flash('Product not found in your favorites.', 'danger')
        return redirect('/account')  # Nếu không có sản phẩm yêu thích, quay lại trang tài khoản

    # Xóa sản phẩm khỏi danh sách yêu thích
    db.session.delete(favorite_detail)
    db.session.commit()

    flash('Product removed from your favorites.', 'success')
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

    return render_template('admin/login.html')

if __name__ == '__main__':
    from bookstoremanagement.admin import *
    init_scheduler()
    app.run(debug=True)
