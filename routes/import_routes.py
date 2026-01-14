from flask import Blueprint, render_template

bp = Blueprint('import', __name__, url_prefix='/import')


@bp.route('/')
def index():
    return render_template('import/index.html')
