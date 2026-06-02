from flask import Flask
from .database import init_db
from .routes import transactions_bp, categories_bp, summary_bp


def create_app(config=None):
    app = Flask(__name__)
    app.config["DATABASE"] = "finance.db"

    if config:
        app.config.update(config)

    app.register_blueprint(transactions_bp)
    app.register_blueprint(categories_bp)
    app.register_blueprint(summary_bp)

    with app.app_context():
        init_db(app)

    return app