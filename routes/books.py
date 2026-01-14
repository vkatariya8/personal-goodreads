from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, Book, ReadingRecord, Review, Category, BookCategory
from forms.book_forms import BookForm
from sqlalchemy import or_

bp = Blueprint('books', __name__, url_prefix='/books')


@bp.route('/library')
def library():
    page = request.args.get('page', 1, type=int)
    per_page = 20

    query = Book.query

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

    rating_filter = request.args.get('rating', type=int)
    if rating_filter:
        query = query.join(Review).filter(Review.rating == rating_filter)

    category_filter = request.args.get('category', type=int)
    if category_filter:
        query = query.join(BookCategory).filter(BookCategory.category_id == category_filter)

    sort_by = request.args.get('sort', 'date_added')
    if sort_by == 'title':
        query = query.order_by(Book.title)
    elif sort_by == 'author':
        query = query.order_by(Book.author)
    elif sort_by == 'date_added':
        query = query.order_by(Book.date_added.desc())
    elif sort_by == 'date_read':
        query = query.join(ReadingRecord).order_by(ReadingRecord.date_finished.desc())
    elif sort_by == 'rating':
        query = query.join(Review).order_by(Review.rating.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    books = pagination.items

    all_categories = Category.query.order_by(Category.name).all()

    return render_template(
        'library/index.html',
        books=books,
        pagination=pagination,
        categories=all_categories,
        search=search,
        status_filter=status_filter,
        rating_filter=rating_filter,
        category_filter=category_filter,
        sort_by=sort_by
    )


@bp.route('/<int:book_id>')
def detail(book_id):
    book = Book.query.get_or_404(book_id)
    return render_template('library/detail.html', book=book)


@bp.route('/add', methods=['GET', 'POST'])
def add():
    form = BookForm()

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

        rating = int(form.rating.data) if form.rating.data else None
        if rating or form.review_text.data or form.private_notes.data:
            review = Review(
                book_id=book.id,
                rating=rating,
                review_text=form.review_text.data or None,
                private_notes=form.private_notes.data or None,
            )
            db.session.add(review)

        db.session.commit()
        flash(f'"{book.title}" has been added to your library.', 'success')
        return redirect(url_for('books.detail', book_id=book.id))

    return render_template('library/form.html', form=form, title='Add Book', is_edit=False)


@bp.route('/<int:book_id>/edit', methods=['GET', 'POST'])
def edit(book_id):
    book = Book.query.get_or_404(book_id)
    form = BookForm(obj=book)

    if request.method == 'GET':
        if book.reading_record:
            form.status.data = book.reading_record.status
            form.date_started.data = book.reading_record.date_started
            form.date_finished.data = book.reading_record.date_finished

        if book.review:
            form.rating.data = str(book.review.rating) if book.review.rating else ''
            form.review_text.data = book.review.review_text
            form.private_notes.data = book.review.private_notes

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

        rating = int(form.rating.data) if form.rating.data else None
        if book.review:
            book.review.rating = rating
            book.review.review_text = form.review_text.data or None
            book.review.private_notes = form.private_notes.data or None
        elif rating or form.review_text.data or form.private_notes.data:
            review = Review(
                book_id=book.id,
                rating=rating,
                review_text=form.review_text.data or None,
                private_notes=form.private_notes.data or None,
            )
            db.session.add(review)

        db.session.commit()
        flash(f'"{book.title}" has been updated.', 'success')
        return redirect(url_for('books.detail', book_id=book.id))

    return render_template('library/form.html', form=form, book=book, title='Edit Book', is_edit=True)


@bp.route('/<int:book_id>/delete', methods=['POST'])
def delete(book_id):
    book = Book.query.get_or_404(book_id)
    title = book.title
    db.session.delete(book)
    db.session.commit()
    flash(f'"{title}" has been deleted from your library.', 'success')
    return redirect(url_for('books.library'))
