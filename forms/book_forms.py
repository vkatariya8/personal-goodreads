from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, TextAreaField, SelectField, DateField
from wtforms.validators import DataRequired, Optional, Length, NumberRange


class BookForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(max=500)])
    author = StringField('Author', validators=[Optional(), Length(max=300)])
    additional_authors = StringField('Additional Authors', validators=[Optional(), Length(max=500)])

    isbn = StringField('ISBN', validators=[Optional(), Length(max=13)])
    isbn13 = StringField('ISBN-13', validators=[Optional(), Length(max=13)])

    publisher = StringField('Publisher', validators=[Optional(), Length(max=200)])
    binding = SelectField('Binding', choices=[
        ('', '-- Select --'),
        ('Hardcover', 'Hardcover'),
        ('Paperback', 'Paperback'),
        ('Mass Market Paperback', 'Mass Market Paperback'),
        ('Kindle Edition', 'Kindle Edition'),
        ('ebook', 'eBook'),
        ('Audiobook', 'Audiobook'),
        ('Other', 'Other'),
    ], validators=[Optional()])
    pages = IntegerField('Pages', validators=[Optional(), NumberRange(min=1)])
    year_published = IntegerField('Year Published', validators=[Optional(), NumberRange(min=1000, max=2100)])

    status = SelectField('Reading Status', choices=[
        ('to-read', 'To Read'),
        ('currently-reading', 'Currently Reading'),
        ('read', 'Read'),
    ], validators=[DataRequired()])
    date_started = DateField('Date Started', validators=[Optional()])
    date_finished = DateField('Date Finished', validators=[Optional()])

    rating = SelectField('Rating', choices=[
        ('', 'Not Rated'),
        ('1', '1 Star'),
        ('2', '2 Stars'),
        ('3', '3 Stars'),
        ('4', '4 Stars'),
        ('5', '5 Stars'),
    ], validators=[Optional()])
    review_text = TextAreaField('Review', validators=[Optional()])
    private_notes = TextAreaField('Private Notes', validators=[Optional()])
