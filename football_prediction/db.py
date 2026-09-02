"""
db.py — thin MySQL connection helper.

Uses PyMySQL directly (no ORM). One connection is opened per request
via Flask's `g` object and closed automatically when the request ends.
"""

import pymysql
import pymysql.cursors
from flask import g

# --- Edit these to match your local MySQL setup -------------------------
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "April1504!",          # <-- change to your MySQL password
    "database": "football_prediction",
    "cursorclass": pymysql.cursors.DictCursor,
    "autocommit": False,
}
# --------------------------------------------------------------------


def get_db():
    """Return a request-scoped MySQL connection, opening one if needed."""
    if "db" not in g:
        g.db = pymysql.connect(**DB_CONFIG)
    return g.db


def close_db(e=None):
    """Close the connection at the end of the request, if one was opened."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_app(app):
    app.teardown_appcontext(close_db)


def query_one(sql, params=None):
    """Run a SELECT and return a single row (dict) or None."""
    db = get_db()
    with db.cursor() as cur:
        cur.execute(sql, params or ())
        return cur.fetchone()


def query_all(sql, params=None):
    """Run a SELECT and return all rows as a list of dicts."""
    db = get_db()
    with db.cursor() as cur:
        cur.execute(sql, params or ())
        return cur.fetchall()


def execute(sql, params=None):
    """Run an INSERT/UPDATE/DELETE, commit, and return the cursor's lastrowid."""
    db = get_db()
    with db.cursor() as cur:
        cur.execute(sql, params or ())
        db.commit()
        return cur.lastrowid
