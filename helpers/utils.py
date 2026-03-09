# Third-party libraries
import requests

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
