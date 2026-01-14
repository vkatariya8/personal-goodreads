from app import create_app
from models import db, Book, ReadingRecord, Review, Category, BookCategory
from datetime import datetime, timedelta
import random

app = create_app()

with app.app_context():
    print("Clearing existing data...")
    BookCategory.query.delete()
    Review.query.delete()
    ReadingRecord.query.delete()
    Category.query.delete()
    Book.query.delete()
    db.session.commit()

    print("Creating categories...")
    categories = [
        Category(name='Fiction', color='#3498DB'),
        Category(name='Non-Fiction', color='#E67E22'),
        Category(name='Science Fiction', color='#9B59B6'),
        Category(name='Fantasy', color='#1ABC9C'),
        Category(name='Mystery', color='#34495E'),
        Category(name='Biography', color='#F39C12'),
        Category(name='History', color='#C0392B'),
        Category(name='Science', color='#27AE60'),
    ]
    db.session.add_all(categories)
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
            'categories': ['Fiction'],
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
            'categories': ['Fiction', 'Science Fiction'],
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
            'categories': ['Fiction'],
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
            'categories': ['Fantasy', 'Fiction'],
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
            'categories': ['Non-Fiction', 'History', 'Science'],
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
            'categories': ['Science Fiction', 'Fiction'],
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
            'categories': ['Fiction'],
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
            'categories': ['Non-Fiction', 'Biography'],
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
            'categories': ['Science Fiction', 'Fiction']
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
            'categories': ['Fiction', 'Mystery'],
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

        for cat_name in book_data.get('categories', []):
            category = Category.query.filter_by(name=cat_name).first()
            if category:
                book_category = BookCategory(
                    book_id=book.id,
                    category_id=category.id
                )
                db.session.add(book_category)

    db.session.commit()
    print(f"Successfully added {len(sample_books)} sample books!")
    print(f"Created {len(categories)} categories!")
    print("\nYou can now run 'flask run' to start the application!")
