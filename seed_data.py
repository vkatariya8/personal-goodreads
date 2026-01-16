from app import create_app
from models import db, Book, ReadingRecord, Review, Shelf, BookShelf
from datetime import datetime, timedelta
import random

app = create_app()

with app.app_context():
    print("Clearing existing data...")
    BookShelf.query.delete()
    Review.query.delete()
    ReadingRecord.query.delete()
    Shelf.query.delete()
    Book.query.delete()
    db.session.commit()

    print("Creating shelves...")
    shelves = [
        Shelf(name='Fiction', color='#3498DB'),
        Shelf(name='Non-Fiction', color='#E67E22'),
        Shelf(name='Science Fiction', color='#9B59B6'),
        Shelf(name='Fantasy', color='#1ABC9C'),
        Shelf(name='Mystery', color='#34495E'),
        Shelf(name='Biography', color='#F39C12'),
        Shelf(name='History', color='#C0392B'),
        Shelf(name='Science', color='#27AE60'),
    ]
    db.session.add_all(shelves)
    db.session.commit()

    print("Creating sample books...")
    sample_books = [
        {
            'title': 'To Kill a Mockingbird',
            'author': 'Harper Lee',
            'isbn13': '9780061120084',
            'pages': 324,
            'year_published': 1960,
            'status': 'read',
            'rating': 5,
            'review': 'A timeless classic that explores themes of racial injustice and moral growth.',
            'shelves': ['Fiction'],
            'date_finished': datetime.now() - timedelta(days=30)
        },
        {
            'title': '1984',
            'author': 'George Orwell',
            'isbn13': '9780451524935',
            'pages': 328,
            'year_published': 1949,
            'status': 'read',
            'rating': 5,
            'review': 'A chilling dystopian masterpiece that remains relevant today.',
            'shelves': ['Fiction', 'Science Fiction'],
            'date_finished': datetime.now() - timedelta(days=60)
        },
        {
            'title': 'The Great Gatsby',
            'author': 'F. Scott Fitzgerald',
            'isbn13': '9780743273565',
            'pages': 180,
            'year_published': 1925,
            'status': 'read',
            'rating': 4,
            'review': 'A beautiful exploration of the American Dream and its disillusionment.',
            'shelves': ['Fiction'],
            'date_finished': datetime.now() - timedelta(days=45)
        },
        {
            'title': 'The Hobbit',
            'author': 'J.R.R. Tolkien',
            'isbn13': '9780547928227',
            'pages': 310,
            'year_published': 1937,
            'status': 'currently-reading',
            'rating': None,
            'review': None,
            'shelves': ['Fantasy', 'Fiction'],
            'date_started': datetime.now() - timedelta(days=5)
        },
        {
            'title': 'Sapiens: A Brief History of Humankind',
            'author': 'Yuval Noah Harari',
            'isbn13': '9780062316097',
            'pages': 443,
            'year_published': 2015,
            'status': 'read',
            'rating': 5,
            'review': 'Fascinating overview of human history from a unique perspective.',
            'shelves': ['Non-Fiction', 'History', 'Science'],
            'date_finished': datetime.now() - timedelta(days=15)
        },
        {
            'title': 'Project Hail Mary',
            'author': 'Andy Weir',
            'isbn13': '9780593135204',
            'pages': 476,
            'year_published': 2021,
            'status': 'read',
            'rating': 5,
            'review': 'An incredibly fun and scientifically grounded space adventure!',
            'shelves': ['Science Fiction', 'Fiction'],
            'date_finished': datetime.now() - timedelta(days=7)
        },
        {
            'title': 'The Midnight Library',
            'author': 'Matt Haig',
            'isbn13': '9780525559474',
            'pages': 304,
            'year_published': 2020,
            'status': 'read',
            'rating': 4,
            'review': 'A thoughtful exploration of choices and alternate lives.',
            'shelves': ['Fiction'],
            'date_finished': datetime.now() - timedelta(days=20)
        },
        {
            'title': 'Educated',
            'author': 'Tara Westover',
            'isbn13': '9780399590504',
            'pages': 334,
            'year_published': 2018,
            'status': 'read',
            'rating': 5,
            'review': 'A powerful memoir about education and self-invention.',
            'shelves': ['Non-Fiction', 'Biography'],
            'date_finished': datetime.now() - timedelta(days=90)
        },
        {
            'title': 'Dune',
            'author': 'Frank Herbert',
            'isbn13': '9780441013593',
            'pages': 688,
            'year_published': 1965,
            'status': 'to-read',
            'rating': None,
            'review': None,
            'shelves': ['Science Fiction', 'Fiction']
        },
        {
            'title': 'The Silent Patient',
            'author': 'Alex Michaelides',
            'isbn13': '9781250301697',
            'pages': 336,
            'year_published': 2019,
            'status': 'read',
            'rating': 4,
            'review': 'A gripping psychological thriller with a shocking twist.',
            'shelves': ['Fiction', 'Mystery'],
            'date_finished': datetime.now() - timedelta(days=50)
        },
    ]

    for book_data in sample_books:
        book = Book(
            title=book_data['title'],
            author=book_data['author'],
            isbn13=book_data['isbn13'],
            pages=book_data['pages'],
            year_published=book_data['year_published']
        )
        db.session.add(book)
        db.session.flush()

        reading_record = ReadingRecord(
            book_id=book.id,
            status=book_data['status']
        )
        if book_data.get('date_started'):
            reading_record.date_started = book_data['date_started'].date()
        if book_data.get('date_finished'):
            reading_record.date_finished = book_data['date_finished'].date()
        db.session.add(reading_record)

        if book_data.get('rating') or book_data.get('review'):
            review = Review(
                book_id=book.id,
                rating=book_data['rating'],
                review_text=book_data['review']
            )
            db.session.add(review)

        for shelf_name in book_data.get('shelves', []):
            shelf = Shelf.query.filter_by(name=shelf_name).first()
            if shelf:
                book_shelf = BookShelf(
                    book_id=book.id,
                    shelf_id=shelf.id
                )
                db.session.add(book_shelf)

    db.session.commit()
    print(f"Successfully added {len(sample_books)} sample books!")
    print(f"Created {len(shelves)} shelves!")
    print("\nYou can now run 'flask run' to start the application!")
