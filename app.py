import os
from flask_sqlalchemy import SQLAlchemy
from flask import Flask, render_template, request, session, redirect
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///gundam.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

db = SQLAlchemy(app)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        if not request.form.get("username") or not request.form.get("password"):
            return render_template("login.html", error="Must provide username and password")

        users = db.session.execute("SELECT * FROM users WHERE username = ?",
                                   (request.form.get("username")))

        if len(users) != 1 or not check_password_hash(users[0]["password"], request.form.get("password")):
            return render_template("login.html", error="Invalid username or password")

        # Remember which user has logged in
        session["user_id"] = users[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        if not request.form.get("username") or not request.form.get("password") or not request.form.get("confirmation"):
            return render_template("register.html", error="Must provide username and password")

        if request.form.get("password") != request.form.get("confirmation"):
            return render_template("register.html", error="Passwords do not match")

        # Hash the password and insert the new user into the database
        hash = generate_password_hash(request.form.get("password"))
        try:
            db.session.execute("INSERT INTO users (username, password) VALUES (?, ?)",
                               (request.form.get("username"), hash))
            db.session.commit()
        except ValueError:
            return render_template("register.html", error="Username already taken")

        # Redirect user to login page
        return redirect("/login")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


@app.route("/search")
def search():
    """Search for mobile suits"""

    # Get the search query from the request
    query = request.args.get("query")

    # For now, just render the search results page with the query
    return render_template("search_results.html", query=query)
