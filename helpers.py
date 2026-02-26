from functools import wraps
from flask import g, request, redirect, url_for
import requests

BASE_URL = "https://gundam-api.pages.dev"


def login_required(f):
    """Decorator that requires login for routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.user is None:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def get_mobile_suit(name):
    url = f"{BASE_URL}/api/gundams?page=1&limit=200"
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()

    suits = data.get("results", [])
    name = name.lower()

    filtered = []
    for suit in suits:
        # Safely extract fields (avoids KeyError)
        gname = suit.get("gundamName", "")
        wname = suit.get("wikiName", "")
        header = suit.get("header", "")

        # Match against any available field
        if (
            name in gname.lower()
            or name in wname.lower()
            or name in header.lower()
        ):
            filtered.append(suit)

    return filtered
