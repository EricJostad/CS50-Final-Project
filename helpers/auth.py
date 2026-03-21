# Standard library
from functools import wraps

# Third-party libraries
from flask import g, redirect, request, url_for, session

# Local imports
from models import User


# Load user before each request
def load_user():
    g.user = None
    user_id = session.get("user_id")

    if user_id is not None:
        g.user = User.query.get(user_id)


# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("login", next=request.path))
        return f(*args, **kwargs)
    return decorated_function
