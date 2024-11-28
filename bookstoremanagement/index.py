from flask import render_template, request, redirect, session, url_for, jsonify

from bookstoremanagement import app, dao, db
from bookstoremanagement.models import Cart, CartDetail, Book

app.secret_key = "123456"

@app.route('/')
def home_page():
    return render_template('index.html')


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
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')


        # Kiểm tra đăng nhập
        if email == ('customer@gmail.com') and password == ('123456'):
            session['user_role'] = 'customer'
            session['user_id'] = 1
            return redirect("/account")
        elif email == ('sale@gmail.com') and password == ('456123'):
            session['user_role'] = 'sale'
            return redirect("/sale-employee")
        elif email == ('admin@gmail.com') and password == ('123456'):
            session['user_role'] = 'admin'
            return redirect("/admin")
    return render_template('login.html')

@app.route('/register')
def register_page():
    return render_template('register.html')

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
@app.route('/payment')
def payment_page():
    return render_template('payment.html')

@app.route('/account')
def account_page():
    if session.get('user_role') == 'customer':
        return render_template('accountcustomer.html')
    return redirect(url_for('user_login_page'))


@app.route('/cart')
def cart_page():
    user_id = session.get('user_id')  # Get user ID from session
    if not user_id:
        return redirect('/login')  # Redirect to login if the user is not logged in

    # Get the cart for the customer with cart_id = 1
    cart = Cart.query.filter_by(id=1, customer_id=user_id).first()  # Assuming cart_id is 1
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
    user_id = session.get('user_id')  # Lấy ID người dùng từ session

    if not user_id:  # Nếu không có user_id, yêu cầu đăng nhập
        return jsonify({"error": "Bạn phải đăng nhập"}), 401

    # Kiểm tra xem người dùng đã có giỏ hàng chưa
    cart = Cart.query.filter_by(customer_id=user_id).first()
    if not cart:
        # Tạo mới giỏ hàng nếu chưa có
        cart = Cart(customer_id=user_id)
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
    return jsonify({"message": "Sản phẩm đã được thêm vào giỏ hàng"}), 200

@app.route('/remove_from_cart', methods=['POST'])
def remove_from_cart():
    user_id = session.get('user_id')  # Lấy ID người dùng từ session
    if not user_id:
        return redirect('/login')  # Nếu chưa đăng nhập, chuyển hướng tới trang login

    book_id = request.form.get('book_id')

    # Truy vấn giỏ hàng của người dùng
    cart = Cart.query.filter_by(customer_id=user_id).first()
    if not cart:
        return redirect('/cart')  # Nếu không có giỏ hàng, quay lại trang giỏ hàng

    # Xóa sản phẩm khỏi giỏ hàng
    cart_detail = CartDetail.query.filter_by(cart_id=cart.id, book_id=book_id).first()
    if cart_detail:
        db.session.delete(cart_detail)
        db.session.commit()

    return redirect('/cart')  # Quay lại trang giỏ hàng sau khi xóa


if __name__ == '__main__':
    app.run(debug=True)
