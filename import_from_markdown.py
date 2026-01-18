#!/usr/bin/env python
"""
Import Script: Markdown → SQLite
One-time script to import all books from markdown files to SQLite database.
"""

import os
from pathlib import Path
from app import create_app
from models import db
from services.markdown_sync_service import MarkdownSyncService


def import_all_books():
    """Import all books from markdown files to SQLite"""
    app = create_app()

    with app.app_context():
        # Initialize sync service
        sync_service = MarkdownSyncService()

        # Get all markdown files
        books_path = app.config['BOOKS_PATH']
        md_files = list(books_path.glob('*.md'))

        print(f"\n📚 Found {len(md_files)} markdown files to import")
        print(f"📁 Import directory: {books_path}\n")

        success_count = 0
        error_count = 0

        for md_file in md_files:
            try:
                # Import from markdown
                if sync_service.sync_markdown_to_db(str(md_file)):
                    print(f"  ✅ {md_file.name}")
                    success_count += 1
                else:
                    print(f"  ❌ {md_file.name} (sync failed)")
                    error_count += 1

            except Exception as e:
                print(f"  ❌ {md_file.name}: {str(e)}")
                error_count += 1

        # Summary
        print(f"\n{'='*60}")
        print(f"✅ Successfully imported: {success_count} books")
        if error_count > 0:
            print(f"❌ Failed: {error_count} books")
        print(f"{'='*60}\n")

        if success_count > 0:
            print("Books imported to database successfully!")
            print("You can now:")
            print("  1. View them in the web app")
            print("  2. Edit them via the web UI (changes sync to markdown)")
            print("  3. Continue editing markdown files (changes sync to DB)\n")


if __name__ == '__main__':
    print("\n" + "="*60)
    print("  📚 Personal Goodreads: Import from Markdown")
    print("="*60)
    import_all_books()
