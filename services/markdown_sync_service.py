"""
Markdown Sync Service
Handles bidirectional synchronization between markdown files and SQLite database.
Markdown files are the source of truth, SQLite is a performance cache.
"""

import os
import yaml
import json
import hashlib
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from slugify import slugify

from models import db
from models.book import Book
from models.reading_record import ReadingRecord
from models.review import Review
from models.shelf import Shelf, BookShelf

logger = logging.getLogger(__name__)


class MarkdownBook:
    """
    Data class representing a book parsed from markdown.
    Contains frontmatter metadata and body sections.
    """

    def __init__(self, frontmatter: Dict, review_text: str = None, private_notes: str = None, highlights: list = None, file_path: str = None):
        self.frontmatter = frontmatter
        self.review_text = review_text
        self.private_notes = private_notes
        self.highlights = highlights or []
        self.file_path = file_path

    def to_db_models(self) -> Tuple[Book, ReadingRecord, Review]:
        """
        Convert this markdown book to SQLAlchemy models.

        Returns:
            Tuple of (Book, ReadingRecord, Review) models ready to be added to session
        """
        # Create Book model
        book = Book(
            title=self.frontmatter.get('title', 'Untitled'),
            author=self.frontmatter.get('author', ''),
            isbn=self.frontmatter.get('isbn'),
            isbn13=self.frontmatter.get('isbn13'),
            publisher=self.frontmatter.get('publisher'),
            binding=self.frontmatter.get('binding'),
            pages=self.frontmatter.get('pages'),
            year_published=self.frontmatter.get('year_published'),
            original_publication_year=self.frontmatter.get('original_publication_year'),
            goodreads_book_id=self.frontmatter.get('goodreads_book_id'),
            cover_image_url=self.frontmatter.get('cover_image_url'),
            date_added=self._parse_datetime(self.frontmatter.get('date_added')),
        )

        # Create ReadingRecord
        reading_record = ReadingRecord(
            status=self.frontmatter.get('status', 'to-read'),
            date_started=self._parse_date(self.frontmatter.get('date_started')),
            date_finished=self._parse_date(self.frontmatter.get('date_finished')),
            read_count=self.frontmatter.get('read_count', 1),
        )

        # Create Review
        highlights_json = json.dumps(self.highlights) if self.highlights else None
        review = Review(
            rating=self.frontmatter.get('rating'),
            review_text=self.review_text,
            private_notes=self.private_notes,
            highlights=highlights_json,
            is_spoiler=self.frontmatter.get('is_spoiler', False),
        )

        return book, reading_record, review

    @classmethod
    def from_db_models(cls, book: Book, reading_record: ReadingRecord = None, review: Review = None) -> 'MarkdownBook':
        """
        Convert SQLAlchemy models to MarkdownBook format.

        Args:
            book: Book model
            reading_record: ReadingRecord model (optional)
            review: Review model (optional)

        Returns:
            MarkdownBook instance ready to be written to file
        """
        frontmatter = {
            'title': book.title,
            'author': book.author,
            'isbn': book.isbn,
            'isbn13': book.isbn13,
            'publisher': book.publisher,
            'binding': book.binding,
            'pages': book.pages,
            'year_published': book.year_published,
            'original_publication_year': book.original_publication_year,
            'goodreads_book_id': book.goodreads_book_id,
            'cover_image_url': book.cover_image_url,
            'date_added': book.date_added.isoformat() if book.date_added else None,
        }

        # Add reading record data
        if reading_record:
            frontmatter['status'] = reading_record.status
            frontmatter['date_started'] = reading_record.date_started.isoformat() if reading_record.date_started else None
            frontmatter['date_finished'] = reading_record.date_finished.isoformat() if reading_record.date_finished else None
            frontmatter['read_count'] = reading_record.read_count

        # Add review data
        review_text = None
        private_notes = None
        highlights = []
        if review:
            frontmatter['rating'] = review.rating
            frontmatter['is_spoiler'] = review.is_spoiler
            review_text = review.review_text
            private_notes = review.private_notes
            # Parse highlights JSON to list
            if review.highlights:
                try:
                    highlights = json.loads(review.highlights)
                except (json.JSONDecodeError, TypeError):
                    highlights = []

        # Add shelves
        if book.book_shelves:
            frontmatter['shelves'] = [bs.shelf.name for bs in book.book_shelves]

        # Add sync metadata
        frontmatter['last_synced'] = datetime.utcnow().isoformat()

        return cls(frontmatter, review_text, private_notes, highlights)

    def _parse_datetime(self, value) -> Optional[datetime]:
        """Parse ISO datetime string to datetime object"""
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except:
            return None

    def _parse_date(self, value) -> Optional[datetime]:
        """Parse ISO date/datetime string to datetime object"""
        if not value:
            return None
        try:
            if isinstance(value, str):
                return datetime.fromisoformat(value)
            return value
        except:
            return None


