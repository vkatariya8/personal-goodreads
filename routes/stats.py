from flask import Blueprint, render_template
from sqlalchemy import func, extract
from datetime import datetime, timedelta
from collections import defaultdict
from models import db, Book, ReadingRecord, Review, Category, BookCategory

bp = Blueprint('stats', __name__, url_prefix='/stats')


@bp.route('/')
def index():
    stats = {}

    # Basic counts
    stats['total_books'] = Book.query.count()
    stats['books_read'] = ReadingRecord.query.filter_by(status='read').count()
    stats['currently_reading'] = ReadingRecord.query.filter_by(status='currently-reading').count()
    stats['to_read'] = ReadingRecord.query.filter_by(status='to-read').count()

    # Pages read
    pages_read = db.session.query(func.sum(Book.pages)).join(ReadingRecord).filter(
        ReadingRecord.status == 'read',
        Book.pages.isnot(None)
    ).scalar() or 0
    stats['pages_read'] = pages_read

    # This year stats
    current_year = datetime.now().year
    stats['books_read_this_year'] = ReadingRecord.query.filter(
        ReadingRecord.status == 'read',
        extract('year', ReadingRecord.date_finished) == current_year
    ).count()

    # Rating distribution
    rating_dist = db.session.query(
        Review.rating,
        func.count(Review.id)
    ).filter(Review.rating.isnot(None)).group_by(Review.rating).all()
    stats['rating_distribution'] = {r: c for r, c in rating_dist}

    # Average rating
    avg_rating = db.session.query(func.avg(Review.rating)).filter(
        Review.rating.isnot(None)
    ).scalar()
    stats['average_rating'] = round(avg_rating, 2) if avg_rating else None

    # Books per month (last 12 months)
    twelve_months_ago = datetime.now() - timedelta(days=365)
    monthly_reads = db.session.query(
        extract('year', ReadingRecord.date_finished).label('year'),
        extract('month', ReadingRecord.date_finished).label('month'),
        func.count(ReadingRecord.id)
    ).filter(
        ReadingRecord.status == 'read',
        ReadingRecord.date_finished.isnot(None),
        ReadingRecord.date_finished >= twelve_months_ago.date()
    ).group_by('year', 'month').order_by('year', 'month').all()

    # Format for chart
    months_data = []
    for year, month, count in monthly_reads:
        month_name = datetime(int(year), int(month), 1).strftime('%b %Y')
        months_data.append({'month': month_name, 'count': count})
    stats['books_by_month'] = months_data

    # Top categories
    top_categories = db.session.query(
        Category.name,
        Category.color,
        func.count(BookCategory.id).label('count')
    ).join(BookCategory).group_by(Category.id).order_by(func.count(BookCategory.id).desc()).limit(10).all()
    stats['top_categories'] = [{'name': name, 'color': color, 'count': count} for name, color, count in top_categories]

    # Top authors (by books read)
    top_authors = db.session.query(
        Book.author,
        func.count(Book.id).label('count')
    ).join(ReadingRecord).filter(
        ReadingRecord.status == 'read',
        Book.author.isnot(None),
        Book.author != ''
    ).group_by(Book.author).order_by(func.count(Book.id).desc()).limit(10).all()
    stats['top_authors'] = [{'author': author, 'count': count} for author, count in top_authors]

    # Reading pace (books per month average)
    if monthly_reads:
        total_months = len(monthly_reads) or 1
        total_books_in_period = sum(count for _, _, count in monthly_reads)
        stats['avg_books_per_month'] = round(total_books_in_period / total_months, 1)
    else:
        stats['avg_books_per_month'] = 0

    # Longest and shortest books read
    longest_book = Book.query.join(ReadingRecord).filter(
        ReadingRecord.status == 'read',
        Book.pages.isnot(None)
    ).order_by(Book.pages.desc()).first()
    stats['longest_book'] = longest_book

    shortest_book = Book.query.join(ReadingRecord).filter(
        ReadingRecord.status == 'read',
        Book.pages.isnot(None),
        Book.pages > 0
    ).order_by(Book.pages.asc()).first()
    stats['shortest_book'] = shortest_book

    return render_template('stats/index.html', stats=stats)
