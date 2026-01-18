import os
import sys
from flask import Flask
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from config import Config
from models import db

migrate = Migrate()
csrf = CSRFProtect()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    # Register custom Jinja2 filters
    import json
    @app.template_filter('from_json')
    def from_json_filter(value):
        """Parse JSON string to Python object"""
        try:
            return json.loads(value) if value else []
        except:
            return []

    from routes import main, books, stats, import_routes, api, shelves, recommendations, admin
    app.register_blueprint(main.bp)
    app.register_blueprint(books.bp)
    app.register_blueprint(recommendations.bp)
    app.register_blueprint(stats.bp)
    app.register_blueprint(import_routes.bp)
    app.register_blueprint(api.bp)
    app.register_blueprint(shelves.bp)
    app.register_blueprint(admin.bp)

    os.makedirs(app.config['UPLOAD_FOLDER'] / 'originals', exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER'] / 'thumbnails', exist_ok=True)

    # Register CLI commands
    from cli_commands import register_commands
    register_commands(app)

    return app


# Initialize file watcher after app creation (for web server only)
def init_app_watcher(app):
    """Initialize file watcher - call this when running the web server"""
    from services.file_watcher_service import init_file_watcher
    with app.app_context():
        init_file_watcher(app)


# Create app instance for flask run
app = create_app()

# Only initialize file watcher if not running a CLI command
if 'flask' not in sys.argv[0] or 'run' in sys.argv:
    init_app_watcher(app)

if __name__ == '__main__':
    app.run(debug=True)
