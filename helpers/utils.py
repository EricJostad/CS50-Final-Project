# Third-party libraries
import requests
from flask import render_template

# Load environment variables
from dotenv import load_dotenv
load_dotenv()


# Simple in-memory cache for wiki API responses
wiki_cache = {}


def cached_get(url, params=None):
    """Cached GET request wrapper for Wiki API calls."""
    key = (url, tuple(sorted((params or {}).items())))
    if key in wiki_cache:
        return wiki_cache[key]

    resp = requests.get(url, params=params, timeout=3)
    wiki_cache[key] = resp
    return resp


def fix_relative_links(html):
    if not html:
        return html
    return html.replace('href="/wiki/', 'href="https://gundam.fandom.com/wiki/')


def apology(message, code=400):
    """Render message as an apology to user."""

    return render_template("apology.html", top=code, bottom=message), code
