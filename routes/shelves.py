from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, Shelf, BookShelf
from forms.shelf_forms import ShelfForm

bp = Blueprint('shelves', __name__, url_prefix='/shelves')

# Nice color palette for auto-assigning shelf colors
SHELF_COLORS = [
    '#3498DB',  # Blue
    '#E74C3C',  # Red
    '#2ECC71',  # Green
    '#F39C12',  # Orange
    '#9B59B6',  # Purple
    '#1ABC9C',  # Teal
    '#E67E22',  # Dark Orange
    '#34495E',  # Dark Gray
    '#16A085',  # Dark Teal
    '#27AE60',  # Dark Green
    '#2980B9',  # Dark Blue
    '#8E44AD',  # Dark Purple
    '#C0392B',  # Dark Red
    '#D35400',  # Pumpkin
    '#7F8C8D',  # Gray
]


def get_next_color():
    """Get the next color from the palette based on existing shelves."""
    existing_shelves = Shelf.query.all()
    used_colors = [s.color for s in existing_shelves]

    # Find first unused color
    for color in SHELF_COLORS:
        if color not in used_colors:
            return color

    # If all colors are used, cycle through them
    return SHELF_COLORS[len(existing_shelves) % len(SHELF_COLORS)]


@bp.route('/')
def index():
    """List all shelves."""
    shelves = Shelf.query.order_by(Shelf.name).all()
    return render_template('shelves/index.html', shelves=shelves)


@bp.route('/add', methods=['GET', 'POST'])
def add():
    """Add a new shelf."""
    form = ShelfForm()

    if form.validate_on_submit():
        # Check if shelf name already exists
        existing = Shelf.query.filter_by(name=form.name.data).first()
        if existing:
            flash(f'A shelf named "{form.name.data}" already exists.', 'error')
            return render_template('shelves/form.html', form=form, title='Add Shelf', is_edit=False)

        # Auto-assign color if not provided or if default color
        color = form.color.data
        if not color or color == '#3498DB':
            color = get_next_color()

        shelf = Shelf(
            name=form.name.data,
            color=color
        )
        db.session.add(shelf)
        db.session.commit()

        flash(f'Shelf "{shelf.name}" has been created.', 'success')
        return redirect(url_for('shelves.index'))

    # Set auto color as default for new shelf
    if request.method == 'GET':
        form.color.data = get_next_color()

    return render_template('shelves/form.html', form=form, title='Add Shelf', is_edit=False)


@bp.route('/<int:shelf_id>/edit', methods=['GET', 'POST'])
def edit(shelf_id):
    """Edit an existing shelf."""
    shelf = Shelf.query.get_or_404(shelf_id)
    form = ShelfForm(obj=shelf)

    if form.validate_on_submit():
        # Check if new name conflicts with another shelf
        existing = Shelf.query.filter(Shelf.name == form.name.data, Shelf.id != shelf_id).first()
        if existing:
            flash(f'A shelf named "{form.name.data}" already exists.', 'error')
            return render_template('shelves/form.html', form=form, shelf=shelf, title='Edit Shelf', is_edit=True)

        shelf.name = form.name.data
        shelf.color = form.color.data
        db.session.commit()

        flash(f'Shelf "{shelf.name}" has been updated.', 'success')
        return redirect(url_for('shelves.index'))

    return render_template('shelves/form.html', form=form, shelf=shelf, title='Edit Shelf', is_edit=True)


@bp.route('/<int:shelf_id>/delete', methods=['POST'])
def delete(shelf_id):
    """Delete a shelf."""
    shelf = Shelf.query.get_or_404(shelf_id)

    # Check if shelf has books
    if shelf.book_count > 0:
        flash(f'Cannot delete shelf "{shelf.name}" because it has {shelf.book_count} book(s). Remove books from this shelf first.', 'error')
        return redirect(url_for('shelves.index'))

    name = shelf.name
    db.session.delete(shelf)
    db.session.commit()

    flash(f'Shelf "{name}" has been deleted.', 'success')
    return redirect(url_for('shelves.index'))
