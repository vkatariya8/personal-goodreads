#!/usr/bin/env python
"""
Export Script: SQLite → Markdown
One-time script to export all books from SQLite database to markdown files.
"""

import os
import shutil
from pathlib import Path
from app import create_app
from models import db
from models.book import Book
from services.markdown_sync_service import MarkdownSyncService


def export_all_books():
    """Export all books from SQLite to markdown files"""
    app = create_app()

    with app.app_context():
        # Initialize sync service
        sync_service = MarkdownSyncService()

        # Ensure directories exist
        os.makedirs(app.config['BOOKS_PATH'], exist_ok=True)
        os.makedirs(app.config['ATTACHMENTS_PATH'], exist_ok=True)

        # Get all books
        books = Book.query.all()
        print(f"\n📚 Found {len(books)} books to export")
        print(f"📁 Export directory: {app.config['BOOKS_PATH']}\n")

        success_count = 0
        error_count = 0

        for book in books:
            try:
                # Export to markdown
                if sync_service.sync_db_to_markdown(book.id):
                    print(f"  ✅ {book.title}")
                    success_count += 1

                    # Copy cover image if it exists
                    if book.cover_image_path:
                        src = Path('static/covers/originals') / book.cover_image_path
                        dst = app.config['ATTACHMENTS_PATH'] / book.cover_image_path

                        if src.exists() and not dst.exists():
                            shutil.copy2(src, dst)
                            print(f"     📸 Copied cover image")
                else:
                    print(f"  ❌ {book.title} (sync failed)")
                    error_count += 1

            except Exception as e:
                print(f"  ❌ {book.title}: {str(e)}")
                error_count += 1

        # Summary
        print(f"\n{'='*60}")
        print(f"✅ Successfully exported: {success_count} books")
        if error_count > 0:
            print(f"❌ Failed: {error_count} books")
        print(f"{'='*60}\n")

        # Show example file
        md_files = list(app.config['BOOKS_PATH'].glob('*.md'))
        if md_files:
            print(f"📄 Example markdown file created:")
            print(f"   {md_files[0]}\n")
            print("You can now:")
            print("  1. Open these files in Obsidian/Logseq")
            print("  2. Edit them and they'll sync back to the web app")
            print("  3. View them in the library/ directory\n")


if __name__ == '__main__':
    print("\n" + "="*60)
    print("  📚 Personal Goodreads: Export to Markdown")
    print("="*60)
    export_all_books()
