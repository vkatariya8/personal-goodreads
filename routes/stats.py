from flask import Blueprint, render_template
from sqlalchemy import func, extract
from datetime import datetime, timedelta
from collections import defaultdict
from models import db, Book, ReadingRecord, Review, Category, BookCategory

bp = Blueprint('stats', __name__, url_prefix='/stats')


# Helper functions
def calculate_yoy_growth(yearly_data):
    """Calculate year-over-year growth percentages"""
    result = []
    for i, (year, count) in enumerate(yearly_data):
        growth_pct = None
        if i > 0:
            prev_count = yearly_data[i-1][1]
            if prev_count > 0:
                growth_pct = round(((count - prev_count) / prev_count) * 100, 1)
        result.append({
            'year': int(year),
            'count': count,
            'growth_pct': growth_pct
        })
    return result


def calculate_reading_streaks():
    """Calculate current and longest reading streaks"""
    finished_dates = db.session.query(
        ReadingRecord.date_finished
    ).filter(
        ReadingRecord.status == 'read',
        ReadingRecord.date_finished.isnot(None)
    ).order_by(ReadingRecord.date_finished.desc()).all()

    if not finished_dates:
        return {'current_streak': 0, 'longest_streak': 0}

    dates = [d[0] for d in finished_dates]
    current_streak = 0
    longest_streak = 0
    temp_streak = 1

    # Current streak calculation
    today = datetime.now().date()
    if dates[0] >= today - timedelta(days=1):
        current_streak = 1
        for i in range(1, len(dates)):
            if (dates[i-1] - dates[i]).days <= 1:
                current_streak += 1
            else:
                break

    # Longest streak calculation
    for i in range(1, len(dates)):
        if (dates[i-1] - dates[i]).days <= 1:
            temp_streak += 1
            longest_streak = max(longest_streak, temp_streak)
        else:
            temp_streak = 1

    return {
        'current_streak': current_streak,
        'longest_streak': max(longest_streak, current_streak, 1)
    }


def format_decade(year_value):
    """Convert year to decade string (e.g., 2010 -> '2010s')"""
    if year_value is None:
        return 'Unknown'
    decade = int(year_value / 10) * 10
    return "{}s".format(decade)


