from flask import render_template, request, redirect, session, url_for

from bookstoremanagement import app, dao

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

        print(f"Email: {email}, Password: {password}")

        # Kiểm tra đăng nhập
        if email == ('customer@gmail.com') and password == ('123456'):
            session['user_role'] = 'customer'
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
@app.route('/cart')
def cart_page():
    return render_template('cart.html')

@app.route('/payment')
def payment_page():
    return render_template('payment.html')

@app.route('/account')
def account_page():
    if session.get('user_role') == 'customer':
        return render_template('accountcustomer.html')
    return redirect(url_for('user_login_page'))

if __name__ == '__main__':
    app.run(debug=True)
