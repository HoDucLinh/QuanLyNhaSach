from flask_admin import Admin, AdminIndexView, expose, BaseView
from flask_admin.contrib.sqla import ModelView
from bookstoremanagement import app, db
from bookstoremanagement.models import *
from flask_login import current_user, logout_user
from flask import redirect, url_for
from wtforms import SelectField, PasswordField, validators
import dao
from flask import request


# Base ModelView với kiểm tra quyền
class AuthModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.user_role == UserRole.ADMIN

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('admin_login'))

# Các ModelView kế thừa từ AuthModelView
class UserView(AuthModelView):
    can_view_details = True
    column_exclude_list = ['password']
    column_searchable_list = ['username', 'name', 'email']
    column_list = ['id', 'name', 'username','email', 'user_role']

    def scaffold_form(self):
        form_class = super(UserView, self).scaffold_form()
        form_class.user_role = SelectField('User Role',
                                       choices=[(choice.value, choice.name) for choice in UserRole],
                                       coerce=int)
        form_class.password = PasswordField('Password', [
            validators.DataRequired(message='Password không được để trống'),
            validators.Length(min=3, message='Password phải có ít nhất 3 ký tự')
        ])
        return form_class

    def on_model_change(self, form, model, is_created):
        # Kiểm tra password khi tạo mới
        if is_created and not form.password.data:
            raise validators.ValidationError('Password là bắt buộc khi tạo mới user')
            
        # Mã hóa password khi có dữ liệu
        if form.password.data:
            model.password = str(hashlib.md5(form.password.data.strip().encode('utf-8')).hexdigest())
        # Lấy role từ form
        model.user_role = UserRole(form.user_role.data)

# class UserView(AuthModelView):
#     can_view_details = True
#     column_exclude_list = ['password'] # ẩn pass trên lsv
#     form_excluded_columns = ['password'] # ẩn pass khi tạo or chỉnh sửa
#     column_searchable_list = ['username', 'name', 'email']
#
#     # ghi đè để tùy chỉnh biểu mẫu
#     def scaffold_form(self):
#         form_class = super(UserView, self).scaffold_form()
#         form_class.user_role = SelectField('User Role',
#                                          choices=UserRole.choices(),
#                                          coerce=int)
#         return form_class

class CategoryView(AuthModelView):
    can_view_details = True
    column_searchable_list = ['name']
    form_columns = ['name', 'stock_id']
    column_list = ['id','name', 'stock_id']

    def get_stock_choices(self): # Lấy danh sách all stock từ db,  [(1, "Kho A"), (2, "Kho B")]
        return [(stock.id, stock.name) for stock in Stock.query.all()]

    def scaffold_form(self):
        form_class = super(CategoryView, self).scaffold_form()
        form_class.stock_id = SelectField('Stock',
                                        choices=[],  # Để trống choices ban đầu
                                        coerce=int) # Chuyển đổi giá trị được chọn thành số nguyên
        return form_class

    def create_form(self, obj=None):
        form = super(CategoryView, self).create_form(obj)
        form.stock_id.choices = self.get_stock_choices()  # Cập nhật choices khi tạo form
        return form

    def edit_form(self, obj=None):
        form = super(CategoryView, self).edit_form(obj)
        form.stock_id.choices = self.get_stock_choices()  # Cập nhật choices khi sửa form
        return form
#
# Code cũ không dùng được drop down
# class CategoryView(ModelView):
#     can_view_details = True
#     column_searchable_list = ['name']
#    # form_columns = ['name', 'stock_id'] # hiển thị khi CE
#     column_list = ['name', 'stock_id'] # hiển thị ở lsv
#
#     def on_form_prefill(self, form, id):
#         category = Category.query.get(id)
#         if category:
#             form.stock_id.data = category.stock.name

class StockView(AuthModelView):
    column_list = ['id', 'name']

