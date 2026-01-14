from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, Book, ReadingRecord, Review, Category, BookCategory
from sqlalchemy import or_

bp = Blueprint('books', __name__, url_prefix='/books')


@bp.route('/library')
def library():
    page = request.args.get('page', 1, type=int)
    per_page = 20

    query = Book.query

    search = request.args.get('search', '').strip()
    if search:
        query = query.filter(
            or_(
                Book.title.ilike(f'%{search}%'),
                Book.author.ilike(f'%{search}%'),
                Book.isbn.ilike(f'%{search}%'),
                Book.isbn13.ilike(f'%{search}%')
            )
        )

    status_filter = request.args.get('status')
    if status_filter:
        query = query.join(ReadingRecord).filter(ReadingRecord.status == status_filter)

    rating_filter = request.args.get('rating', type=int)
    if rating_filter:
        query = query.join(Review).filter(Review.rating == rating_filter)

    category_filter = request.args.get('category', type=int)
    if category_filter:
        query = query.join(BookCategory).filter(BookCategory.category_id == category_filter)

    sort_by = request.args.get('sort', 'date_added')
    if sort_by == 'title':
        query = query.order_by(Book.title)
    elif sort_by == 'author':
        query = query.order_by(Book.author)
    elif sort_by == 'date_added':
        query = query.order_by(Book.date_added.desc())
    elif sort_by == 'date_read':
        query = query.join(ReadingRecord).order_by(ReadingRecord.date_finished.desc())
    elif sort_by == 'rating':
        query = query.join(Review).order_by(Review.rating.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    books = pagination.items

    all_categories = Category.query.order_by(Category.name).all()

    return render_template(
        'library/index.html',
        books=books,
        pagination=pagination,
        categories=all_categories,
        search=search,
        status_filter=status_filter,
        rating_filter=rating_filter,
        category_filter=category_filter,
        sort_by=sort_by
    )


@bp.route('/<int:book_id>')
def detail(book_id):
    book = Book.query.get_or_404(book_id)
    return render_template('library/detail.html', book=book)
