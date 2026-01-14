from datetime import datetime
from models import db


class Review(db.Model):
    __tablename__ = 'reviews'

    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False, unique=True)

    rating = db.Column(db.Integer, nullable=True, index=True)
    review_text = db.Column(db.Text, nullable=True)
    is_spoiler = db.Column(db.Boolean, default=False)
    private_notes = db.Column(db.Text, nullable=True)

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
