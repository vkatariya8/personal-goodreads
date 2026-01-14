import time
import requests
from pathlib import Path
from typing import Optional, List
from PIL import Image
from io import BytesIO
from flask import current_app
from models import db
from models.book import Book


class CoverDownloader:
    """Service for downloading book covers from Open Library."""

    OPEN_LIBRARY_URL = 'https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg'
    MIN_IMAGE_SIZE = 100  # Minimum width/height to consider valid (not placeholder)

    def __init__(self, covers_folder: Path, thumbnail_size: tuple = (200, 300)):
        self.covers_folder = Path(covers_folder)
        self.thumbnail_size = thumbnail_size
        self.timeout = 10

        self.originals_folder = self.covers_folder / 'originals'
        self.thumbnails_folder = self.covers_folder / 'thumbnails'
        self.originals_folder.mkdir(parents=True, exist_ok=True)
        self.thumbnails_folder.mkdir(parents=True, exist_ok=True)

    def download_cover(self, isbn: str) -> Optional[str]:
        """Download cover from Open Library and return filename if successful."""
        if not isbn:
            return None

        try:
            url = self.OPEN_LIBRARY_URL.format(isbn=isbn)
            response = requests.get(url, timeout=self.timeout)

            if response.status_code != 200:
                return None

            if not self.validate_image(response.content):
                return None

            filename = f"{isbn}.jpg"
            original_path = self.originals_folder / filename
            thumbnail_path = self.thumbnails_folder / filename

            with open(original_path, 'wb') as f:
                f.write(response.content)

            self.create_thumbnail(original_path, thumbnail_path)

            return filename

        except requests.RequestException:
            return None
        except Exception:
            return None

    def validate_image(self, image_data: bytes) -> bool:
        """Check if image data is a valid image (not a tiny placeholder)."""
        try:
            image = Image.open(BytesIO(image_data))
            width, height = image.size
            return width >= self.MIN_IMAGE_SIZE and height >= self.MIN_IMAGE_SIZE
        except Exception:
            return False

    def create_thumbnail(self, original_path: Path, thumbnail_path: Path) -> bool:
        """Create a thumbnail from the original image."""
        try:
            with Image.open(original_path) as img:
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')

                img.thumbnail(self.thumbnail_size, Image.Resampling.LANCZOS)
                img.save(thumbnail_path, 'JPEG', quality=85)
                return True
        except Exception:
            return False

    def download_covers_batch(self, books: List[Book], rate_limit: float = 0.5) -> dict:
        """Download covers for multiple books with rate limiting."""
        results = {'success': 0, 'failed': 0, 'skipped': 0}

        for book in books:
            if book.cover_image_path:
                results['skipped'] += 1
                continue

            isbn = book.isbn13 or book.isbn
            if not isbn:
                results['skipped'] += 1
                continue

            filename = self.download_cover(isbn)
            if filename:
                book.cover_image_path = filename
                results['success'] += 1
            else:
                results['failed'] += 1

            time.sleep(rate_limit)

        db.session.commit()
        return results
