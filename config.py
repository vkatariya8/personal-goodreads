import os
from pathlib import Path

basedir = Path(__file__).parent.absolute()


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'

    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        f'sqlite:///{basedir / "data" / "personal_goodreads.db"}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

    UPLOAD_FOLDER = basedir / 'static' / 'covers'
    ALLOWED_COVER_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

    COVERS_PER_PAGE = 20
    BOOKS_PER_PAGE = 24
    BOOKS_PER_PAGE_OPTIONS = [12, 24, 48, 96]

    COVER_THUMBNAIL_SIZE = (200, 300)
    COVER_ORIGINAL_MAX_SIZE = (800, 1200)

    # CSV Import settings
    CSV_UPLOAD_FOLDER = basedir / 'uploads' / 'csv'
    ALLOWED_CSV_EXTENSIONS = {'csv'}
    COVER_DOWNLOAD_TIMEOUT = 10  # seconds
    OPEN_LIBRARY_COVER_URL = 'https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg'
