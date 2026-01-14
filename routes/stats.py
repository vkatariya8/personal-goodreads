from flask import Blueprint, render_template

bp = Blueprint('stats', __name__, url_prefix='/stats')


@bp.route('/')
def index():
    return render_template('stats/index.html')
