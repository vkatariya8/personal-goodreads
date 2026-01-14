# Getting Started - Personal Goodreads

## Running the Application

```bash
# Navigate to project directory
cd /Users/workaccount/Documents/claude/personal-goodreads

# Activate virtual environment
source venv/bin/activate

# Start the Flask server
flask run
```

The application will be available at **http://localhost:5000**

## To Stop the Server

Press `Ctrl+C` in the terminal where Flask is running.

## What's Available Now

- **Home** (http://localhost:5000) - Dashboard with reading stats
- **Library** (http://localhost:5000/books/library) - Browse all books
- **Book Details** - Click any book to see full information
- **Statistics** (Coming in Phase 5) - Reading analytics
- **Import** (Coming in Phase 4) - Goodreads CSV import

## Current Features

✅ 10 sample books with covers, ratings, and reviews
✅ Filter by status (read, currently-reading, to-read)
✅ Filter by rating (1-5 stars)
✅ Filter by category
✅ Search by title, author, or ISBN
✅ Sort by title, author, date added, date read, or rating
✅ Beautiful responsive UI with Tailwind CSS

## Next Development Phases

**Phase 2: Core CRUD** (Next)
- Add new books manually
- Edit existing books
- Delete books
- Upload cover images
- Manage categories

**Phase 4: Goodreads Import**
- Import your Goodreads CSV export
- Automatic cover image downloads
- Preserve all ratings and reviews

**Phase 5: Statistics Dashboard**
- Reading progress over time
- Genre analysis charts
- Author statistics
- Rating insights

## Troubleshooting

**Port already in use?**
```bash
flask run --port 5001
```

**Need to reset the database?**
```bash
rm data/personal_goodreads.db
flask db upgrade
python seed_data.py
```

**Virtual environment not activating?**
Make sure you're in the project directory first, then try:
```bash
source venv/bin/activate
```
