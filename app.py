import os
from datetime import datetime
from functools import wraps

import psycopg2
import psycopg2.extras
from flask import Flask, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

DATABASE_URL = os.environ["DATABASE_URL"]

app = Flask(__name__)
app.secret_key = os.environ["SECRET_KEY"]


def get_db():
    if "db" not in g:
        g.db = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    conn = psycopg2.connect(DATABASE_URL)
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                content TEXT NOT NULL,
                done BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TEXT NOT NULL
            )
            """
        )
        cur.execute("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS user_id BIGINT REFERENCES users(id)")
    conn.commit()
    conn.close()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")
        if not username or not password:
            flash("아이디와 비밀번호를 모두 입력해주세요.")
        elif password != confirm:
            flash("비밀번호가 서로 일치하지 않습니다.")
        else:
            db = get_db()
            with db.cursor() as cur:
                cur.execute("SELECT id FROM users WHERE username = %s", (username,))
                if cur.fetchone():
                    flash("이미 사용 중인 아이디입니다.")
                    return render_template("register.html")
                cur.execute(
                    "INSERT INTO users (username, password_hash, created_at) VALUES (%s, %s, %s) RETURNING id",
                    (username, generate_password_hash(password), datetime.now().strftime("%Y-%m-%d %H:%M")),
                )
                user_id = cur.fetchone()["id"]
            db.commit()
            session["user_id"] = user_id
            session["username"] = username
            return redirect(url_for("index"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        db = get_db()
        with db.cursor() as cur:
            cur.execute("SELECT id, password_hash FROM users WHERE username = %s", (username,))
            user = cur.fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["username"] = username
            return redirect(url_for("index"))
        flash("아이디 또는 비밀번호가 올바르지 않습니다.")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def index():
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            "SELECT * FROM tasks WHERE user_id = %s ORDER BY done ASC, id DESC",
            (session["user_id"],),
        )
        tasks = cur.fetchall()
    total = len(tasks)
    done_count = sum(1 for t in tasks if t["done"])
    return render_template(
        "index.html",
        tasks=tasks,
        total=total,
        done_count=done_count,
        username=session["username"],
    )


@app.route("/add", methods=["POST"])
@login_required
def add():
    content = request.form.get("content", "").strip()
    if content:
        db = get_db()
        with db.cursor() as cur:
            cur.execute(
                "INSERT INTO tasks (content, done, created_at, user_id) VALUES (%s, FALSE, %s, %s)",
                (content, datetime.now().strftime("%Y-%m-%d %H:%M"), session["user_id"]),
            )
        db.commit()
    return redirect(url_for("index"))


@app.route("/toggle/<int:task_id>", methods=["POST"])
@login_required
def toggle(task_id):
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            "UPDATE tasks SET done = NOT done WHERE id = %s AND user_id = %s",
            (task_id, session["user_id"]),
        )
    db.commit()
    return redirect(url_for("index"))


@app.route("/delete/<int:task_id>", methods=["POST"])
@login_required
def delete(task_id):
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            "DELETE FROM tasks WHERE id = %s AND user_id = %s",
            (task_id, session["user_id"]),
        )
    db.commit()
    return redirect(url_for("index"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
