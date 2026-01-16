from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms.validators import DataRequired, Length, Regexp


class ShelfForm(FlaskForm):
    name = StringField('Shelf Name', validators=[
        DataRequired(),
        Length(min=1, max=100, message='Shelf name must be between 1 and 100 characters')
    ])
    color = StringField('Color', validators=[
        DataRequired(),
        Length(min=4, max=7),
        Regexp(r'^#[0-9A-Fa-f]{6}$', message='Color must be a valid hex color (e.g., #3498DB)')
    ], default='#3498DB')
