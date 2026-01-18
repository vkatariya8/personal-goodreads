from datetime import datetime, timedelta
from models import db


class Recommendation(db.Model):
    """
    Stores cached book recommendations for the user.
    Each recommendation includes:
    - Book identifier (ISBN or title+author for external books)
    - Strategy used to generate the recommendation
    - Confidence score
    - Human-readable explanation
    - Metadata from external API (stored as JSON)
    - Expiration timestamp for cache management
    """
    __tablename__ = 'recommendations'

    id = db.Column(db.Integer, primary_key=True)

    # Book identification - can be ISBN or composite key for external books
    book_identifier = db.Column(db.String(255), nullable=False, index=True)

    # Book metadata from API (stored as JSON)
    title = db.Column(db.String(500), nullable=False)
    authors = db.Column(db.Text, nullable=False)  # JSON array of author names
    isbn = db.Column(db.String(20))
    isbn13 = db.Column(db.String(20))
    cover_url = db.Column(db.Text)
    publish_year = db.Column(db.Integer)
    page_count = db.Column(db.Integer)
    subjects = db.Column(db.Text)  # JSON array of subjects/genres
    description = db.Column(db.Text)

    # Recommendation metadata
    strategy = db.Column(db.String(50), nullable=False, index=True)  # 'author_based', 'shelf_based', etc.
    score = db.Column(db.Float, nullable=False, index=True)  # Confidence score 0.0 to 1.0
    reason = db.Column(db.Text, nullable=False)  # Human-readable explanation

    # Optional: Link to existing book if user already has it
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=True)

    # Cache management
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)

    # Relationships
    book = db.relationship('Book', backref='recommendations', lazy=True)

    def __init__(self, **kwargs):
        super(Recommendation, self).__init__(**kwargs)
        # Set expiration to 24 hours from creation if not specified
        if not self.expires_at:
            self.expires_at = datetime.utcnow() + timedelta(hours=24)

    def is_expired(self):
        """Check if this recommendation has expired"""
        return datetime.utcnow() > self.expires_at

    def to_dict(self):
        """Convert recommendation to dictionary for JSON serialization"""
        import json
        return {
            'id': self.id,
            'book_identifier': self.book_identifier,
            'title': self.title,
            'authors': json.loads(self.authors) if self.authors else [],
            'isbn': self.isbn,
            'isbn13': self.isbn13,
            'cover_url': self.cover_url,
            'publish_year': self.publish_year,
            'page_count': self.page_count,
            'subjects': json.loads(self.subjects) if self.subjects else [],
            'description': self.description,
            'strategy': self.strategy,
            'score': self.score,
            'reason': self.reason,
            'book_id': self.book_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_expired': self.is_expired()
        }

    def __repr__(self):
        return f'<Recommendation {self.title} ({self.strategy}, score: {self.score})>'


class RecommendationDismissal(db.Model):
    """
    Tracks books that user has dismissed from recommendations.
    Prevents the same book from being recommended again.
    """
    __tablename__ = 'recommendation_dismissals'

    id = db.Column(db.Integer, primary_key=True)

    # Book identifier (same format as Recommendation.book_identifier)
    book_identifier = db.Column(db.String(255), nullable=False, unique=True, index=True)

    # Dismissal metadata
    dismissed_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    reason = db.Column(db.String(50))  # 'not_interested', 'already_own', 'wrong_genre', etc.

    # Optional: Store book title for reference
    title = db.Column(db.String(500))

    def to_dict(self):
        """Convert dismissal to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'book_identifier': self.book_identifier,
            'title': self.title,
            'dismissed_at': self.dismissed_at.isoformat() if self.dismissed_at else None,
            'reason': self.reason
        }

    def __repr__(self):
        return f'<RecommendationDismissal {self.book_identifier} ({self.reason})>'
