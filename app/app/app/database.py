import sqlite3
from flask import g, current_app


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(
            current_app.config["DATABASE"],
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(app):
    app.teardown_appcontext(close_db)

    with app.app_context():
        db = get_db()
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS categories (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                name    TEXT    NOT NULL UNIQUE,
                type    TEXT    NOT NULL CHECK(type IN ('receita', 'despesa'))
            );

            CREATE TABLE IF NOT EXISTS transactions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                description TEXT    NOT NULL,
                amount      REAL    NOT NULL CHECK(amount > 0),
                type        TEXT    NOT NULL CHECK(type IN ('receita', 'despesa')),
                category_id INTEGER REFERENCES categories(id),
                date        TEXT    NOT NULL,
                created_at  TEXT    DEFAULT (datetime('now'))
            );

            INSERT OR IGNORE INTO categories (name, type) VALUES
                ('Salário',      'receita'),
                ('Freelance',    'receita'),
                ('Alimentação',  'despesa'),
                ('Transporte',   'despesa'),
                ('Moradia',      'despesa'),
                ('Lazer',        'despesa'),
                ('Saúde',        'despesa');
            """
        )
        db.commit()
    