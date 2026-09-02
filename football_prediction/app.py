"""
Football Score Prediction System
---------------------------------
University database-systems project.

Stack:
  Frontend : HTML + CSS (+ a little vanilla JS)
  Backend  : Python + Flask
  Database : MySQL
  DB access: raw SQL via PyMySQL (no ORM)

Setup:
  1. mysql -u root -p < schema.sql
  2. pip install -r requirements.txt
  3. Edit db.py with your MySQL password
  4. python create_admin.py admin admin123
  5. python app.py
  6. Visit http://127.0.0.1:5000
"""

from datetime import datetime

from flask import Flask, render_template, redirect, url_for, request, flash, abort
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user,
    login_required, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash

import db

app = Flask(__name__)
app.config["SECRET_KEY"] = "dev-secret-key-change-me"

db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "Please log in to continue."
login_manager.login_message_category = "info"

EXACT_SCORE_POINTS = 3
CORRECT_OUTCOME_POINTS = 1
WRONG_POINTS = 0


# --------------------------------------------------------------------------
# Flask-Login user wrapper (session/cookie handling only — no DB queries
# happen inside this class itself, they're all explicit SQL in the routes)
# --------------------------------------------------------------------------

class User(UserMixin):
    def __init__(self, row):
        self.id = row["id"]
        self.username = row["username"]
        self.email = row["email"]
        self.password_hash = row["password_hash"]
        self.is_admin = bool(row["is_admin"])

    def get_id(self):
        return str(self.id)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)


@login_manager.user_loader
def load_user(user_id):
    row = db.query_one("SELECT * FROM users WHERE id = %s", (user_id,))
    return User(row) if row else None


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------

def outcome(home, away):
    if home > away:
        return "H"
    if home < away:
        return "A"
    return "D"


def annotate_match(match):
    """Attach computed, template-friendly fields to a match row (dict)."""
    now = datetime.now()
    match["is_locked"] = (match["status"] != "upcoming") or (now >= match["kickoff_at"])
    if match["actual_home_score"] is not None and match["actual_away_score"] is not None:
        match["outcome"] = outcome(match["actual_home_score"], match["actual_away_score"])
    else:
        match["outcome"] = None
    return match


def score_match(match_id, actual_home, actual_away):
    """Award points to every prediction on this match with plain SQL.
    Called right after the admin submits the real result."""
    actual_outcome = outcome(actual_home, actual_away)
    predictions = db.query_all(
        "SELECT id, predicted_home_score, predicted_away_score "
        "FROM predictions WHERE match_id = %s",
        (match_id,),
    )
    for p in predictions:
        if (p["predicted_home_score"] == actual_home
                and p["predicted_away_score"] == actual_away):
            points = EXACT_SCORE_POINTS
        else:
            pred_outcome = outcome(p["predicted_home_score"], p["predicted_away_score"])
            points = CORRECT_OUTCOME_POINTS if pred_outcome == actual_outcome else WRONG_POINTS
        db.execute("UPDATE predictions SET points = %s WHERE id = %s", (points, p["id"]))


def admin_required():
    if not current_user.is_authenticated or not current_user.is_admin:
        abort(403)


# --------------------------------------------------------------------------
# Auth routes
# --------------------------------------------------------------------------

