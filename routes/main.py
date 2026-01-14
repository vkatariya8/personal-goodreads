from flask import Blueprint, render_template
from sqlalchemy import func, extract
from models import db, Book, ReadingRecord, Review
from datetime import datetime, timedelta

bp = Blueprint('main', __name__)


@bp.route('/')
def index():
    total_books = Book.query.count()

    current_year = datetime.now().year
    books_read_this_year = db.session.query(func.count(Book.id)).join(
        ReadingRecord
    ).filter(
        ReadingRecord.status == 'read',
        extract('year', ReadingRecord.date_finished) == current_year
    ).scalar() or 0

    currently_reading = Book.query.join(ReadingRecord).filter(
        ReadingRecord.status == 'currently-reading'
    ).all()

    recently_added = Book.query.order_by(
        Book.date_added.desc()
    ).limit(10).all()

    books_per_month = db.session.query(
        extract('year', ReadingRecord.date_finished).label('year'),
        extract('month', ReadingRecord.date_finished).label('month'),
        func.count(Book.id).label('count')
    ).join(ReadingRecord).filter(
        ReadingRecord.status == 'read',
        ReadingRecord.date_finished.isnot(None)
    ).group_by('year', 'month').order_by('year', 'month').all()

    rating_distribution = db.session.query(
        Review.rating,
        func.count(Review.id).label('count')
    ).filter(
        Review.rating.isnot(None)
    ).group_by(Review.rating).all()

    stats = {
        'total_books': total_books,
        'books_read_this_year': books_read_this_year,
        'currently_reading': currently_reading,
        'recently_added': recently_added,
        'books_per_month': books_per_month,
        'rating_distribution': rating_distribution
    }

    return render_template('index.html', stats=stats)