@bp.route('/')
def index():
    stats = {}

    # Calculate date ranges used in multiple queries
    twelve_months_ago = datetime.now() - timedelta(days=365)
    current_year = datetime.now().year
    five_years_ago = datetime(current_year - 4, 1, 1).date()

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
    stats['books_read_this_year'] = ReadingRecord.query.filter(
        ReadingRecord.status == 'read',
        extract('year', ReadingRecord.date_finished) == current_year
    ).count()

    # Year-over-Year comparison (last 5 years)
    yearly_reads = db.session.query(
        extract('year', ReadingRecord.date_finished).label('year'),
        func.count(ReadingRecord.id)
    ).filter(
        ReadingRecord.status == 'read',
        ReadingRecord.date_finished.isnot(None),
        ReadingRecord.date_finished >= five_years_ago
    ).group_by('year').order_by('year').all()

    stats['yearly_comparison'] = calculate_yoy_growth(yearly_reads)

    # Calculate YoY change for current year
    if len(stats['yearly_comparison']) >= 2:
        current_year_data = stats['yearly_comparison'][-1]
        prev_year_data = stats['yearly_comparison'][-2]
        stats['current_year_count'] = current_year_data['count']
        stats['previous_year_count'] = prev_year_data['count']
        stats['yoy_change_pct'] = current_year_data['growth_pct']
    else:
        stats['current_year_count'] = stats['books_read_this_year']
        stats['previous_year_count'] = 0
        stats['yoy_change_pct'] = None

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

    # Rating trends over time (last 12 months)
    rating_trends = db.session.query(
        extract('year', ReadingRecord.date_finished).label('year'),
        extract('month', ReadingRecord.date_finished).label('month'),
        func.avg(Review.rating).label('avg_rating'),
        func.count(Review.id).label('count')
    ).select_from(ReadingRecord).join(
        Book, ReadingRecord.book_id == Book.id
    ).join(
        Review, Book.id == Review.book_id
    ).filter(
        ReadingRecord.status == 'read',
        ReadingRecord.date_finished.isnot(None),
        ReadingRecord.date_finished >= twelve_months_ago.date(),
        Review.rating.isnot(None)
    ).group_by('year', 'month').order_by('year', 'month').all()

    rating_trends_data = []
    for year, month, avg_rating, count in rating_trends:
        month_name = datetime(int(year), int(month), 1).strftime('%b %Y')
        rating_trends_data.append({
            'month': month_name,
            'avg_rating': round(avg_rating, 2),
            'count': count
        })
    stats['rating_trends'] = rating_trends_data

    # Books per month (last 12 months)
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

    # Pages per month (last 12 months)
    monthly_pages = db.session.query(
        extract('year', ReadingRecord.date_finished).label('year'),
        extract('month', ReadingRecord.date_finished).label('month'),
        func.sum(Book.pages).label('total_pages')
    ).join(Book).filter(
        ReadingRecord.status == 'read',
        ReadingRecord.date_finished.isnot(None),
        ReadingRecord.date_finished >= twelve_months_ago.date(),
        Book.pages.isnot(None)
    ).group_by('year', 'month').order_by('year', 'month').all()

    pages_data = []
    for year, month, pages in monthly_pages:
        month_name = datetime(int(year), int(month), 1).strftime('%b %Y')
        pages_data.append({'month': month_name, 'pages': int(pages) if pages else 0})
    stats['pages_by_month'] = pages_data

    # Top categories
    top_categories = db.session.query(
        Category.name,
        Category.color,
        func.count(BookCategory.id).label('count')
    ).join(BookCategory).group_by(Category.id).order_by(func.count(BookCategory.id).desc()).limit(10).all()
    stats['top_categories'] = [{'name': name, 'color': color, 'count': count} for name, color, count in top_categories]

    # Category breakdown for chart (all categories with read counts)
    category_breakdown = db.session.query(
        Category.name,
        Category.color,
        func.count(BookCategory.id).label('total_count')
    ).join(BookCategory).group_by(Category.id).order_by(
        func.count(BookCategory.id).desc()
    ).all()
    stats['category_chart_data'] = [
        {'name': name, 'color': color, 'count': count}
        for name, color, count in category_breakdown
    ]

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

    # Reading speed analytics
    reading_times = db.session.query(
        Book.id,
        Book.title,
        (func.julianday(ReadingRecord.date_finished) -
         func.julianday(ReadingRecord.date_started)).label('days_to_read')
    ).join(ReadingRecord).filter(
        ReadingRecord.status == 'read',
        ReadingRecord.date_started.isnot(None),
        ReadingRecord.date_finished.isnot(None),
        ReadingRecord.date_finished >= ReadingRecord.date_started
    ).all()

    if reading_times:
        days_list = [days for _, _, days in reading_times]
        stats['avg_days_to_finish'] = round(sum(days_list) / len(days_list), 1)
        stats['median_days_to_finish'] = round(sorted(days_list)[len(days_list) // 2], 1)

        # Fastest and slowest reads
        fastest = min(reading_times, key=lambda x: x[2])
        slowest = max(reading_times, key=lambda x: x[2])
        stats['fastest_read'] = {
            'book': Book.query.get(fastest[0]),
            'days': round(fastest[2], 1)
        }
        stats['slowest_read'] = {
            'book': Book.query.get(slowest[0]),
            'days': round(slowest[2], 1)
        }
        stats['books_with_reading_time'] = len(reading_times)
    else:
        stats['avg_days_to_finish'] = None
        stats['median_days_to_finish'] = None
        stats['fastest_read'] = None
        stats['slowest_read'] = None
        stats['books_with_reading_time'] = 0

    # Reading streaks
    streak_data = calculate_reading_streaks()
    stats['current_streak'] = streak_data['current_streak']
    stats['longest_streak'] = streak_data['longest_streak']

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

    # Top publishers
    top_publishers = db.session.query(
        Book.publisher,
        func.count(Book.id).label('count')
    ).join(ReadingRecord).filter(
        ReadingRecord.status == 'read',
        Book.publisher.isnot(None),
        Book.publisher != ''
    ).group_by(Book.publisher).order_by(func.count(Book.id).desc()).limit(10).all()
    stats['top_publishers'] = [{'publisher': pub, 'count': count} for pub, count in top_publishers]

    # Publication year distribution by decade
    pub_year_dist = db.session.query(
        (func.cast(Book.year_published / 10, db.Integer) * 10).label('decade'),
        func.count(Book.id).label('count')
    ).join(ReadingRecord).filter(
        ReadingRecord.status == 'read',
        Book.year_published.isnot(None),
        Book.year_published >= 1900,
        Book.year_published <= datetime.now().year
    ).group_by('decade').order_by('decade').all()

    stats['publication_decades'] = [
        {'decade': format_decade(decade), 'count': count}
        for decade, count in pub_year_dist
    ]

    # Average publication year
    avg_pub_year = db.session.query(func.avg(Book.year_published)).join(ReadingRecord).filter(
        ReadingRecord.status == 'read',
        Book.year_published.isnot(None),
        Book.year_published >= 1900
    ).scalar()
    stats['avg_publication_year'] = int(avg_pub_year) if avg_pub_year else None

    # Oldest and newest books read
    oldest_book = Book.query.join(ReadingRecord).filter(
        ReadingRecord.status == 'read',
        Book.year_published.isnot(None),
        Book.year_published >= 1900
    ).order_by(Book.year_published.asc()).first()
    stats['oldest_book_read'] = oldest_book

    newest_book = Book.query.join(ReadingRecord).filter(
        ReadingRecord.status == 'read',
        Book.year_published.isnot(None)
    ).order_by(Book.year_published.desc()).first()
    stats['newest_book_read'] = newest_book

    # Page count distribution (buckets)
    length_buckets = db.session.query(
        db.case(
            (Book.pages < 100, '< 100'),
            (Book.pages < 200, '100-199'),
            (Book.pages < 300, '200-299'),
            (Book.pages < 400, '300-399'),
            (Book.pages < 500, '400-499'),
            else_='500+'
        ).label('bucket'),
        func.count(Book.id).label('count')
    ).join(ReadingRecord).filter(
        ReadingRecord.status == 'read',
        Book.pages.isnot(None),
        Book.pages > 0
    ).group_by('bucket').all()

    # Reorder buckets for proper display
    bucket_order = ['< 100', '100-199', '200-299', '300-399', '400-499', '500+']
    bucket_dict = {bucket: count for bucket, count in length_buckets}
    stats['page_count_buckets'] = [
        {'range': bucket, 'count': bucket_dict.get(bucket, 0)}
        for bucket in bucket_order
    ]

    # Average pages by reading status
    avg_pages_by_status = db.session.query(
        ReadingRecord.status,
        func.avg(Book.pages).label('avg_pages'),
        func.count(Book.id).label('count')
    ).join(Book).filter(
        Book.pages.isnot(None),
        Book.pages > 0
    ).group_by(ReadingRecord.status).all()

    stats['avg_pages_by_status'] = {
        status: {'avg': round(avg), 'count': count}
        for status, avg, count in avg_pages_by_status
    }

    # Reading activity heatmap (last 365 days)
    one_year_ago = (datetime.now() - timedelta(days=365)).date()
    heatmap_data = db.session.query(
        ReadingRecord.date_finished.label('date'),
        func.count(ReadingRecord.id).label('count')
    ).filter(
        ReadingRecord.status == 'read',
        ReadingRecord.date_finished.isnot(None),
        ReadingRecord.date_finished >= one_year_ago
    ).group_by(ReadingRecord.date_finished).all()

    stats['heatmap_data'] = [
        {
            'date': record.date.strftime('%Y-%m-%d'),
            'value': record.count
        }
        for record in heatmap_data
    ]

    return render_template('stats/index.html', stats=stats)
