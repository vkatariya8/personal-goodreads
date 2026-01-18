from datetime import datetime
from models import db


class Book(db.Model):
    __tablename__ = 'books'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(500), nullable=False, index=True)
    author = db.Column(db.String(300), index=True)
    author_lf = db.Column(db.String(300))
    additional_authors = db.Column(db.String(500))

    isbn = db.Column(db.String(13), unique=True, nullable=True)
    isbn13 = db.Column(db.String(13), unique=True, nullable=True)

    publisher = db.Column(db.String(200))
    binding = db.Column(db.String(50))
    pages = db.Column(db.Integer)
    year_published = db.Column(db.Integer)
    original_publication_year = db.Column(db.Integer)

    cover_image_path = db.Column(db.String(300))
    cover_image_url = db.Column(db.String(500))

    goodreads_book_id = db.Column(db.String(50), unique=True, nullable=True)

    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Markdown sync fields
    last_synced_at = db.Column(db.DateTime, nullable=True)
    sync_hash = db.Column(db.String(32), nullable=True)

    reading_record = db.relationship('ReadingRecord', backref='book', uselist=False, cascade='all, delete-orphan')
    review = db.relationship('Review', backref='book', uselist=False, cascade='all, delete-orphan')
    book_shelves = db.relationship('BookShelf', backref='book', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Book {self.id}: {self.title} by {self.author}>'

    @property
    def cover_url(self):
        if self.cover_image_path:
            return f'/static/covers/thumbnails/{self.cover_image_path}'
        elif self.cover_image_url:
            return self.cover_image_url
        elif self.isbn13:
            return f'https://covers.openlibrary.org/b/isbn/{self.isbn13}-M.jpg'
        elif self.isbn:
            return f'https://covers.openlibrary.org/b/isbn/{self.isbn}-M.jpg'
        else:
            return '/static/images/placeholder-cover.svg'

    @property
    def display_author(self):
        return self.author or 'Unknown Author'

    @property
    def all_authors(self):
        authors = [self.author] if self.author else []
        if self.additional_authors:
            authors.extend([a.strip() for a in self.additional_authors.split(',')])
        return authors

    @property
    def status(self):
        if self.reading_record:
            return self.reading_record.status
        return None

    @property
    def rating(self):
        if self.review:
            return self.review.rating
        return None

    @property
    def shelves(self):
        return [bs.shelf for bs in self.book_shelves]
