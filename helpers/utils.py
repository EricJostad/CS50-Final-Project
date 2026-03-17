# Third-party libraries
import requests

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Simple in-memory cache for wiki API responses
wiki_cache = {}


def cached_get(url, params=None):
    """Cached GET request wrapper for Wiki API calls and full HTML fetches."""
    key = (url, tuple(sorted((params or {}).items())))
    if key in wiki_cache:
        return wiki_cache[key]

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;"
            "q=0.9,image/avif,image/webp,*/*;q=0.8"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.google.com/",
        "DNT": "1",
        "Upgrade-Insecure-Requests": "1",
    }

    resp = requests.get(url, params=params, headers=headers, timeout=10)
    wiki_cache[key] = resp
    return resp
