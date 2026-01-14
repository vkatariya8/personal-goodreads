import os
from flask import Flask
from flask_migrate import Migrate
from config import Config
from models import db

migrate = Migrate()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)

    from routes import main, books, stats, import_routes, api
    app.register_blueprint(main.bp)
    app.register_blueprint(books.bp)
    app.register_blueprint(stats.bp)
    app.register_blueprint(import_routes.bp)
    app.register_blueprint(api.bp)

    os.makedirs(app.config['UPLOAD_FOLDER'] / 'originals', exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER'] / 'thumbnails', exist_ok=True)

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
