from flask import render_template, request, redirect, session, url_for, jsonify, flash

from bookstoremanagement import app, dao, db , login
from bookstoremanagement.models import Cart, CartDetail, Book
from flask_login import login_user, current_user , logout_user
import cloudinary.uploader

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
    return render_template('popularbook.html')

@app.route('/ourstore')
def our_store_page():
    # Lấy danh mục
    cates = dao.load_categories()

    # Lấy category_id từ tham số URL
    cate_id = request.args.get('category_id')

    # Nếu không có category_id, lấy tất cả sách
    books = dao.load_books() if not cate_id else dao.load_books(cate_id=cate_id)

    return render_template('ourstore.html', categories=cates, books=books ,active_cate_id=cate_id)

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

@app.route('/admin')
def admin_page():
    if session.get('user_role') == 'admin':
        return render_template('admin.html')
    return redirect(url_for('user_login_page'))
@app.route('/sale-employee')
def sale_employee_page():
    if session.get('user_role') == 'sale':
        return render_template('sale_employee.html')
    return redirect(url_for('user_login_page'))
@app.route('/payment' , methods=['POST'])
def payment_page():
    return render_template('payment.html')

@app.route('/account')
def account_page():
    if session.get('user_role') == 'customer':
        return render_template('accountcustomer.html')
    return redirect(url_for('user_login_page'))


@app.route('/cart')
def cart_page():
    user_id = current_user.id  # Get user ID from session
    if not user_id:
        return redirect('/login')  # Redirect to login if the user is not logged in

    # Get the cart for the customer with cart_id = 1
    cart = Cart.query.filter_by(user_id=user_id).first()  # Assuming cart_id is 1
    if not cart:
        return render_template('cart.html', books=[], total_price=0)  # Return empty cart if no cart is found

    # Get the cart details (products in the cart)
    cart_details = CartDetail.query.filter_by(cart_id=cart.id).all()

    # Create list of books in the cart and calculate total price
    books_in_cart = []
    total_price = 0
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
            total_price += book.price * detail.quantity

    return render_template('cart.html', books=books_in_cart, total_price=total_price)

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    # Lấy dữ liệu từ form
    book_id = request.form.get('book_id')
    user_id = current_user.id  # Lấy ID người dùng từ session

    if not user_id:  # Nếu không có user_id, yêu cầu đăng nhập
        return jsonify({"error": "Bạn phải đăng nhập"}), 401

    dao.insert_book_to_cart(user_id , book_id)

    return jsonify({"message": "Sản phẩm đã được thêm vào giỏ hàng"}), 200

@app.route('/remove_from_cart', methods=['POST'])
def remove_from_cart():
    user_id = current_user.id  # Lấy ID người dùng từ session
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


@app.route('/logout')
def logout_my_user():
    logout_user()
    return redirect('/login')


@app.route('/update_quantity', methods=['POST'])
def update_quantity():
    user_id = session.get('user_id')  # Lấy ID người dùng từ session
    if not user_id:
        return redirect('/login')  # Yêu cầu đăng nhập nếu chưa có user_id

    book_id = request.form.get('book_id')  # Lấy book_id từ form
    quantity = int(request.form.get('quantity'))  # Lấy số lượng mới

    # Lấy giỏ hàng của người dùng
    cart = Cart.query.filter_by(user_id=user_id).first()
    if not cart:
        return redirect('/cart')  # Nếu không có giỏ hàng, quay lại trang giỏ hàng

    # Tìm sản phẩm trong giỏ hàng
    cart_detail = CartDetail.query.filter_by(cart_id=cart.id, book_id=book_id).first()
    if cart_detail:
        if quantity > 0:
            # Cập nhật số lượng
            cart_detail.quantity = quantity
            db.session.commit()
        else:
            # Nếu số lượng = 0, xóa sản phẩm khỏi giỏ hàng
            db.session.delete(cart_detail)
            db.session.commit()

    return redirect('/cart')  # Quay lại trang giỏ hàng

if __name__ == '__main__':
    app.run(debug=True)
