"""
Flask CLI Commands
Custom commands for managing markdown sync and library operations.
"""

import click
from flask import current_app
from pathlib import Path
from models import db, Book
from services.markdown_sync_service import MarkdownSyncService


def register_commands(app):
    """Register custom CLI commands with the Flask app"""

    @app.cli.command('export-markdown')
    @click.option('--book-id', type=int, help='Export specific book by ID')
    def export_markdown(book_id):
        """Export books from SQLite to markdown files"""
        sync_service = MarkdownSyncService()

        if book_id:
            # Export single book
            book = Book.query.get(book_id)
            if not book:
                click.echo(f"❌ Book {book_id} not found", err=True)
                return

            if sync_service.sync_db_to_markdown(book_id):
                click.echo(f"✅ Exported: {book.title}")
            else:
                click.echo(f"❌ Failed to export: {book.title}", err=True)
        else:
            # Export all books
            books = Book.query.all()
            click.echo(f"\n📚 Exporting {len(books)} books to markdown...")

            success_count = 0
            error_count = 0

            with click.progressbar(books, label='Exporting books') as bar:
                for book in bar:
                    try:
                        if sync_service.sync_db_to_markdown(book.id):
                            success_count += 1
                        else:
                            error_count += 1
                    except Exception as e:
                        click.echo(f"\n❌ Error exporting {book.title}: {e}", err=True)
                        error_count += 1

            click.echo(f"\n✅ Successfully exported: {success_count} books")
            if error_count > 0:
                click.echo(f"❌ Failed: {error_count} books")

    @app.cli.command('import-markdown')
    @click.option('--file', type=str, help='Import specific markdown file')
    def import_markdown(file):
        """Import books from markdown files to SQLite"""
        sync_service = MarkdownSyncService()
        books_path = current_app.config['BOOKS_PATH']

        if file:
            # Import single file
            file_path = Path(file)
            if not file_path.exists():
                click.echo(f"❌ File not found: {file}", err=True)
                return

            if sync_service.sync_markdown_to_db(str(file_path)):
                click.echo(f"✅ Imported: {file_path.name}")
            else:
                click.echo(f"❌ Failed to import: {file_path.name}", err=True)
        else:
            # Import all markdown files
            md_files = list(books_path.glob('*.md'))
            click.echo(f"\n📚 Importing {len(md_files)} markdown files...")

            success_count = 0
            error_count = 0

            with click.progressbar(md_files, label='Importing files') as bar:
                for md_file in bar:
                    try:
                        if sync_service.sync_markdown_to_db(str(md_file)):
                            success_count += 1
                        else:
                            error_count += 1
                    except Exception as e:
                        click.echo(f"\n❌ Error importing {md_file.name}: {e}", err=True)
                        error_count += 1

            click.echo(f"\n✅ Successfully imported: {success_count} books")
            if error_count > 0:
                click.echo(f"❌ Failed: {error_count} books")

    @app.cli.command('sync-library')
    def sync_library():
        """Sync all books bidirectionally (markdown ↔ SQLite)"""
        sync_service = MarkdownSyncService()
        books_path = current_app.config['BOOKS_PATH']

        # First, import any new markdown files
        md_files = list(books_path.glob('*.md'))
        click.echo(f"\n📥 Importing {len(md_files)} markdown files...")

        for md_file in md_files:
            try:
                sync_service.sync_markdown_to_db(str(md_file))
            except Exception as e:
                click.echo(f"❌ Error importing {md_file.name}: {e}", err=True)

        # Then, export all database books
        books = Book.query.all()
        click.echo(f"📤 Exporting {len(books)} database books...")

        for book in books:
            try:
                sync_service.sync_db_to_markdown(book.id)
            except Exception as e:
                click.echo(f"❌ Error exporting {book.title}: {e}", err=True)

        click.echo("✅ Library sync complete")

    @app.cli.command('check-conflicts')
    def check_conflicts():
        """Check for sync conflicts between markdown and database"""
        from datetime import datetime
        import yaml
        import hashlib

        sync_service = MarkdownSyncService()
        books_path = current_app.config['BOOKS_PATH']
        conflicts = []

        click.echo("\n🔍 Checking for conflicts...")

        # Check each book in database
        books = Book.query.all()
        for book in books:
            # Generate expected markdown filename
            filename = sync_service._generate_filename(book.title)
            file_path = books_path / filename

            if not file_path.exists():
                conflicts.append({
                    'type': 'missing_markdown',
                    'book': book.title,
                    'message': f'Book in database but markdown file missing: {filename}'
                })
                continue

            # Parse markdown file
            md_book = sync_service._parse_markdown_file(str(file_path))
            if not md_book:
                conflicts.append({
                    'type': 'invalid_markdown',
                    'book': book.title,
                    'message': f'Cannot parse markdown file: {filename}'
                })
                continue

            # Calculate hash from markdown
            md_hash = sync_service._calculate_sync_hash(md_book)

            # Compare with stored hash
            if book.sync_hash and book.sync_hash != md_hash:
                conflicts.append({
                    'type': 'hash_mismatch',
                    'book': book.title,
                    'message': f'Content differs between markdown and database'
                })

        # Check for markdown files not in database
        md_files = list(books_path.glob('*.md'))
        db_titles = {sync_service._generate_filename(book.title) for book in books}

        for md_file in md_files:
            if md_file.name not in db_titles:
                conflicts.append({
                    'type': 'missing_database',
                    'book': md_file.name,
                    'message': f'Markdown file exists but not in database: {md_file.name}'
                })

        # Report results
        if conflicts:
            click.echo(f"\n⚠️  Found {len(conflicts)} conflicts:\n")
            for conflict in conflicts:
                click.echo(f"  [{conflict['type']}] {conflict['message']}")
            click.echo("\nRun 'flask sync-library' to resolve conflicts")
        else:
            click.echo("✅ No conflicts found - library is in sync")

    @app.cli.command('init-library')
    def init_library():
        """Initialize the markdown library directory structure"""
        library_path = current_app.config['LIBRARY_PATH']
        books_path = current_app.config['BOOKS_PATH']
        attachments_path = current_app.config['ATTACHMENTS_PATH']
        shelves_path = current_app.config['SHELVES_PATH']

        click.echo("\n📁 Initializing library directories...")

        # Create directories
        for path in [library_path, books_path, attachments_path, shelves_path]:
            path.mkdir(parents=True, exist_ok=True)
            click.echo(f"  ✅ {path}")

        # Create README
        readme_path = library_path / 'README.md'
        if not readme_path.exists():
            readme_content = """# Personal Goodreads Library

This directory contains your book library in markdown format.

## Structure

- `books/` - Individual book files with metadata and notes
- `attachments/` - Cover images and other media
- `shelves/` - Shelf definitions and book collections

## Usage

- Edit markdown files directly in Obsidian, Logseq, or any text editor
- Changes sync automatically to the web app database
- Use the web app to browse, search, and manage your library

## File Format

Each book is stored as a markdown file with YAML frontmatter:

```markdown
---
title: "Book Title"
author: "Author Name"
isbn13: "9781234567890"
status: "read"
rating: 5
shelves: [Fiction, Favorites]
---

# Review
Your review text here...

# Private Notes
Your private notes here...
```
"""
            readme_path.write_text(readme_content)
            click.echo(f"  ✅ Created README.md")

        click.echo("\n✅ Library initialized successfully")
