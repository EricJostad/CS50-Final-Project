# Standard library
import os
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache, wraps

# Third-party libraries
from bs4 import BeautifulSoup
from flask import g, redirect, request, url_for
from serpapi import GoogleSearch
import requests

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

WIKI_API = "https://gundam.fandom.com/api.php"

# -----------------------------
# LOGIN DECORATOR
# -----------------------------


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.user is None:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


# -----------------------------
# SIMPLE WIKI REQUEST CACHE
# -----------------------------
wiki_cache = {}


def cached_get(url, params=None):
    key = (url, tuple(sorted((params or {}).items())))
    if key in wiki_cache:
        return wiki_cache[key]
    resp = requests.get(url, params=params, timeout=3)
    wiki_cache[key] = resp
    return resp


# -----------------------------
# GOOGLE IMAGE FETCHER (CACHED)
# -----------------------------
@lru_cache(maxsize=200)
def get_first_google_image(query):
    """Return the first Google Images result URL using SerpAPI."""
    api_key = os.getenv("SERPAPI_KEY")

    if not api_key:
        print("ERROR: SERPAPI_KEY missing from environment")
        return None

    params = {
        "engine": "google",
        "q": query,
        "tbm": "isch",
        "api_key": api_key
    }

    try:
        search = GoogleSearch(params)
        results = search.get_dict()

        images = results.get("images_results", [])
        if images:
            return images[0].get("original") or images[0].get("thumbnail")

    except Exception as e:
        print("SerpAPI error:", e)

    return None  # fallback


# -----------------------------
# PARSE INFOBOX FIELDS (LIGHTER)
# -----------------------------
def parse_infobox(title):
    """Extract model number, manufacturer, height from wiki infobox."""
    params = {
        "action": "parse",
        "page": title,
        "prop": "text",
        "section": 0,   # Only fetch top section (faster)
        "format": "json",
        "origin": "*"
    }

    try:
        resp = cached_get(WIKI_API, params=params)
        parsed = resp.json()

        html = parsed.get("parse", {}).get("text", {}).get("*", "")
        soup = BeautifulSoup(html, "html.parser")

        model_number = None
        manufacturer = None
        height = None

        # Lighter selector: only .pi-data rows
        for row in soup.select(".pi-data"):
            label = row.find(class_="pi-data-label")
            value = row.find(class_="pi-data-value")

            if not label or not value:
                continue

            key = label.get_text(strip=True).lower()
            val = value.get_text(" ", strip=True)

            if "model" in key:
                model_number = val
            elif "manufacturer" in key:
                manufacturer = val
            elif "height" in key:
                height = val

        return model_number, manufacturer, height

    except Exception as e:
        print("Wiki parse error:", e)
        return None, None, None


# -----------------------------
# PROCESS A SINGLE RESULT (for threading)
# -----------------------------
def process_page(page):
    title = page["title"]
    wiki_url = f"https://gundam.fandom.com/wiki/{title.replace(' ', '_')}"

    # No wiki image scraping
    image_url = None

    # Infobox fields
    model_number, manufacturer, height = parse_infobox(title)

    # SerpAPI image (cached + fallback)
    google_image = get_first_google_image(title + " gundam")

    return {
        "title": title,
        "wiki_url": wiki_url,
        "image_url": image_url,
        "google_image": google_image,
        "model_number": model_number,
        "manufacturer": manufacturer,
        "height": height,
    }


# -----------------------------
# MAIN SEARCH FUNCTION
# -----------------------------
def get_mobile_suit(name):
    """Search Gundam Wiki and return structured mobile suit data."""
    name = name.lower()

    # Search for matching pages
    params = {
        "action": "query",
        "list": "search",
        "srsearch": name,
        "format": "json",
        "origin": "*"
    }

    response = cached_get(WIKI_API, params=params)
    pages = response.json().get("query", {}).get("search", [])

    # Limit to top 3
    pages = pages[:3]

    # Parallelize processing of each page
    with ThreadPoolExecutor(max_workers=3) as executor:
        results = list(executor.map(process_page, pages))

    return results
