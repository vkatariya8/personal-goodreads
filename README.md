# Personal Goodreads - Your Private Book Tracking App

A beautiful, locally-hosted web application for tracking your reading journey. Import your Goodreads library, manage your books, and view insightful statistics about your reading habits.

## Features

- **Beautiful UI**: Modern, aesthetically pleasing interface built with Tailwind CSS
- **Book Management**: Track books with covers, ratings, reviews, and reading status
- **Categories & Tags**: Organize books with custom categories
- **Reading Statistics**: Visualize your reading progress over time
- **Goodreads Import**: Import your existing Goodreads library (coming soon in Phase 4)
- **Local & Private**: All data stored locally in a SQLite database

## Quick Start

### 1. Set Up the Environment

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Initialize the Database

```bash
# Set Flask app
export FLASK_APP=app.py  # On Windows: set FLASK_APP=app.py

# Create database tables
flask db upgrade
```

### 3. Add Sample Data (Optional)

```bash
# Populate database with 10 sample books
python seed_data.py
```

### 4. Run the Application

```bash
# Start development server
flask run

# Application will be available at http://localhost:5000
```

## Project Structure

```
personal-goodreads/
├── app.py                  # Flask application entry point
├── config.py               # Configuration settings
├── models/                 # Database models
│   ├── book.py            # Book model
│   ├── reading_record.py  # Reading status tracking
│   ├── review.py          # Ratings and reviews
│   └── category.py        # Categories and tags
├── routes/                 # Route handlers
│   ├── main.py            # Home dashboard
│   ├── books.py           # Library and book pages
│   ├── stats.py           # Statistics (coming soon)
│   └── import_routes.py   # Import functionality (coming soon)
├── templates/             # HTML templates
│   ├── base.html          # Base layout with navigation
│   ├── index.html         # Home dashboard
│   └── library/           # Book pages
├── static/                # Static files (CSS, JS, images)
└── data/                  # SQLite database location
```

## Current Implementation Status

### ✅ Phase 1: Foundation (COMPLETED)
- Project structure and dependencies
- Database models with relationships
- Flask application with migrations
- Base templates with Tailwind CSS
- Home dashboard and library views
- Sample data for testing

### 🔄 Phase 2: Core CRUD (Next)
- Add/edit/delete books manually
- Cover image upload and management
- Category management
- Book forms with validation

### 📋 Phase 3: Library Features (Upcoming)
- Enhanced search and filtering
- Grid/list view toggle
- Pagination improvements
- Sorting options

### 📋 Phase 4: Import System (Upcoming)
- Goodreads CSV import
- Cover image downloads
- Duplicate detection
- Import history tracking

### 📋 Phase 5: Statistics (Upcoming)
- Reading progress charts
- Genre analysis
- Author statistics
- Rating insights

### 📋 Phase 6: Polish (Upcoming)
- UI refinements
- ISBN lookup via Open Library API
- Data export functionality
- Performance optimizations

## Database Schema

- **books**: Core book information (title, author, ISBN, pages, etc.)
- **reading_records**: Reading status and dates
- **reviews**: Ratings and review text
- **categories**: Custom tags/categories
- **book_categories**: Many-to-many relationship between books and categories
- **import_history**: Track imports from Goodreads

## Technology Stack

- **Backend**: Flask 3.0 + SQLAlchemy
- **Database**: SQLite (single file, zero configuration)
- **Frontend**: Tailwind CSS + vanilla JavaScript
- **Migrations**: Flask-Migrate (Alembic)
- **Data Processing**: Pandas (for CSV import)
- **Image Processing**: Pillow (for cover thumbnails)

## Key Features in Action

### Home Dashboard
- Quick stats: Total books, books read this year, currently reading
- Currently reading shelf with book covers
- Recently added books grid

### Library View
- Grid display of all books with covers
- Filter by status, rating, category
- Sort by title, author, date added, date read, rating
- Search across title, author, and ISBN

### Book Detail Page
- Large cover image display
- Complete book metadata
- Reading status and dates
- Star rating display
- Review text and private notes
- Category tags with colors

## API Integrations

### Open Library API (Coming Soon)
- Automatic metadata lookup by ISBN
- Cover image fetching
- No authentication required

## Development

### Run in Debug Mode

```bash
export FLASK_APP=app.py
flask run --debug
```

### Create New Migration

```bash
flask db migrate -m "Description of changes"
flask db upgrade
```

### Reset Database

```bash
rm data/personal_goodreads.db
flask db upgrade
python seed_data.py
```

## Configuration

Configuration is managed in `config.py`. Key settings:

- `SECRET_KEY`: Flask secret key (set via environment variable in production)
- `SQLALCHEMY_DATABASE_URI`: Database connection string
- `UPLOAD_FOLDER`: Location for book cover images
- `BOOKS_PER_PAGE`: Pagination setting

## Importing from Goodreads (Coming Soon)

1. Export your Goodreads library:
   - Go to https://www.goodreads.com/review/import
   - Click "Export Library"
   - Download the CSV file

2. Import via the app:
   - Navigate to Import page
   - Upload your CSV file
   - Configure import options
   - Wait for processing

## Troubleshooting

### Port Already in Use
```bash
# Use a different port
flask run --port 5001
```

### Database Locked Error
- Ensure only one Flask instance is running
- Close any database browser tools

### Missing Dependencies
```bash
pip install -r requirements.txt
```

## Contributing

This is a personal project, but feel free to fork and customize for your own use!

## Future Enhancements

- Reading goals and progress tracking
- Custom book lists
- Advanced statistics and charts
- Progressive Web App (PWA) support
- Data export in multiple formats
- Book recommendations based on your ratings

## License

This is a personal project created for individual use.

---

**Enjoy tracking your reading journey!** 📚
