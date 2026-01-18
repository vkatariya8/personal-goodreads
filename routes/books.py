from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from models import db, Book, ReadingRecord, Review, Shelf, BookShelf
from forms.book_forms import BookForm
from sqlalchemy import or_
from services.markdown_sync_service import MarkdownSyncService
import logging
import json

logger = logging.getLogger(__name__)

bp = Blueprint('books', __name__, url_prefix='/books')


@bp.route('/library')
def library():
    page = request.args.get('page', 1, type=int)

    # Per-page with validation
    per_page_options = current_app.config.get('BOOKS_PER_PAGE_OPTIONS', [12, 24, 48, 96])
    default_per_page = current_app.config.get('BOOKS_PER_PAGE', 24)
    per_page = request.args.get('per_page', default_per_page, type=int)
    if per_page not in per_page_options:
        per_page = default_per_page

    # View mode (grid or list)
    view = request.args.get('view', 'grid')
    if view not in ('grid', 'list'):
        view = 'grid'

    query = Book.query

    # Track which tables have been joined to avoid double joins
    joined_tables = set()

    search = request.args.get('search', '').strip()
    if search:
        query = query.filter(
            or_(
                Book.title.ilike(f'%{search}%'),
                Book.author.ilike(f'%{search}%'),
                Book.isbn.ilike(f'%{search}%'),
                Book.isbn13.ilike(f'%{search}%')
            )
        )

    status_filter = request.args.get('status')
    if status_filter:
        query = query.join(ReadingRecord).filter(ReadingRecord.status == status_filter)
        joined_tables.add('ReadingRecord')

    rating_filter = request.args.get('rating', type=int)
    if rating_filter:
        query = query.join(Review).filter(Review.rating == rating_filter)
        joined_tables.add('Review')

    shelf_filter = request.args.get('shelf', type=int)
    if shelf_filter:
        query = query.join(BookShelf).filter(BookShelf.shelf_id == shelf_filter)
        joined_tables.add('BookShelf')

    # Sort with direction
    sort_by = request.args.get('sort', 'date_added')
    order = request.args.get('order', 'desc')
    if order not in ('asc', 'desc'):
        order = 'desc'

    if sort_by == 'title':
        query = query.order_by(Book.title.asc() if order == 'asc' else Book.title.desc())
    elif sort_by == 'author':
        query = query.order_by(Book.author.asc() if order == 'asc' else Book.author.desc())
    elif sort_by == 'date_added':
        query = query.order_by(Book.date_added.asc() if order == 'asc' else Book.date_added.desc())
    elif sort_by == 'date_read':
        if 'ReadingRecord' not in joined_tables:
            query = query.outerjoin(ReadingRecord)
        query = query.order_by(
            ReadingRecord.date_finished.asc() if order == 'asc' else ReadingRecord.date_finished.desc()
        )
    elif sort_by == 'rating':
        if 'Review' not in joined_tables:
            query = query.outerjoin(Review)
        query = query.order_by(
            Review.rating.asc() if order == 'asc' else Review.rating.desc()
        )
    elif sort_by == 'pages':
        query = query.order_by(Book.pages.asc() if order == 'asc' else Book.pages.desc())
    elif sort_by == 'year':
        query = query.order_by(Book.year_published.asc() if order == 'asc' else Book.year_published.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    books = pagination.items

    all_shelves = Shelf.query.order_by(Shelf.name).all()

    return render_template(
        'library/index.html',
        books=books,
        pagination=pagination,
        shelves=all_shelves,
        search=search,
        status_filter=status_filter,
        rating_filter=rating_filter,
        shelf_filter=shelf_filter,
        sort_by=sort_by,
        order=order,
        per_page=per_page,
        per_page_options=per_page_options,
        view=view
    )


@bp.route('/<int:book_id>')
def detail(book_id):
    book = Book.query.get_or_404(book_id)
    return render_template('library/detail.html', book=book)


@bp.route('/add', methods=['GET', 'POST'])
def add():
    form = BookForm()

    # Populate shelf choices
    all_shelves = Shelf.query.order_by(Shelf.name).all()
    form.shelves.choices = [(str(s.id), s.name) for s in all_shelves]

    if form.validate_on_submit():
        book = Book(
            title=form.title.data,
            author=form.author.data or None,
            additional_authors=form.additional_authors.data or None,
            isbn=form.isbn.data or None,
            isbn13=form.isbn13.data or None,
            publisher=form.publisher.data or None,
            binding=form.binding.data or None,
            pages=form.pages.data,
            year_published=form.year_published.data,
        )
        db.session.add(book)
        db.session.flush()

        reading_record = ReadingRecord(
            book_id=book.id,
            status=form.status.data,
            date_started=form.date_started.data,
            date_finished=form.date_finished.data,
        )
        db.session.add(reading_record)

        # Parse highlights from textarea (one per line)
        highlights_text = form.highlights.data or ''
        highlights_list = []
        for line in highlights_text.split('\n'):
            line = line.strip()
            # Remove quotes if user manually added them
            if line.startswith('"') and line.endswith('"'):
                line = line[1:-1].strip()
            if line:  # Only add non-empty highlights
                highlights_list.append(line)

        # Optional: Soft validation (warn if too many, but don't block)
        MAX_HIGHLIGHTS = 20
        if len(highlights_list) > MAX_HIGHLIGHTS:
            flash(f'You added {len(highlights_list)} highlights. Consider keeping it to 3-5 for readability.', 'warning')

        # Save as JSON (or None if empty)
        highlights_json = json.dumps(highlights_list) if highlights_list else None

        rating = int(form.rating.data) if form.rating.data else None
        if rating or form.review_text.data or form.private_notes.data or highlights_json:
            review = Review(
                book_id=book.id,
                rating=rating,
                review_text=form.review_text.data or None,
                private_notes=form.private_notes.data or None,
                highlights=highlights_json,
            )
            db.session.add(review)

        # Process selected shelves
        if form.shelves.data:
            for position, shelf_id in enumerate(form.shelves.data):
                book_shelf = BookShelf(
                    book_id=book.id,
                    shelf_id=int(shelf_id),
                    position=position
                )
                db.session.add(book_shelf)

        db.session.commit()

        # Sync to markdown
        try:
            sync_service = MarkdownSyncService()
            sync_service.sync_db_to_markdown(book.id)
        except Exception as e:
            logger.error(f"Failed to sync book {book.id} to markdown: {e}")

        flash(f'"{book.title}" has been added to your library.', 'success')
        return redirect(url_for('books.detail', book_id=book.id))

    return render_template('library/form.html', form=form, title='Add Book', is_edit=False)


@bp.route('/<int:book_id>/edit', methods=['GET', 'POST'])
def edit(book_id):
    book = Book.query.get_or_404(book_id)
    form = BookForm(obj=book)

    # Populate shelf choices
    all_shelves = Shelf.query.order_by(Shelf.name).all()
    form.shelves.choices = [(str(s.id), s.name) for s in all_shelves]

    if request.method == 'GET':
        # Pre-populate existing shelves
        form.shelves.data = [str(bs.shelf_id) for bs in book.book_shelves]
        if book.reading_record:
            form.status.data = book.reading_record.status
            form.date_started.data = book.reading_record.date_started
            form.date_finished.data = book.reading_record.date_finished

        if book.review:
            form.rating.data = str(book.review.rating) if book.review.rating else ''
            form.review_text.data = book.review.review_text
            form.private_notes.data = book.review.private_notes
            # Load highlights into textarea
            if book.review.highlights:
                try:
                    highlights_list = json.loads(book.review.highlights)
                    form.highlights.data = '\n'.join(highlights_list)
                except (json.JSONDecodeError, TypeError):
                    form.highlights.data = ''

    if form.validate_on_submit():
        book.title = form.title.data
        book.author = form.author.data or None
        book.additional_authors = form.additional_authors.data or None
        book.isbn = form.isbn.data or None
        book.isbn13 = form.isbn13.data or None
        book.publisher = form.publisher.data or None
        book.binding = form.binding.data or None
        book.pages = form.pages.data
        book.year_published = form.year_published.data

        if book.reading_record:
            book.reading_record.status = form.status.data
            book.reading_record.date_started = form.date_started.data
            book.reading_record.date_finished = form.date_finished.data
        else:
            reading_record = ReadingRecord(
                book_id=book.id,
                status=form.status.data,
                date_started=form.date_started.data,
                date_finished=form.date_finished.data,
            )
            db.session.add(reading_record)

        # Parse highlights from textarea (one per line)
        highlights_text = form.highlights.data or ''
        highlights_list = []
        for line in highlights_text.split('\n'):
            line = line.strip()
            # Remove quotes if user manually added them
            if line.startswith('"') and line.endswith('"'):
                line = line[1:-1].strip()
            if line:  # Only add non-empty highlights
                highlights_list.append(line)

        # Optional: Soft validation (warn if too many, but don't block)
        MAX_HIGHLIGHTS = 20
        if len(highlights_list) > MAX_HIGHLIGHTS:
            flash(f'You added {len(highlights_list)} highlights. Consider keeping it to 3-5 for readability.', 'warning')

        # Save as JSON (or None if empty)
        highlights_json = json.dumps(highlights_list) if highlights_list else None

        rating = int(form.rating.data) if form.rating.data else None
        if book.review:
            book.review.rating = rating
            book.review.review_text = form.review_text.data or None
            book.review.private_notes = form.private_notes.data or None
            book.review.highlights = highlights_json
        elif rating or form.review_text.data or form.private_notes.data or highlights_json:
            review = Review(
                book_id=book.id,
                rating=rating,
                review_text=form.review_text.data or None,
                private_notes=form.private_notes.data or None,
                highlights=highlights_json,
            )
            db.session.add(review)

        # Update shelves - remove old ones and add new ones
        BookShelf.query.filter_by(book_id=book.id).delete()
        if form.shelves.data:
            for position, shelf_id in enumerate(form.shelves.data):
                book_shelf = BookShelf(
                    book_id=book.id,
                    shelf_id=int(shelf_id),
                    position=position
                )
                db.session.add(book_shelf)

        db.session.commit()

        # Sync to markdown
        try:
            sync_service = MarkdownSyncService()
            sync_service.sync_db_to_markdown(book.id)
        except Exception as e:
            logger.error(f"Failed to sync book {book.id} to markdown: {e}")

        flash(f'"{book.title}" has been updated.', 'success')
        return redirect(url_for('books.detail', book_id=book.id))

    return render_template('library/form.html', form=form, book=book, title='Edit Book', is_edit=True)


@bp.route('/<int:book_id>/delete', methods=['POST'])
def delete(book_id):
    book = Book.query.get_or_404(book_id)
    title = book.title

    # Delete markdown file
    try:
        sync_service = MarkdownSyncService()
        filename = sync_service._generate_filename(title)
        file_path = current_app.config['BOOKS_PATH'] / filename
        if file_path.exists():
            file_path.unlink()
            logger.info(f"Deleted markdown file: {filename}")
    except Exception as e:
        logger.error(f"Failed to delete markdown file for {title}: {e}")

    db.session.delete(book)
    db.session.commit()
    flash(f'"{title}" has been deleted from your library.', 'success')
    return redirect(url_for('books.library'))
