from flask_apscheduler import APScheduler
from bookstoremanagement import app, dao, db

scheduler = APScheduler()

@scheduler.task('interval', id='check_orders', seconds=30)
def check_and_cancel_orders():
    with app.app_context():
        overdue_orders = dao.check_order_cancellation()
        for order in overdue_orders:
            order.paymentStatus = 'Cancelled'
            db.session.commit()

def init_scheduler():
    scheduler.init_app(app)
    scheduler.start()