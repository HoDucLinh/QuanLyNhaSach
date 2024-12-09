from flask_admin import Admin, AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
from bookstoremanagement import app, db
from bookstoremanagement.models import *
from flask_login import current_user
from flask import redirect, url_for
from wtforms import SelectField

# Custom AdminIndexView với kiểm tra quyền
class MyAdminIndexView(AdminIndexView):
    @expose('/')
    def index(self):
        if not current_user.is_authenticated or current_user.user_role != UserRole.ADMIN:
            return redirect(url_for('admin_login'))
        return super(MyAdminIndexView, self).index()

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
    form_excluded_columns = ['password']
    column_searchable_list = ['username', 'name', 'email']
    
    def scaffold_form(self):
        form_class = super(UserView, self).scaffold_form()
        form_class.user_role = SelectField('User Role', 
                                         choices=UserRole.choices(),
                                         coerce=int)
        return form_class

class CategoryView(AuthModelView):
    can_view_details = True
    column_searchable_list = ['name']
    form_columns = ['name', 'stock_id']

    def on_form_prefill(self, form, id):
        category = Category.query.get(id)
        if category:
            form.stock_id.data = category.stock.name

class BookView(AuthModelView):
    can_view_details = True
    column_searchable_list = ['name', 'publisherName']
    form_columns = ['name', 'price', 'publisherName', 'image', 'description', 'category_id']

    def on_form_prefill(self, form, id):
        book = Book.query.get(id)
        if book:
            form.category_id.data = book.category.name

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

# Khởi tạo Admin với custom index view
admin = Admin(app=app, name='Book Store Admin', template_mode='bootstrap4', 
             index_view=MyAdminIndexView())

# Đăng ký các ModelView
admin.add_view(UserView(User, db.session, name='Users'))
admin.add_view(BookView(Book, db.session, name='Books'))
admin.add_view(CategoryView(Category, db.session, name='Categories'))
admin.add_view(AuthModelView(Stock, db.session, name='Stocks'))
admin.add_view(AuthModelView(Cart, db.session, name='Carts'))
admin.add_view(AuthModelView(CartDetail, db.session, name='Cart Details'))
admin.add_view(SaleInvoiceView(SaleInvoice, db.session, name='Sale Invoices'))
admin.add_view(DetailInvoiceView(DetailInvoice, db.session, name='Invoice Details'))
admin.add_view(ReportView(Report, db.session, name='Reports'))