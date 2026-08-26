"""
app.py
Main Flask application for the To-Do List app.

Provides:
- User registration / login / logout (session-based auth)
- Task CRUD (create, read, update, delete)
- Mark task complete
- Priority + due date support
- Each user can only ever see/modify their own tasks

Run with:
    python app.py
"""

import os
import re
from datetime import datetime, date
from functools import wraps

from flask import Flask, request, jsonify, session
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import pymysql

from db import get_connection

load_dotenv()

# ------------------------------------------------------------------
# App setup
# ------------------------------------------------------------------
app = Flask(__name__, static_folder="../frontend", static_url_path="")
app.secret_key = os.environ["SECRET_KEY"]

# Session cookie settings (relaxed for local http dev)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="None",
    SESSION_COOKIE_SECURE=True,
)

# CORS only matters if you serve the frontend from a different origin
# (e.g. a separate dev server on another port). Since this app also
# serves the frontend directly, supports_credentials keeps cookies
# working either way.
CORS(
    app,
    origins=["https://animated-stardust-9e12d3.netlify.app"],
    supports_credentials=True
)

EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@gmail\.com$")
VALID_PRIORITIES = {"low", "medium", "high"}


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def login_required(f):
    """Decorator that blocks a route unless the user has a session."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Authentication required"}), 401
        return f(*args, **kwargs)
    return wrapper


def parse_due_date(value):
    """Validates a 'YYYY-MM-DD' string, returns it or raises ValueError."""
    if value in (None, ""):
        return None
    datetime.strptime(value, "%Y-%m-%d")  # raises ValueError if malformed
    return value


def task_to_dict(row):
    """Normalizes a DB row into JSON-friendly types."""
    due = row.get("due_date")
    if isinstance(due, date):
        due = due.isoformat()
    created = row.get("created_at")
    updated = row.get("updated_at")
    return {
        "id": row["id"],
        "title": row["title"],
        "description": row["description"],
        "priority": row["priority"],
        "due_date": due,
        "completed": bool(row["completed"]),
        "created_at": created.isoformat() if created else None,
        "updated_at": updated.isoformat() if updated else None,
    }


# ------------------------------------------------------------------
# Auth routes
# ------------------------------------------------------------------
@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not username or len(username) < 3:
        return jsonify({"error": "Username must be at least 3 characters"}), 400
    
    if not EMAIL_RE.match(email):
        return jsonify({"error": "Please enter a valid email address"}), 400
    
    if not re.match(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*[0-9])(?=.*[^A-Za-z0-9]).{8,}$", password):
        return jsonify({
            "error": "Password must be at least 8 characters and contain uppercase, lowercase, number, and special character."
        }), 400

    password_hash = generate_password_hash(password)

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Check for existing username/email up front for a friendly error
            cur.execute(
                "SELECT id FROM users WHERE username=%s OR email=%s",
                (username, email),
            )
            if cur.fetchone():
                return jsonify({"error": "Username or email already taken"}), 409

            cur.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
                (username, email, password_hash),
            )
            conn.commit()
            user_id = cur.lastrowid

        session["user_id"] = user_id
        session["username"] = username
        return jsonify({"id": user_id, "username": username, "email": email}), 201

    except pymysql.err.IntegrityError:
        conn.rollback()
        return jsonify({"error": "Username or email already taken"}), 409
    finally:
        conn.close()


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username_or_email = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username_or_email or not password:
        return jsonify({"error": "Username and password are required"}), 400

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, username, email, password_hash FROM users "
                "WHERE username=%s OR email=%s",
                (username_or_email, username_or_email),
            )
            user = cur.fetchone()

        if not user or not check_password_hash(user["password_hash"], password):
            return jsonify({"error": "Invalid username or password"}), 401

        session["user_id"] = user["id"]
        session["username"] = user["username"]
        return jsonify({"id": user["id"], "username": user["username"], "email": user["email"]})
    finally:
        conn.close()


@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out"})


@app.route("/api/me", methods=["GET"])
def me():
    """Lets the frontend check whether a session is currently active."""
    if "user_id" not in session:
        return jsonify({"authenticated": False}), 200
    return jsonify({
        "authenticated": True,
        "id": session["user_id"],
        "username": session["username"],
    })


# ------------------------------------------------------------------
# Task routes  (all scoped to the logged-in user)
# ------------------------------------------------------------------
@app.route("/api/tasks", methods=["GET"])
@login_required
def get_tasks():
    """
    Returns all tasks belonging to the logged-in user.
    Optional query params:
      ?completed=true|false
      ?priority=low|medium|high
      ?sort=due_date|priority|created_at
    """
    user_id = session["user_id"]
    completed = request.args.get("completed")
    priority = request.args.get("priority")
    sort = request.args.get("sort", "created_at")

    sort_columns = {"due_date": "due_date", "priority": "priority", "created_at": "created_at"}
    order_by = sort_columns.get(sort, "created_at")

    query = "SELECT * FROM tasks WHERE user_id=%s"
    params = [user_id]

    if completed in ("true", "false"):
        query += " AND completed=%s"
        params.append(completed == "true")

    if priority in VALID_PRIORITIES:
        query += " AND priority=%s"
        params.append(priority)

    query += f" ORDER BY completed ASC, {order_by} ASC"

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
        return jsonify([task_to_dict(r) for r in rows])
    finally:
        conn.close()


@app.route("/api/tasks/<int:task_id>", methods=["GET"])
@login_required
def get_task(task_id):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM tasks WHERE id=%s AND user_id=%s",
                (task_id, session["user_id"]),
            )
            row = cur.fetchone()
        if not row:
            return jsonify({"error": "Task not found"}), 404
        return jsonify(task_to_dict(row))
    finally:
        conn.close()


@app.route("/api/tasks", methods=["POST"])
@login_required
def create_task():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    description = (data.get("description") or "").strip()
    priority = data.get("priority", "medium")
    due_date_raw = data.get("due_date")

    if not title:
        return jsonify({"error": "Title is required"}), 400
    if priority not in VALID_PRIORITIES:
        return jsonify({"error": "Priority must be low, medium, or high"}), 400
    try:
        due_date = parse_due_date(due_date_raw)
    except ValueError:
        return jsonify({"error": "due_date must be in YYYY-MM-DD format"}), 400

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO tasks (user_id, title, description, priority, due_date)
                   VALUES (%s, %s, %s, %s, %s)""",
                (session["user_id"], title, description, priority, due_date),
            )
            conn.commit()
            task_id = cur.lastrowid

            cur.execute("SELECT * FROM tasks WHERE id=%s", (task_id,))
            row = cur.fetchone()
        return jsonify(task_to_dict(row)), 201
    finally:
        conn.close()


