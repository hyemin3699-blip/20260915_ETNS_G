import os
from datetime import datetime

import psycopg2
import psycopg2.extras
from flask import Flask, g, redirect, render_template, request, url_for

DATABASE_URL = os.environ["DATABASE_URL"]

app = Flask(__name__)


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
            CREATE TABLE IF NOT EXISTS tasks (
                id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                content TEXT NOT NULL,
                done BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TEXT NOT NULL
            )
            """
        )
    conn.commit()
    conn.close()


@app.route("/")
def index():
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT * FROM tasks ORDER BY done ASC, id DESC")
        tasks = cur.fetchall()
    total = len(tasks)
    done_count = sum(1 for t in tasks if t["done"])
    return render_template(
        "index.html", tasks=tasks, total=total, done_count=done_count
    )


@app.route("/add", methods=["POST"])
def add():
    content = request.form.get("content", "").strip()
    if content:
        db = get_db()
        with db.cursor() as cur:
            cur.execute(
                "INSERT INTO tasks (content, done, created_at) VALUES (%s, FALSE, %s)",
                (content, datetime.now().strftime("%Y-%m-%d %H:%M")),
            )
        db.commit()
    return redirect(url_for("index"))


@app.route("/toggle/<int:task_id>", methods=["POST"])
def toggle(task_id):
    db = get_db()
    with db.cursor() as cur:
        cur.execute("UPDATE tasks SET done = NOT done WHERE id = %s", (task_id,))
    db.commit()
    return redirect(url_for("index"))


@app.route("/delete/<int:task_id>", methods=["POST"])
def delete(task_id):
    db = get_db()
    with db.cursor() as cur:
        cur.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
    db.commit()
    return redirect(url_for("index"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
