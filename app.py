# Standard library
import os

# Third-party libraries
from flask import Flask, redirect, render_template, request, session
from flask_session import Session
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

# Local application imports
from helpers.mobile_suits import get_mobile_suit
from helpers.series import get_series
from helpers.auth import login_required
from helpers.utils import apology
from helpers.auth import load_user
from models import User, db

app = Flask(__name__, instance_relative_config=True)

# Ensure instance folder exists
os.makedirs(app.instance_path, exist_ok=True)

# Use absolute path for the database
db_path = os.path.join(app.instance_path, "gundam.db")
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


@app.before_request
def before_request():
    load_user()


@app.route("/")
def index():

    user_id = session.get("user_id")

    user = None
    if user_id:
        user = User.query.filter_by(id=user_id).first()

    return render_template("index.html", user=user)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    session.clear()

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if not username or not password:
            return apology("Must provide username and password")

        user = User.query.filter_by(username=username).first()

        if not user or not check_password_hash(user.password, password):
            return apology("Invalid username or password")

        # Remember which user has logged in
        session["user_id"] = user.id

        # Redirect user to home page
        return redirect("/")
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""
    session.clear()
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        if not username or not password or not confirmation:
            return apology("Must provide username and password", 400)

        elif password != confirmation:
            return apology("Passwords do not match", 400)

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return apology("Username already taken", 400)

        hashed_password = generate_password_hash(password)
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        return redirect("/login")

    return render_template("register.html")


def classify_query(query):
    """Simple heuristic to classify query as 'mobile_suit' or 'series'."""
    query = query.lower()

    series_keywords = ["anime", "episode", "film", "gundam",
                       "season", "series", "show", "movie", "ova", "tv"]

    if any(keyword in query for keyword in series_keywords):
        return "series"

    else:
        # Default to mobile suit if unsure
        return "mobile_suit"


@app.route("/search")
def search():
    """Search Gundam wiki for user query and display results."""
    query = request.args.get("query", "").strip()

    if not query:
        return render_template("search_results.html", results={}, query=query)

    category = classify_query(query)
    results = {}

    if category == "mobile_suit":
        # Direct mobile suit search
        results["mobile_suits"] = get_mobile_suit(query)

    else:
        # Series search
        series_list = get_series(query)
        results["series"] = series_list

    return render_template("search_results.html", results=results, query=query)


@app.route("/settings")
@login_required
def settings():
    """Allow user to change their settings"""

    return render_template("settings.html")


@app.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    """Allow user to change password"""

    # Query user data for easy access in function
    user_id = session.get("user_id")
    user = User.query.filter_by(id=user_id).first()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        old_pw = request.form.get("old password")
        new_pw = request.form.get("new password")
        confirm_pw = request.form.get("confirm password")

        # Help to validate the the request is coming from the correct user
        if not old_pw:
            return apology("must provide your current password")
        elif not check_password_hash(user.password, old_pw):
            return apology("invalid password")

        else:
            # If so, check that the password does not match their current password
            if old_pw == new_pw:
                return apology("cannot use previous password as new password")
            # Ensure that the new password meets the minimum requirement
            elif len(new_pw) < 6:
                return apology("password must be at least 6 characters")
            # Ensure that the user is providing the correct new password
            elif new_pw != confirm_pw:
                return apology("passwords must match")

        user.password = generate_password_hash(new_pw)
        db.session.commit()

        # Redirect user to home page
        return redirect("/")

    return render_template("change-password.html")


@app.route("/deactivate-account", methods=["GET", "POST"])
@login_required
def deactivate_account():
    """Allow user to permanantly deactivate their account"""

    # Pulling userdata for easy access in function
    user_id = session.get("user_id")
    user = User.query.filter_by(id=user_id).first()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        user_pw = request.form.get("password")

        # Help to validate the the request is coming from the correct user
        if not user_pw:
            return apology("must provide password")
        elif not check_password_hash(user.password, user_pw):
            return apology("invalid password")

        # Move user to confirm deactivation
        else:
            return render_template("/confirm-deactivate.html")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("deactivate-account.html")


@app.route("/confirm_deactivate", methods=["GET", "POST"])
@login_required
def confirm_deactivate():
    """Allow user to confirm that they would like to deactivate their account"""

    # Pulling userdata for easy access in function
    user_id = session.get("user_id")
    user = User.query.filter_by(id=user_id).first()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        user_pw = request.form.get("password")

        # Help to validate the the request is coming from the correct user
        if not user_pw:
            return apology("must provide password")
        elif not check_password_hash(user.password, user_pw):
            return apology("invalid password")
        # Deactivate user account, but does not delete user data from database for the purposes of record keeping
        else:

            user.is_active = False
            db.session.commit()

            # Forget any user_id
            session.clear()

            # Redirect user to login form
            return redirect("/login")
    else:
        return render_template("confirm_deactivate.html", user=user)


with app.app_context():
    db.create_all()
