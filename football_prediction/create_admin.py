"""
create_admin.py — bootstrap an admin account.

Usage:
    python create_admin.py <username> <password> [email]

Example:
    python create_admin.py admin admin123
"""

import sys
from werkzeug.security import generate_password_hash

import db
from app import app  # reuse the same DB_CONFIG / Flask app context


def main():
    if len(sys.argv) < 3:
        print("Usage: python create_admin.py <username> <password> [email]")
        sys.exit(1)

    username = sys.argv[1]
    password = sys.argv[2]
    email = sys.argv[3] if len(sys.argv) > 3 else f"{username}@admin.local"

    with app.app_context():
        existing = db.query_one("SELECT id FROM users WHERE username = %s", (username,))
        if existing:
            print(f"User '{username}' already exists.")
            return

        password_hash = generate_password_hash(password)
        db.execute(
            "INSERT INTO users (username, email, password_hash, is_admin) "
            "VALUES (%s, %s, %s, 1)",
            (username, email, password_hash),
        )
        print(f"Admin user '{username}' created.")


if __name__ == "__main__":
    main()
