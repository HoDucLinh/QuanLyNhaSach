from bookstoremanagement.models import Book, Category


def load_books(cate_id=None, kw=None):
    query = Book.query

    if cate_id:
        query = query.filter(Book.category_id == cate_id)

    if kw:
        query = query.filter(Book.name.contains(kw))

    return query.all()

def load_categories():
    return Category.query.all()

def load_product_by_id(id):
    book = Book.query.filter_by(id=id).first()
    return book