@app.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("admin_dashboard" if current_user.is_admin else "dashboard"))
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        error = None
        if not username or not email or not password:
            error = "All fields are required."
        elif password != confirm:
            error = "Passwords do not match."
        elif db.query_one("SELECT id FROM users WHERE username = %s", (username,)):
            error = "That username is already taken."
        elif db.query_one("SELECT id FROM users WHERE email = %s", (email,)):
            error = "That email is already registered."

        if error:
            flash(error, "error")
            return render_template("register.html", username=username, email=email)

        password_hash = generate_password_hash(password)
        db.execute(
            "INSERT INTO users (username, email, password_hash, is_admin) "
            "VALUES (%s, %s, %s, 0)",
            (username, email, password_hash),
        )
        flash("Account created. Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        row = db.query_one("SELECT * FROM users WHERE username = %s", (username,))

        if row is None or not check_password_hash(row["password_hash"], password):
            flash("Invalid username or password.", "error")
            return render_template("login.html", username=username)

        user = User(row)
        login_user(user)
        flash(f"Welcome back, {user.username}.", "success")
        return redirect(url_for("admin_dashboard" if user.is_admin else "dashboard"))

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


# --------------------------------------------------------------------------
# User routes
# --------------------------------------------------------------------------

@app.route("/dashboard")
@login_required
def dashboard():
    if current_user.is_admin:
        return redirect(url_for("admin_dashboard"))

    matches = db.query_all("SELECT * FROM matches ORDER BY kickoff_at ASC")
    matches = [annotate_match(m) for m in matches]

    my_preds_rows = db.query_all(
        "SELECT * FROM predictions WHERE user_id = %s", (current_user.id,)
    )
    my_predictions = {p["match_id"]: p for p in my_preds_rows}

    upcoming = [m for m in matches if not m["is_locked"]]
    locked_or_done = [m for m in matches if m["is_locked"]]

    return render_template(
        "user_dashboard.html",
        upcoming=upcoming,
        locked_or_done=locked_or_done,
        my_predictions=my_predictions,
    )


@app.route("/predict/<int:match_id>", methods=["GET", "POST"])
@login_required
def predict(match_id):
    if current_user.is_admin:
        abort(403)

    match = db.query_one("SELECT * FROM matches WHERE id = %s", (match_id,))
    if match is None:
        abort(404)
    match = annotate_match(match)

    existing = db.query_one(
        "SELECT * FROM predictions WHERE user_id = %s AND match_id = %s",
        (current_user.id, match_id),
    )

    if match["is_locked"]:
        flash("Predictions are closed for this match.", "error")
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        try:
            home = int(request.form["home_score"])
            away = int(request.form["away_score"])
            if home < 0 or away < 0:
                raise ValueError
        except (KeyError, ValueError):
            flash("Enter valid, non-negative scores for both teams.", "error")
            return render_template("predict.html", match=match, existing=existing)

        if existing:
            db.execute(
                "UPDATE predictions SET predicted_home_score = %s, "
                "predicted_away_score = %s WHERE id = %s",
                (home, away, existing["id"]),
            )
        else:
            db.execute(
                "INSERT INTO predictions "
                "(user_id, match_id, predicted_home_score, predicted_away_score) "
                "VALUES (%s, %s, %s, %s)",
                (current_user.id, match_id, home, away),
            )
        flash("Prediction saved.", "success")
        return redirect(url_for("dashboard"))

    return render_template("predict.html", match=match, existing=existing)


@app.route("/leaderboard")
@login_required
def leaderboard():
    ranked = db.query_all(
        "SELECT u.id, u.username, COALESCE(SUM(p.points), 0) AS total_points, "
        "COUNT(p.id) AS predictions_made "
        "FROM users u "
        "LEFT JOIN predictions p ON p.user_id = u.id "
        "WHERE u.is_admin = 0 "
        "GROUP BY u.id, u.username "
        "ORDER BY total_points DESC, u.username ASC"
    )
    return render_template("leaderboard.html", ranked=ranked)


# --------------------------------------------------------------------------
# Admin routes
# --------------------------------------------------------------------------

@app.route("/admin")
@login_required
def admin_dashboard():
    admin_required()
    matches = db.query_all("SELECT * FROM matches ORDER BY kickoff_at DESC")
    matches = [annotate_match(m) for m in matches]
    return render_template("admin_dashboard.html", matches=matches)


@app.route("/admin/matches/new", methods=["GET", "POST"])
@login_required
def admin_add_match():
    admin_required()

    if request.method == "POST":
        home_team = request.form.get("home_team", "").strip()
        away_team = request.form.get("away_team", "").strip()
        kickoff_raw = request.form.get("kickoff_at", "")

        error = None
        kickoff_at = None
        if not home_team or not away_team or not kickoff_raw:
            error = "All fields are required."
        elif home_team.lower() == away_team.lower():
            error = "Home and away teams must be different."
        else:
            try:
                kickoff_at = datetime.fromisoformat(kickoff_raw)
            except ValueError:
                error = "Invalid kickoff date/time."

        if error:
            flash(error, "error")
            return render_template(
                "admin_add_match.html",
                home_team=home_team, away_team=away_team, kickoff_at=kickoff_raw,
            )

        db.execute(
            "INSERT INTO matches (home_team, away_team, kickoff_at, created_by) "
            "VALUES (%s, %s, %s, %s)",
            (home_team, away_team, kickoff_at, current_user.id),
        )
        flash(f"Match added: {home_team} vs {away_team}.", "success")
        return redirect(url_for("admin_dashboard"))

    return render_template("admin_add_match.html")


@app.route("/admin/matches/<int:match_id>/result", methods=["GET", "POST"])
@login_required
def admin_enter_result(match_id):
    admin_required()
    match = db.query_one("SELECT * FROM matches WHERE id = %s", (match_id,))
    if match is None:
        abort(404)
    match = annotate_match(match)

    if request.method == "POST":
        try:
            home = int(request.form["home_score"])
            away = int(request.form["away_score"])
            if home < 0 or away < 0:
                raise ValueError
        except (KeyError, ValueError):
            flash("Enter valid, non-negative scores for both teams.", "error")
            return render_template("admin_enter_result.html", match=match)

        db.execute(
            "UPDATE matches SET actual_home_score = %s, actual_away_score = %s, "
            "status = 'completed' WHERE id = %s",
            (home, away, match_id),
        )
        score_match(match_id, home, away)  # award points to all predictions

        flash("Result saved and points awarded.", "success")
        return redirect(url_for("admin_dashboard"))

    return render_template("admin_enter_result.html", match=match)


@app.route("/admin/matches/<int:match_id>/predictions")
@login_required
def admin_view_predictions(match_id):
    admin_required()
    match = db.query_one("SELECT * FROM matches WHERE id = %s", (match_id,))
    if match is None:
        abort(404)
    match = annotate_match(match)

    predictions = db.query_all(
        "SELECT p.*, u.username FROM predictions p "
        "JOIN users u ON u.id = p.user_id "
        "WHERE p.match_id = %s "
        "ORDER BY (p.points IS NULL) ASC, p.points DESC, u.username ASC",
        (match_id,),
    )
    return render_template("admin_view_predictions.html", match=match, predictions=predictions)


@app.route("/admin/matches/<int:match_id>/delete", methods=["POST"])
@login_required
def admin_delete_match(match_id):
    admin_required()
    db.execute("DELETE FROM matches WHERE id = %s", (match_id,))
    flash("Match deleted.", "info")
    return redirect(url_for("admin_dashboard"))


if __name__ == "__main__":
    app.run(debug=True)
