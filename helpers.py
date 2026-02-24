from functools import wraps
from flask import g, request, redirect, url_for


def login_required(f):
    """Decorator that requires login for routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.user is None:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function
