from datetime import datetime
import json
import logging
from models import db

logger = logging.getLogger(__name__)


class Review(db.Model):
    __tablename__ = 'reviews'

    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False, unique=True)

    rating = db.Column(db.Integer, nullable=True, index=True)
    review_text = db.Column(db.Text, nullable=True)
    is_spoiler = db.Column(db.Boolean, default=False)
    private_notes = db.Column(db.Text, nullable=True)
    highlights = db.Column(db.Text, nullable=True)  # Stored as JSON array

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Review {self.id}: Book {self.book_id} - {self.rating} stars>'

    @property
    def has_review(self):
        return bool(self.review_text)

    @property
    def star_display(self):
        if self.rating is None:
            return 'Not rated'
        return '★' * self.rating + '☆' * (5 - self.rating)

    @property
    def highlights_list(self):
        """Parse highlights JSON to Python list for templates"""
        if not self.highlights:
            return []
        try:
            result = json.loads(self.highlights)
            # Ensure it's a list (type safety)
            return result if isinstance(result, list) else []
        except (json.JSONDecodeError, TypeError):
            logger.warning(f"Failed to parse highlights for review {self.id}")
            return []