class BookView(AuthModelView):
    can_view_details = True
    column_searchable_list = ['name', 'publisherName']
    form_columns = ['name', 'price', 'publisherName', 'image', 'description', 'category_id','quantity']
    column_list = ['id', 'name', 'price', 'publisherName', 'category_id', 'quantity']  # Thêm các cột muốn hiển thị

    def get_category_choices(self):
        return [(category.id, category.name) for category in Category.query.all()]

    def scaffold_form(self):
        form_class = super(BookView, self).scaffold_form()
        form_class.category_id = SelectField('Category',
                                           choices=[],
                                           coerce=int)
        return form_class

    def create_form(self, obj=None):
        form = super(BookView, self).create_form(obj)
        form.category_id.choices = self.get_category_choices()
        return form

    def edit_form(self, obj=None):
        form = super(BookView, self).edit_form(obj)
        form.category_id.choices = self.get_category_choices()
        return form

# class BookView(AuthModelView):
#     can_view_details = True
#     column_searchable_list = ['name', 'publisherName']
#     form_columns = ['name', 'price', 'publisherName', 'image', 'description', 'category_id']

#     def on_form_prefill(self, form, id):
#         book = Book.query.get(id)
#         if book:
#             form.category_id.data = book.category.name

class SaleInvoiceView(AuthModelView):
    can_view_details = True
    form_columns = ['paymentStatus', 'customer_id', 'sale_id', 'orderDate']

    def on_form_prefill(self, form, id):
        sale_invoice = SaleInvoice.query.get(id)
        if sale_invoice:
            form.customer_id.data = sale_invoice.customer.name
            form.sale_id.data = sale_invoice.sale_user.name if sale_invoice.sale_user else 'N/A'

class DetailInvoiceView(AuthModelView):
    can_view_details = True
    form_columns = ['book_id', 'saleInvoice_id', 'quantity']

    def on_form_prefill(self, form, id):
        detail_invoice = DetailInvoice.query.get(id)
        if detail_invoice:
            form.book_id.data = detail_invoice.book.name
            form.saleInvoice_id.data = f"Hóa đơn {detail_invoice.saleInvoice_id} - {detail_invoice.saleInvoice.orderDate}"

class ReportView(AuthModelView):
    can_view_details = True
    form_columns = ['reportDate', 'reportType', 'user_id']

    def on_form_prefill(self, form, id):
        report = Report.query.get(id)
        if report:
            form.user_id.data = report.report.name

class LogoutView(BaseView):
    @expose('/')
    def index(self):
        logout_user()
        return redirect('/admin')

class StatsView(BaseView):
    @expose('/')
    def index(self):
        kw = request.args.get('kw')
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')
        return self.render('admin/stats.html',
                           stats = dao.category_revenue_stats(kw=kw,
                                                              from_date=from_date,
                                                              to_date=to_date))

# Custom AdminIndexView với kiểm tra quyền
class MyAdminIndexView(AdminIndexView):
    @expose('/')
    def index(self):
        if not current_user.is_authenticated or current_user.user_role != UserRole.ADMIN:
            return redirect(url_for('admin_login'))
        # return super(MyAdminIndexView, self).index()
        return self.render('admin/index.html',
                           stats = dao.category_stats()) # tự render ra template để truyền biểu đồ

# Khởi tạo Admin với custom index view
admin = Admin(app=app, name='Book Store Admin', template_mode='bootstrap4', 
             index_view=MyAdminIndexView())

# Đăng ký các ModelView
admin.add_view(UserView(User, db.session, name='Users'))
admin.add_view(BookView(Book, db.session, name='Books'))
admin.add_view(CategoryView(Category, db.session, name='Categories'))
admin.add_view(StockView(Stock, db.session, name='Stocks'))
# admin.add_view(AuthModelView(Cart, db.session, name='Carts'))
# admin.add_view(AuthModelView(CartDetail, db.session, name='Cart Details'))
# admin.add_view(SaleInvoiceView(SaleInvoice, db.session, name='Sale Invoices'))
# admin.add_view(DetailInvoiceView(DetailInvoice, db.session, name='Invoice Details'))
admin.add_view(ReportView(Report, db.session, name='Reports'))
admin.add_view((StatsView(name='Thống kê báo cáo')))
admin.add_view((LogoutView(name='Đăng xuất')))