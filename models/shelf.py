from datetime import datetime
from models import db


class Shelf(db.Model):
    __tablename__ = 'shelves'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    color = db.Column(db.String(7), default='#3498DB')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    book_shelves = db.relationship('BookShelf', backref='shelf', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Shelf {self.id}: {self.name}>'

    @property
    def book_count(self):
        return len(self.book_shelves)


class BookShelf(db.Model):
    __tablename__ = 'book_shelves'

    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False)
    shelf_id = db.Column(db.Integer, db.ForeignKey('shelves.id'), nullable=False)
    position = db.Column(db.Integer, nullable=True)

    __table_args__ = (
        db.UniqueConstraint('book_id', 'shelf_id', name='unique_book_shelf'),
    )

    def __repr__(self):
        return f'<BookShelf {self.id}: Book {self.book_id} - Shelf {self.shelf_id}>'
