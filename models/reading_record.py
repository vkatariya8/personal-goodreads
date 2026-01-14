from datetime import datetime
from models import db


class ReadingRecord(db.Model):
    __tablename__ = 'reading_records'

    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False, unique=True)

    status = db.Column(db.String(20), default='to-read', index=True)
    date_started = db.Column(db.Date, nullable=True)
    date_finished = db.Column(db.Date, nullable=True, index=True)
    read_count = db.Column(db.Integer, default=1)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<ReadingRecord {self.id}: Book {self.book_id} - {self.status}>'

    @property
    def is_read(self):
        return self.status == 'read'

    @property
    def is_currently_reading(self):
        return self.status == 'currently-reading'

    @property
    def is_to_read(self):
        return self.status == 'to-read'
