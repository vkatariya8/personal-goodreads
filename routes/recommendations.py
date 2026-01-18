"""
Recommendations routes
Handles book recommendation display, refresh, and user interactions.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime
import logging

from models import db
from models.book import Book
from models.reading_record import ReadingRecord
from services.recommendation_service import RecommendationEngine

logger = logging.getLogger(__name__)

bp = Blueprint('recommendations', __name__, url_prefix='/recommendations')


@bp.route('/')
def index():
    """
    Main recommendations page showing personalized book suggestions.
    """
    # Get filter parameters
    strategy_filter = request.args.get('strategy', 'all')
    page = request.args.get('page', 1, type=int)
    per_page = 20

    # Initialize recommendation engine
    engine = RecommendationEngine()

    # Check if user has enough data
    # Count highly rated books
    from models.review import Review
    high_rated_count = Review.query.filter(Review.rating >= 4.0).count()

    if high_rated_count < 5:
        # Not enough data for recommendations
        return render_template(
            'recommendations/index.html',
            recommendations=[],
            insufficient_data=True,
            high_rated_count=high_rated_count,
            page=page,
            total_pages=0,
            strategy_filter=strategy_filter
        )

    try:
        # Get recommendations (cached or generate new)
        all_recommendations = engine.get_cached_recommendations(limit=100)

        # If cache is empty or stale, generate new recommendations
        if not all_recommendations:
            logger.info("No cached recommendations, generating new ones")
            all_recommendations = engine.generate_recommendations(limit=100)

        # Apply strategy filter
        if strategy_filter != 'all':
            recommendations = [r for r in all_recommendations if r.strategy == strategy_filter]
        else:
            recommendations = all_recommendations

        # Pagination
        total = len(recommendations)
        total_pages = (total + per_page - 1) // per_page
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        recommendations_page = recommendations[start_idx:end_idx]

        # Get last update time
        last_updated = None
        if recommendations_page:
            last_updated = recommendations_page[0].created_at

        return render_template(
            'recommendations/index.html',
            recommendations=recommendations_page,
            insufficient_data=False,
            page=page,
            total_pages=total_pages,
            total_count=total,
            strategy_filter=strategy_filter,
            last_updated=last_updated
        )

    except Exception as e:
        logger.error(f"Error loading recommendations: {e}", exc_info=True)
        flash('Error loading recommendations. Please try again.', 'error')
        return render_template(
            'recommendations/index.html',
            recommendations=[],
            insufficient_data=False,
            error=True,
            page=page,
            total_pages=0,
            strategy_filter=strategy_filter
        )


@bp.route('/refresh')
def refresh():
    """
    Force refresh recommendations by regenerating them.
    """
    try:
        logger.info("Force refreshing recommendations")
        engine = RecommendationEngine()
        engine.generate_recommendations(limit=100, force_refresh=True)
        flash('Recommendations refreshed successfully!', 'success')
    except Exception as e:
        logger.error(f"Error refreshing recommendations: {e}", exc_info=True)
        flash('Error refreshing recommendations. Please try again.', 'error')

    return redirect(url_for('recommendations.index'))


@bp.route('/<book_identifier>/dismiss', methods=['POST'])
def dismiss(book_identifier):
    """
    Dismiss a recommendation so it doesn't appear again.

    Args:
        book_identifier: Unique identifier for the book to dismiss
    """
    reason = request.form.get('reason', 'not_interested')
    title = request.form.get('title')

    try:
        engine = RecommendationEngine()
        success = engine.dismiss_recommendation(book_identifier, reason, title)

        if success:
            flash('Recommendation dismissed', 'success')
        else:
            flash('Error dismissing recommendation', 'error')

    except Exception as e:
        logger.error(f"Error dismissing recommendation: {e}", exc_info=True)
        flash('Error dismissing recommendation', 'error')

    # Return to recommendations page
    return redirect(url_for('recommendations.index'))


@bp.route('/<book_identifier>/add-to-read', methods=['POST'])
def add_to_read(book_identifier):
    """
    Add a recommended book to the "To Read" shelf.
    Creates a new book entry in the library.

    Args:
        book_identifier: Unique identifier for the book
    """
    try:
        # Get recommendation data
        from models.recommendation import Recommendation
        import json

        rec = Recommendation.query.filter_by(book_identifier=book_identifier).first()
        if not rec:
            flash('Recommendation not found', 'error')
            return redirect(url_for('recommendations.index'))

        # Check if book already exists
        existing = Book.query.filter(
            db.or_(
                Book.isbn == rec.isbn,
                Book.isbn13 == rec.isbn13,
                db.and_(
                    db.func.lower(Book.title) == rec.title.lower(),
                    db.func.lower(Book.author).contains(json.loads(rec.authors)[0].lower() if rec.authors else '')
                )
            )
        ).first()

        if existing:
            flash('Book already in your library', 'info')
            return redirect(url_for('books.detail', book_id=existing.id))

        # Create new book
        authors_list = json.loads(rec.authors) if rec.authors else []
        author_str = ', '.join(authors_list)

        new_book = Book(
            title=rec.title,
            author=author_str,
            isbn=rec.isbn,
            isbn13=rec.isbn13,
            cover_path=rec.cover_url,  # Store external URL for now
            publication_year=rec.publish_year,
            pages=rec.page_count,
            date_added=datetime.utcnow()
        )

        db.session.add(new_book)
        db.session.flush()  # Get the book ID

        # Create reading record with "To Read" status
        reading_record = ReadingRecord(
            book_id=new_book.id,
            status='to_read'
        )
        db.session.add(reading_record)

        # Add to appropriate shelves based on subjects
        if rec.subjects:
            subjects_list = json.loads(rec.subjects)
            from models.shelf import Shelf, BookShelf

            for subject in subjects_list[:3]:  # Add to first 3 matching shelves
                # Try to find matching shelf
                shelf = Shelf.query.filter(
                    db.func.lower(Shelf.name).contains(subject.lower())
                ).first()

                if shelf:
                    book_shelf = BookShelf(
                        book_id=new_book.id,
                        shelf_id=shelf.id
                    )
                    db.session.add(book_shelf)

        db.session.commit()

        # Dismiss the recommendation
        engine = RecommendationEngine()
        engine.dismiss_recommendation(book_identifier, 'added_to_library', rec.title)

        flash(f'Added "{rec.title}" to your To Read list!', 'success')
        return redirect(url_for('books.detail', book_id=new_book.id))

    except Exception as e:
        logger.error(f"Error adding book to library: {e}", exc_info=True)
        db.session.rollback()
        flash('Error adding book to library', 'error')
        return redirect(url_for('recommendations.index'))


@bp.route('/api', methods=['GET'])
def api_recommendations():
    """
    JSON API endpoint for recommendations.
    Returns recommendations data for AJAX loading.
    """
    try:
        limit = request.args.get('limit', 20, type=int)
        strategy = request.args.get('strategy', 'all')

        engine = RecommendationEngine()
        recommendations = engine.get_cached_recommendations(limit=limit)

        # Apply strategy filter
        if strategy != 'all':
            recommendations = [r for r in recommendations if r.strategy == strategy]

        # Convert to JSON
        result = {
            'recommendations': [r.to_dict() for r in recommendations],
            'count': len(recommendations)
        }

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error in API endpoint: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500
