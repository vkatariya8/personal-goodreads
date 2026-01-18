from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from models.book import Book
from models.reading_record import ReadingRecord
from models.review import Review
from models.shelf import Shelf, BookShelf
from models.import_history import ImportHistory
from models.recommendation import Recommendation, RecommendationDismissal