class MarkdownSyncService:
    """
    Main service for bidirectional sync between markdown files and SQLite.
    """

    def __init__(self, books_path: str = None):
        """
        Initialize the sync service.

        Args:
            books_path: Path to books directory (defaults to config.BOOKS_PATH)
        """
        from flask import current_app
        self.books_path = Path(books_path) if books_path else Path(current_app.config['BOOKS_PATH'])
        self.attachments_path = Path(current_app.config['ATTACHMENTS_PATH'])
        self.db = db.session

    def sync_db_to_markdown(self, book_id: int) -> bool:
        """
        Sync a book from SQLite database to markdown file.

        Args:
            book_id: ID of the book to sync

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get book and related records
            book = Book.query.get(book_id)
            if not book:
                logger.error(f"Book {book_id} not found")
                return False

            # Convert to markdown format
            md_book = MarkdownBook.from_db_models(
                book,
                book.reading_record,
                book.review
            )

            # Generate filename
            filename = self._generate_filename(book.title)
            file_path = self.books_path / filename

            # Write to markdown file
            self._write_markdown_file(file_path, md_book)

            # Calculate and store sync hash
            sync_hash = self._calculate_sync_hash(md_book)
            book.sync_hash = sync_hash
            book.last_synced_at = datetime.utcnow()
            self.db.commit()

            logger.info(f"Synced book '{book.title}' to markdown: {filename}")
            return True

        except Exception as e:
            logger.error(f"Error syncing book {book_id} to markdown: {e}", exc_info=True)
            self.db.rollback()
            return False

    def sync_markdown_to_db(self, file_path: str) -> bool:
        """
        Sync a markdown file to SQLite database.

        Args:
            file_path: Path to markdown file

        Returns:
            True if successful, False otherwise
        """
        try:
            # Parse markdown file
            md_book = self._parse_markdown_file(file_path)
            if not md_book:
                logger.error(f"Failed to parse markdown file: {file_path}")
                return False

            # Convert to database models
            book, reading_record, review = md_book.to_db_models()

            # Check if book exists (by ISBN)
            existing_book = None
            if book.isbn13:
                existing_book = Book.query.filter_by(isbn13=book.isbn13).first()
            elif book.isbn:
                existing_book = Book.query.filter_by(isbn=book.isbn).first()

            if existing_book:
                # Update existing book
                self._update_book_from_markdown(existing_book, book, reading_record, review)
            else:
                # Create new book
                self.db.add(book)
                self.db.flush()  # Get book ID

                reading_record.book_id = book.id
                review.book_id = book.id
                self.db.add(reading_record)
                self.db.add(review)

                # Handle shelves
                self._sync_shelves(book, md_book.frontmatter.get('shelves', []))

            # Update sync metadata
            sync_hash = self._calculate_sync_hash(md_book)
            book.sync_hash = sync_hash
            book.last_synced_at = datetime.utcnow()

            self.db.commit()
            logger.info(f"Synced markdown to database: {file_path}")
            return True

        except Exception as e:
            logger.error(f"Error syncing markdown to database: {e}", exc_info=True)
            self.db.rollback()
            return False

    def _generate_filename(self, title: str) -> str:
        """
        Generate a slugified filename from book title.

        Args:
            title: Book title

        Returns:
            Filename with .md extension
        """
        slug = slugify(title, max_length=100)
        return f"{slug}.md"

    def _write_markdown_file(self, file_path: Path, md_book: MarkdownBook):
        """
        Write a MarkdownBook to file with YAML frontmatter.

        Args:
            file_path: Path to write to
            md_book: MarkdownBook to write
        """
        # Remove None values and sync metadata from frontmatter for cleaner output
        clean_frontmatter = {k: v for k, v in md_book.frontmatter.items()
                           if v is not None and k not in ['sync_hash']}

        # Update md_book frontmatter to match what's written (for hash calculation)
        md_book.frontmatter = clean_frontmatter

        # Build markdown content
        content_parts = []

        # Write YAML frontmatter
        content_parts.append('---')
        content_parts.append(yaml.dump(clean_frontmatter, sort_keys=False, allow_unicode=True))
        content_parts.append('---\n')

        # Review section
        if md_book.review_text:
            content_parts.append('# Review\n')
            content_parts.append(md_book.review_text.rstrip())
            content_parts.append('\n\n')

        # Highlights section (NO QUOTES in markdown - added in UI only)
        if md_book.highlights:
            content_parts.append('# Highlights\n')
            for highlight in md_book.highlights:
                content_parts.append(f'- {highlight}\n')
            content_parts.append('\n')

        # Private notes section
        if md_book.private_notes:
            content_parts.append('# Private Notes\n')
            content_parts.append(md_book.private_notes.rstrip())
            content_parts.append('\n')

        content = ''.join(content_parts)

        # Atomic write (write to temp file then rename)
        temp_path = file_path.with_suffix('.tmp')
        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(content)
            temp_path.replace(file_path)
        except Exception as e:
            if temp_path.exists():
                temp_path.unlink()
            raise

    def _parse_markdown_file(self, file_path: str) -> Optional[MarkdownBook]:
        """
        Parse a markdown file into MarkdownBook object.

        Args:
            file_path: Path to markdown file

        Returns:
            MarkdownBook instance or None if parsing failed
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Split frontmatter and body
            if not content.startswith('---'):
                logger.error(f"No frontmatter found in {file_path}")
                return None

            parts = content.split('---', 2)
            if len(parts) < 3:
                logger.error(f"Invalid frontmatter format in {file_path}")
                return None

            # Parse YAML frontmatter
            frontmatter = yaml.safe_load(parts[1])
            body = parts[2].strip()

            # Parse body sections (supports Review, Highlights, Private Notes)
            review_text, highlights, private_notes = self._parse_markdown_sections(body)

            return MarkdownBook(frontmatter, review_text, private_notes, highlights, file_path)

        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error in {file_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error parsing markdown file {file_path}: {e}")
            return None

    def _parse_markdown_sections(self, body: str) -> tuple:
        """
        Parse all sections from markdown body.
        Supports: Review, Highlights, Private Notes in any combination.

        Args:
            body: Markdown body text (after frontmatter)

        Returns:
            Tuple of (review_text, highlights, private_notes)
        """
        review_text = None
        highlights = []
        private_notes = None

        # Find positions of each section header
        sections_map = {}
        section_headers = ['# Review', '# Highlights', '# Private Notes']

        for header in section_headers:
            pos = body.find(header)
            if pos != -1:
                sections_map[header] = pos

        # Extract Review section
        if '# Review' in sections_map:
            start = sections_map['# Review'] + len('# Review')
            # Find next section position or use end of body
            next_positions = [p for h, p in sections_map.items()
                             if p > sections_map['# Review']]
            end = min(next_positions) if next_positions else len(body)
            review_text = body[start:end].strip()
            if not review_text:
                review_text = None

        # Extract Highlights section
        if '# Highlights' in sections_map:
            start = sections_map['# Highlights'] + len('# Highlights')
            next_positions = [p for h, p in sections_map.items()
                             if p > sections_map['# Highlights']]
            end = min(next_positions) if next_positions else len(body)
            highlights_text = body[start:end].strip()
            highlights = self._parse_bullet_list(highlights_text)

        # Extract Private Notes section
        if '# Private Notes' in sections_map:
            start = sections_map['# Private Notes'] + len('# Private Notes')
            private_notes = body[start:].strip()
            if not private_notes:
                private_notes = None

        return review_text, highlights, private_notes

    def _parse_bullet_list(self, text: str) -> list:
        """
        Parse markdown bullet list into array of strings.

        Args:
            text: Text containing bullet list

        Returns:
            List of bullet point contents (without '- ' prefix)
        """
        highlights = []
        for line in text.split('\n'):
            line = line.strip()
            if line.startswith('- '):
                content = line[2:].strip()  # Remove '- ' prefix
                if content:
                    highlights.append(content)
        return highlights

    def _calculate_sync_hash(self, md_book: MarkdownBook) -> str:
        """
        Calculate a hash of content for conflict detection.
        NOW INCLUDES: frontmatter + review + highlights + private_notes
        Excludes sync metadata fields.

        Args:
            md_book: MarkdownBook object

        Returns:
            Hash string (16 characters)
        """
        # Frontmatter fields (exclude sync metadata)
        content_fields = {k: v for k, v in md_book.frontmatter.items()
                         if k not in ['last_synced', 'sync_hash', 'updated_at']}

        # Include body sections in hash for complete conflict detection
        content_fields['_review_text'] = md_book.review_text or ''
        content_fields['_highlights'] = md_book.highlights or []
        content_fields['_private_notes'] = md_book.private_notes or ''

        # Normalize to YAML for consistent hashing
        normalized = yaml.dump(content_fields, sort_keys=True)
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]

    def _update_book_from_markdown(self, existing_book: Book, new_book: Book,
                                   reading_record: ReadingRecord, review: Review):
        """Update an existing book with data from markdown"""
        # Update book fields
        existing_book.title = new_book.title
        existing_book.author = new_book.author
        existing_book.publisher = new_book.publisher
        existing_book.binding = new_book.binding
        existing_book.pages = new_book.pages
        existing_book.year_published = new_book.year_published

        # Update reading record
        if existing_book.reading_record:
            existing_book.reading_record.status = reading_record.status
            existing_book.reading_record.date_started = reading_record.date_started
            existing_book.reading_record.date_finished = reading_record.date_finished
            existing_book.reading_record.read_count = reading_record.read_count

        # Update review
        if existing_book.review:
            existing_book.review.rating = review.rating
            existing_book.review.review_text = review.review_text
            existing_book.review.private_notes = review.private_notes
            existing_book.review.is_spoiler = review.is_spoiler

    def _sync_shelves(self, book: Book, shelf_names: List[str]):
        """Sync shelves from markdown frontmatter array"""
        # Remove existing shelf associations
        BookShelf.query.filter_by(book_id=book.id).delete()

        # Add new shelf associations
        for position, shelf_name in enumerate(shelf_names):
            # Find or create shelf
            shelf = Shelf.query.filter_by(name=shelf_name).first()
            if not shelf:
                # Create new shelf with default color
                shelf = Shelf(name=shelf_name, color='#3498db')
                self.db.add(shelf)
                self.db.flush()

            # Create association
            book_shelf = BookShelf(book_id=book.id, shelf_id=shelf.id, position=position)
            self.db.add(book_shelf)
