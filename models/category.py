from datetime import datetime
from models import db


class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    color = db.Column(db.String(7), default='#3498DB')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    book_categories = db.relationship('BookCategory', backref='category', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Category {self.id}: {self.name}>'

    @property
    def book_count(self):
        return len(self.book_categories)


class BookCategory(db.Model):
    __tablename__ = 'book_categories'

    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    position = db.Column(db.Integer, nullable=True)

    __table_args__ = (
        db.UniqueConstraint('book_id', 'category_id', name='unique_book_category'),
    )

    def __repr__(self):
        return f'<BookCategory {self.id}: Book {self.book_id} - Category {self.category_id}>'
