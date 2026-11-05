"""A minimal blog app used to demo the aspen-connector."""

import sqlite3

from flask import Flask, abort, redirect, render_template_string, request, url_for

app = Flask(__name__)

DB_PATH = "blog.db"


def get_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db


def init_db():
    db = get_db()
    db.execute(
        "CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY, title TEXT, body TEXT)"
    )
    if db.execute("SELECT COUNT(*) FROM posts").fetchone()[0] == 0:
        db.executemany(
            "INSERT INTO posts (title, body) VALUES (?, ?)",
            [
                ("Hello, World", "This is the first post on this blog."),
                ("Why We Blog", "Blogging keeps us honest and helps us think."),
            ],
        )
    db.commit()
    db.close()


init_db()

INDEX_TEMPLATE = """
<h1>Blog</h1>
<form action="{{ url_for('search') }}">
  <input name="q" placeholder="Search posts">
  <button type="submit">Search</button>
</form>
<ul>
  {% for post in posts %}
    <li><a href="{{ url_for('view_post', post_id=post['id']) }}">{{ post['title'] }}</a></li>
  {% endfor %}
</ul>
<a href="{{ url_for('new_post') }}">New post</a>
"""

POST_TEMPLATE = """
<h1>{{ post['title'] }}</h1>
<p>{{ post['body'] }}</p>
<a href="{{ url_for('index') }}">Back</a>
"""

NEW_POST_TEMPLATE = """
<h1>New post</h1>
<form method="post">
  <input name="title" placeholder="Title"><br>
  <textarea name="body" placeholder="Body"></textarea><br>
  <button type="submit">Publish</button>
</form>
"""

SEARCH_TEMPLATE = """
<h1>Search results for "{{ q }}"</h1>
<ul>
  {% for post in posts %}
    <li><a href="{{ url_for('view_post', post_id=post['id']) }}">{{ post['title'] }}</a></li>
  {% endfor %}
</ul>
<a href="{{ url_for('index') }}">Back</a>
"""


@app.route("/")
def index():
    db = get_db()
    posts = db.execute("SELECT id, title FROM posts").fetchall()
    db.close()
    return render_template_string(INDEX_TEMPLATE, posts=posts)


@app.route("/post/<int:post_id>")
def view_post(post_id):
    db = get_db()
    post = db.execute(
        "SELECT id, title, body FROM posts WHERE id = ?", (post_id,)
    ).fetchone()
    db.close()
    if post is None:
        abort(404)
    return render_template_string(POST_TEMPLATE, post=post)


@app.route("/post/new", methods=["GET", "POST"])
def new_post():
    if request.method == "POST":
        db = get_db()
        cursor = db.execute(
            "INSERT INTO posts (title, body) VALUES (?, ?)",
            (request.form.get("title", "Untitled"), request.form.get("body", "")),
        )
        db.commit()
        post_id = cursor.lastrowid
        db.close()
        return redirect(url_for("view_post", post_id=post_id))
    return render_template_string(NEW_POST_TEMPLATE)


@app.route("/search")
def search():
    q = request.args.get("q", "")
    db = get_db()
    query = f"SELECT id, title, body FROM posts WHERE title LIKE '%{q}%' OR body LIKE '%{q}%'"
    posts = db.execute(query).fetchall()
    db.close()
    return render_template_string(SEARCH_TEMPLATE, q=q, posts=posts)


if __name__ == "__main__":
    app.run(debug=False)
