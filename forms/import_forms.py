from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import BooleanField, SubmitField


class GoodreadsImportForm(FlaskForm):
    csv_file = FileField('Goodreads CSV Export', validators=[
        FileRequired(message='Please select a CSV file to import.'),
        FileAllowed(['csv'], 'Only CSV files are allowed.')
    ])
    download_covers = BooleanField('Download cover images from Open Library', default=True)
    skip_duplicates = BooleanField('Skip duplicate books', default=True)
    submit = SubmitField('Import Books')
