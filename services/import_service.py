import pandas as pd
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Optional
from models import db
from models.book import Book
from models.reading_record import ReadingRecord
from models.review import Review
from models.shelf import Shelf, BookShelf


@dataclass
class ImportResult:
    """Container for import operation results."""
    imported: List[Book] = field(default_factory=list)
    skipped: List[dict] = field(default_factory=list)
    errors: List[dict] = field(default_factory=list)

    @property
    def imported_count(self) -> int:
        return len(self.imported)

    @property
    def skipped_count(self) -> int:
        return len(self.skipped)

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def total_processed(self) -> int:
        return self.imported_count + self.skipped_count + self.error_count


class GoodreadsImporter:
    """Service for parsing and importing Goodreads CSV data."""

    STATUS_MAP = {
        'read': 'read',
        'currently-reading': 'currently-reading',
        'to-read': 'to-read',
    }

    def __init__(self, db_session):
        self.db = db_session
        self.results = ImportResult()

    def import_csv(self, file_path: str, skip_duplicates: bool = True) -> ImportResult:
        """Main entry point for CSV import."""
        df = self.parse_csv(file_path)

        for index, row in df.iterrows():
            try:
                existing = self.check_duplicate(row)
                if existing and skip_duplicates:
                    self.results.skipped.append({
                        'row': index + 2,
                        'title': row.get('Title', 'Unknown'),
                        'reason': 'Duplicate book'
                    })
                    continue

                book = self.create_book(row)
                self.db.add(book)
                self.db.flush()

                self.create_reading_record(book, row)
                self.create_review(book, row)
                self.process_shelves(book, row.get('Bookshelves', ''))

                self.results.imported.append(book)

            except Exception as e:
                self.results.errors.append({
                    'row': index + 2,
                    'title': row.get('Title', 'Unknown'),
                    'error': str(e)
                })

        self.db.commit()
        return self.results

    def parse_csv(self, file_path: str) -> pd.DataFrame:
        """Parse CSV file with encoding fallback."""
        try:
            df = pd.read_csv(file_path, encoding='utf-8')
        except UnicodeDecodeError:
            df = pd.read_csv(file_path, encoding='latin-1')

        required = ['Title']
        missing = [col for col in required if col not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        return df

    def clean_isbn(self, value) -> Optional[str]:
        """Clean ISBN from Goodreads format (removes ="" wrapper)."""
        if pd.isna(value) or not value:
            return None

        cleaned = str(value).strip().strip('="')
        cleaned = ''.join(c for c in cleaned if c.isdigit() or c.upper() == 'X')

        if len(cleaned) not in (10, 13):
            return None

        return cleaned

    def check_duplicate(self, row: pd.Series) -> Optional[Book]:
        """Check if book already exists by ISBN, ISBN13, or Goodreads ID."""
        isbn = self.clean_isbn(row.get('ISBN'))
        isbn13 = self.clean_isbn(row.get('ISBN13'))
        goodreads_id = str(row.get('Book Id', '')).strip() if pd.notna(row.get('Book Id')) else None

        if goodreads_id:
            existing = Book.query.filter_by(goodreads_book_id=goodreads_id).first()
            if existing:
                return existing

        if isbn:
            existing = Book.query.filter_by(isbn=isbn).first()
            if existing:
                return existing

        if isbn13:
            existing = Book.query.filter_by(isbn13=isbn13).first()
            if existing:
                return existing

        return None

    def create_book(self, row: pd.Series) -> Book:
        """Create Book model from CSV row."""
        book = Book(
            title=str(row.get('Title', '')).strip(),
            author=str(row.get('Author', '')).strip() if pd.notna(row.get('Author')) else None,
            author_lf=str(row.get('Author l-f', '')).strip() if pd.notna(row.get('Author l-f')) else None,
            additional_authors=str(row.get('Additional Authors', '')).strip() if pd.notna(row.get('Additional Authors')) else None,
            isbn=self.clean_isbn(row.get('ISBN')),
            isbn13=self.clean_isbn(row.get('ISBN13')),
            publisher=str(row.get('Publisher', '')).strip() if pd.notna(row.get('Publisher')) else None,
            binding=str(row.get('Binding', '')).strip() if pd.notna(row.get('Binding')) else None,
            pages=self.parse_int(row.get('Number of Pages')),
            year_published=self.parse_int(row.get('Year Published')),
            original_publication_year=self.parse_int(row.get('Original Publication Year')),
            goodreads_book_id=str(row.get('Book Id', '')).strip() if pd.notna(row.get('Book Id')) else None,
            date_added=self.parse_datetime(row.get('Date Added')),
        )
        return book

    def create_reading_record(self, book: Book, row: pd.Series) -> ReadingRecord:
        """Create ReadingRecord from CSV row."""
        status_raw = str(row.get('Exclusive Shelf', 'to-read')).strip().lower()
        status = self.STATUS_MAP.get(status_raw, 'to-read')

        record = ReadingRecord(
            book_id=book.id,
            status=status,
            date_finished=self.parse_date(row.get('Date Read')),
        )
        self.db.add(record)
        return record

    def create_review(self, book: Book, row: pd.Series) -> Optional[Review]:
        """Create Review if rating or review text exists."""
        rating = self.parse_int(row.get('My Rating'))
        review_text = str(row.get('My Review', '')).strip() if pd.notna(row.get('My Review')) else None

        if rating == 0:
            rating = None

        if rating is None and not review_text:
            return None

        review = Review(
            book_id=book.id,
            rating=rating,
            review_text=review_text,
        )
        self.db.add(review)
        return review

    def process_shelves(self, book: Book, shelves: str) -> List[BookShelf]:
        """Parse Bookshelves column and create/link shelves."""
        if pd.isna(shelves) or not shelves:
            return []

        shelf_names = [s.strip() for s in str(shelves).split(',') if s.strip()]
        book_shelves = []

        for position, shelf_name in enumerate(shelf_names):
            if shelf_name.lower() in ('read', 'currently-reading', 'to-read'):
                continue

            shelf = Shelf.query.filter_by(name=shelf_name).first()
            if not shelf:
                shelf = Shelf(name=shelf_name)
                self.db.add(shelf)
                self.db.flush()

            book_shelf = BookShelf(
                book_id=book.id,
                shelf_id=shelf.id,
                position=position,
            )
            self.db.add(book_shelf)
            book_shelves.append(book_shelf)

        return book_shelves

    def parse_int(self, value) -> Optional[int]:
        """Safely parse integer value."""
        if pd.isna(value):
            return None
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None

    def parse_date(self, value) -> Optional[datetime]:
        """Parse date from various formats."""
        if pd.isna(value) or not value:
            return None
        try:
            return pd.to_datetime(value).date()
        except Exception:
            return None

    def parse_datetime(self, value) -> Optional[datetime]:
        """Parse datetime from various formats."""
        if pd.isna(value) or not value:
            return None
        try:
            return pd.to_datetime(value).to_pydatetime()
        except Exception:
            return None
