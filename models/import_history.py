from datetime import datetime
from models import db


class ImportHistory(db.Model):
    __tablename__ = 'import_history'

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(300), nullable=False)
    import_date = db.Column(db.DateTime, default=datetime.utcnow)
    books_imported = db.Column(db.Integer, default=0)
    books_skipped = db.Column(db.Integer, default=0)
    books_with_errors = db.Column(db.Integer, default=0)
    covers_downloaded = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default='success')
    error_log = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f'<ImportHistory {self.id}: {self.filename} - {self.books_imported} books>'
