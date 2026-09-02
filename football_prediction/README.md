# Matchday Predictor — Football Score Prediction System

A database-systems coursework project: users log in, predict scores for
fixtures posted by an admin, and earn points once the admin enters the
real result.

**Stack**
- Frontend: HTML + CSS (Jinja2 templates), no JS framework
- Backend: Python + Flask
- Database: MySQL
- DB access: raw SQL via `PyMySQL` — no ORM, so every query is visible in
  `app.py` and `db.py`

No external football APIs are used anywhere — all match data is entered
by the admin.

## 1. Create the database

```bash
mysql -u root -p < schema.sql
```

This creates a `football_prediction` database with three tables:
`users`, `matches`, `predictions` (see `schema.sql` for the full DDL,
including foreign keys and a unique constraint that stops a user
predicting the same match twice).

## 2. Install Python dependencies

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 3. Point the app at your MySQL server

Edit `db.py` and set your MySQL host/user/password:

```python
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "your-password-here",
    "database": "football_prediction",
    ...
}
```

## 4. Create an admin account

```bash
python create_admin.py admin admin123
```

Regular users sign themselves up through the `/register` page; admin
accounts are only created this way (or by inserting a row with
`is_admin = 1` directly).

## 5. Run it

```bash
python app.py
```

Visit `http://127.0.0.1:5000`. Log in as `admin` to add fixtures and
enter results; register a second account in another browser/incognito
window to predict as a regular user.

## How the points work

When the admin submits the real score for a match, `score_match()` in
`app.py` runs one query to pull every prediction for that match, then
for each one:

| Condition                          | Points |
|-------------------------------------|--------|
| Exact score match                   | 3      |
| Correct result (home win/draw/away) | 1      |
| Anything else                       | 0      |

The leaderboard (`/leaderboard`) is a single `SUM` + `GROUP BY` query
joining `users` and `predictions`.

## Project structure

```
football_prediction/
├── app.py                 # Flask routes — all SQL lives here or in db.py
├── db.py                  # PyMySQL connection helper (get_db/query_one/query_all/execute)
├── schema.sql             # CREATE DATABASE / CREATE TABLE statements
├── create_admin.py        # One-off script to bootstrap an admin login
├── requirements.txt
├── static/
│   └── style.css
└── templates/
    ├── base.html           # Shared layout, nav, flash messages
    ├── login.html / register.html
    ├── user_dashboard.html # Fixture list for regular users
    ├── predict.html        # Score prediction form
    ├── leaderboard.html
    ├── admin_dashboard.html
    ├── admin_add_match.html
    ├── admin_enter_result.html
    └── admin_view_predictions.html
```

## Ideas if you want to extend it for extra marks

- Add a `leagues` table so predictions can be grouped by competition.
- Add a stored procedure/trigger in MySQL that recalculates points
  instead of doing it in Python — good if your course wants you to
  demonstrate triggers.
- Add pagination for fixtures once the list grows.
- Add a small vanilla-JS countdown timer on `predict.html` showing time
  left until kickoff.