@app.route("/api/tasks/<int:task_id>", methods=["PUT"])
@login_required
def update_task(task_id):
    """Full update of a task's editable fields."""
    data = request.get_json(silent=True) or {}

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM tasks WHERE id=%s AND user_id=%s",
                (task_id, session["user_id"]),
            )
            existing = cur.fetchone()
            if not existing:
                return jsonify({"error": "Task not found"}), 404

            title = (data.get("title", existing["title"]) or "").strip()
            description = data.get("description", existing["description"])
            priority = data.get("priority", existing["priority"])
            due_date_raw = data.get("due_date", existing["due_date"])
            completed = data.get("completed", existing["completed"])

            if not title:
                return jsonify({"error": "Title cannot be empty"}), 400
            if priority not in VALID_PRIORITIES:
                return jsonify({"error": "Priority must be low, medium, or high"}), 400
            try:
                due_date = parse_due_date(
                    due_date_raw.isoformat() if isinstance(due_date_raw, date) else due_date_raw
                )
            except ValueError:
                return jsonify({"error": "due_date must be in YYYY-MM-DD format"}), 400

            cur.execute(
                """UPDATE tasks
                   SET title=%s, description=%s, priority=%s, due_date=%s, completed=%s
                   WHERE id=%s AND user_id=%s""",
                (title, description, priority, due_date, bool(completed), task_id, session["user_id"]),
            )
            conn.commit()

            cur.execute("SELECT * FROM tasks WHERE id=%s", (task_id,))
            row = cur.fetchone()
        return jsonify(task_to_dict(row))
    finally:
        conn.close()


@app.route("/api/tasks/<int:task_id>/complete", methods=["PATCH"])
@login_required
def toggle_complete(task_id):
    """Quick toggle for marking a task done / not done."""
    data = request.get_json(silent=True) or {}

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM tasks WHERE id=%s AND user_id=%s",
                (task_id, session["user_id"]),
            )
            existing = cur.fetchone()
            if not existing:
                return jsonify({"error": "Task not found"}), 404

            new_value = data.get("completed")
            if new_value is None:
                new_value = not existing["completed"]  # no value given -> just flip it

            cur.execute(
                "UPDATE tasks SET completed=%s WHERE id=%s AND user_id=%s",
                (bool(new_value), task_id, session["user_id"]),
            )
            conn.commit()

            cur.execute("SELECT * FROM tasks WHERE id=%s", (task_id,))
            row = cur.fetchone()
        return jsonify(task_to_dict(row))
    finally:
        conn.close()


@app.route("/api/tasks/<int:task_id>", methods=["DELETE"])
@login_required
def delete_task(task_id):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM tasks WHERE id=%s AND user_id=%s",
                (task_id, session["user_id"]),
            )
            conn.commit()
            deleted = cur.rowcount
        if deleted == 0:
            return jsonify({"error": "Task not found"}), 404
        return jsonify({"message": "Task deleted"})
    finally:
        conn.close()


# ------------------------------------------------------------------
# Serve the frontend (index.html, login.html, register.html, css/js)
# ------------------------------------------------------------------
@app.route("/")
def serve_index():
    return app.send_static_file("index.html")


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "0") == "1", port=5000)
