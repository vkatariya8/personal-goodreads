from flask import Blueprint, jsonify

bp = Blueprint('api', __name__, url_prefix='/api')


@bp.route('/books')
def books():
    return jsonify({'books': []})
