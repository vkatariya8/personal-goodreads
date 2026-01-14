import json
from pathlib import Path
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from werkzeug.utils import secure_filename
from models import db
from models.import_history import ImportHistory
from forms.import_forms import GoodreadsImportForm
from services.import_service import GoodreadsImporter
from services.cover_service import CoverDownloader

bp = Blueprint('import', __name__, url_prefix='/import')


@bp.route('/', methods=['GET', 'POST'])
def index():
    form = GoodreadsImportForm()

    if form.validate_on_submit():
        try:
            csv_folder = Path(current_app.config['CSV_UPLOAD_FOLDER'])
            csv_folder.mkdir(parents=True, exist_ok=True)

            filename = secure_filename(form.csv_file.data.filename)
            file_path = csv_folder / filename
            form.csv_file.data.save(str(file_path))

            importer = GoodreadsImporter(db.session)
            results = importer.import_csv(
                str(file_path),
                skip_duplicates=form.skip_duplicates.data
            )

            covers_downloaded = 0
            if form.download_covers.data and results.imported:
                downloader = CoverDownloader(
                    current_app.config['UPLOAD_FOLDER'],
                    current_app.config['COVER_THUMBNAIL_SIZE']
                )
                cover_results = downloader.download_covers_batch(results.imported)
                covers_downloaded = cover_results['success']

            if results.error_count > 0:
                status = 'partial'
            else:
                status = 'success'

            history = ImportHistory(
                filename=filename,
                books_imported=results.imported_count,
                books_skipped=results.skipped_count,
                books_with_errors=results.error_count,
                covers_downloaded=covers_downloaded,
                status=status,
                error_log=json.dumps(results.errors) if results.errors else None
            )
            db.session.add(history)
            db.session.commit()

            if results.error_count > 0:
                flash(
                    f"Import completed with issues: {results.imported_count} imported, "
                    f"{results.skipped_count} skipped, {results.error_count} errors",
                    'warning'
                )
            else:
                flash(
                    f"Import successful: {results.imported_count} books imported, "
                    f"{results.skipped_count} skipped, {covers_downloaded} covers downloaded",
                    'success'
                )

            return redirect(url_for('import.results', import_id=history.id))

        except Exception as e:
            db.session.rollback()
            flash(f"Import failed: {str(e)}", 'error')

    return render_template('import/index.html', form=form)


@bp.route('/results/<int:import_id>')
def results(import_id):
    import_record = ImportHistory.query.get_or_404(import_id)

    errors = []
    if import_record.error_log:
        try:
            errors = json.loads(import_record.error_log)
        except json.JSONDecodeError:
            pass

    return render_template(
        'import/results.html',
        import_record=import_record,
        errors=errors
    )


@bp.route('/history')
def history():
    imports = ImportHistory.query.order_by(ImportHistory.import_date.desc()).all()
    return render_template('import/history.html', imports=imports)
