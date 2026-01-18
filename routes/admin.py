"""
Admin Routes
Administrative interface for managing markdown sync, conflicts, and system status.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from models import db, Book
from services.markdown_sync_service import MarkdownSyncService
from services.file_watcher_service import get_file_watcher
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('admin', __name__, url_prefix='/admin')


@bp.route('/sync-status')
def sync_status():
    """Display sync status and conflicts"""
    sync_service = MarkdownSyncService()
    books_path = current_app.config['BOOKS_PATH']

    # Collect sync status for all books
    book_statuses = []
    conflicts = []

    # Check database books
    db_books = Book.query.all()
    for book in db_books:
        filename = sync_service._generate_filename(book.title)
        file_path = books_path / filename

        status = {
            'book_id': book.id,
            'title': book.title,
            'filename': filename,
            'db_exists': True,
            'md_exists': file_path.exists(),
            'last_synced': book.last_synced_at,
            'sync_hash': book.sync_hash,
            'has_conflict': False,
            'conflict_type': None
        }

        if not file_path.exists():
            status['has_conflict'] = True
            status['conflict_type'] = 'missing_markdown'
            conflicts.append(status)
        else:
            # Check for hash mismatch
            md_book = sync_service._parse_markdown_file(str(file_path))
            if md_book:
                md_hash = sync_service._calculate_sync_hash(md_book)
                if book.sync_hash and book.sync_hash != md_hash:
                    status['has_conflict'] = True
                    status['conflict_type'] = 'hash_mismatch'
                    conflicts.append(status)

        book_statuses.append(status)

    # Check for orphaned markdown files
    md_files = list(books_path.glob('*.md'))
    db_filenames = {sync_service._generate_filename(book.title) for book in db_books}

    for md_file in md_files:
        if md_file.name not in db_filenames:
            status = {
                'book_id': None,
                'title': md_file.stem,
                'filename': md_file.name,
                'db_exists': False,
                'md_exists': True,
                'last_synced': None,
                'sync_hash': None,
                'has_conflict': True,
                'conflict_type': 'orphaned_markdown'
            }
            book_statuses.append(status)
            conflicts.append(status)

    # File watcher status
    file_watcher = get_file_watcher()
    watcher_running = file_watcher.is_running() if file_watcher else False

    # Statistics
    stats = {
        'total_books': len(db_books),
        'total_markdown': len(md_files),
        'total_conflicts': len(conflicts),
        'synced_books': len([b for b in book_statuses if b['db_exists'] and b['md_exists'] and not b['has_conflict']]),
        'watcher_running': watcher_running
    }

    return render_template(
        'admin/sync_status.html',
        book_statuses=book_statuses,
        conflicts=conflicts,
        stats=stats
    )


@bp.route('/sync-book/<int:book_id>', methods=['POST'])
def sync_book(book_id):
    """Manually sync a specific book from database to markdown"""
    try:
        sync_service = MarkdownSyncService()
        book = Book.query.get_or_404(book_id)

        if sync_service.sync_db_to_markdown(book_id):
            flash(f'Successfully synced "{book.title}" to markdown', 'success')
        else:
            flash(f'Failed to sync "{book.title}"', 'error')
    except Exception as e:
        logger.error(f"Error syncing book {book_id}: {e}", exc_info=True)
        flash(f'Error: {str(e)}', 'error')

    return redirect(url_for('admin.sync_status'))


@bp.route('/sync-from-markdown/<path:filename>', methods=['POST'])
def sync_from_markdown(filename):
    """Manually sync a specific markdown file to database"""
    try:
        sync_service = MarkdownSyncService()
        books_path = current_app.config['BOOKS_PATH']
        file_path = books_path / filename

        if not file_path.exists():
            flash(f'Markdown file not found: {filename}', 'error')
        elif sync_service.sync_markdown_to_db(str(file_path)):
            flash(f'Successfully imported "{filename}" from markdown', 'success')
        else:
            flash(f'Failed to import "{filename}"', 'error')
    except Exception as e:
        logger.error(f"Error syncing from markdown {filename}: {e}", exc_info=True)
        flash(f'Error: {str(e)}', 'error')

    return redirect(url_for('admin.sync_status'))


@bp.route('/sync-all', methods=['POST'])
def sync_all():
    """Sync all books bidirectionally"""
    try:
        sync_service = MarkdownSyncService()
        books_path = current_app.config['BOOKS_PATH']

        success_count = 0
        error_count = 0

        # Import all markdown files
        md_files = list(books_path.glob('*.md'))
        for md_file in md_files:
            try:
                if sync_service.sync_markdown_to_db(str(md_file)):
                    success_count += 1
                else:
                    error_count += 1
            except Exception as e:
                logger.error(f"Error importing {md_file}: {e}")
                error_count += 1

        # Export all database books
        books = Book.query.all()
        for book in books:
            try:
                if sync_service.sync_db_to_markdown(book.id):
                    success_count += 1
                else:
                    error_count += 1
            except Exception as e:
                logger.error(f"Error exporting {book.title}: {e}")
                error_count += 1

        if error_count == 0:
            flash(f'Successfully synced all books ({success_count} operations)', 'success')
        else:
            flash(f'Sync completed with {error_count} errors ({success_count} successful)', 'warning')

    except Exception as e:
        logger.error(f"Error during full sync: {e}", exc_info=True)
        flash(f'Error: {str(e)}', 'error')

    return redirect(url_for('admin.sync_status'))


@bp.route('/delete-markdown/<path:filename>', methods=['POST'])
def delete_markdown(filename):
    """Delete an orphaned markdown file"""
    try:
        books_path = current_app.config['BOOKS_PATH']
        file_path = books_path / filename

        if file_path.exists():
            file_path.unlink()
            flash(f'Deleted markdown file: {filename}', 'success')
        else:
            flash(f'File not found: {filename}', 'error')
    except Exception as e:
        logger.error(f"Error deleting markdown {filename}: {e}", exc_info=True)
        flash(f'Error: {str(e)}', 'error')

    return redirect(url_for('admin.sync_status'))
