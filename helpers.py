from functools import wraps
from flask import g, request, redirect, url_for
import requests
from bs4 import BeautifulSoup

WIKI_API = "https://gundam.fandom.com/api.php"


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.user is None:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


# ------------------------------------------------------------
# IMAGE HELPERS (RELIABLE — USE imageinfo + URL verification)
# ------------------------------------------------------------

def get_image_url(filename):
    """
    Given a File: filename from MediaWiki, return the actual CDN URL.
    This avoids broken 'latest?cb=' URLs and ensures the file exists.
    """
    params = {
        "action": "query",
        "titles": filename,
        "prop": "imageinfo",
        "iiprop": "url",
        "format": "json",
        "origin": "*"
    }

    r = requests.get(WIKI_API, params=params)
    r.raise_for_status()
    pages = r.json().get("query", {}).get("pages", {})

    for page in pages.values():
        info = page.get("imageinfo", [])
        if not info:
            continue

        url = info[0].get("url")
        if not url:
            continue

        # Verify the URL exists (avoid 404s)
        head = requests.head(url)
        if head.status_code == 200:
            return url

    return None


def get_page_images(title):
    """
    Return a list of image filenames used on a page.
    """
    params = {
        "action": "query",
        "prop": "images",
        "titles": title,
        "format": "json",
        "origin": "*"
    }

    r = requests.get(WIKI_API, params=params)
    r.raise_for_status()
    pages = r.json().get("query", {}).get("pages", {})

    for page in pages.values():
        return [img.get("title") for img in page.get("images", [])]

    return []


def get_best_image(title):
    """
    Return the first valid image URL for a page.
    Uses imageinfo + HEAD verification to avoid broken images.
    """
    images = get_page_images(title)

    for img in images:
        if img.lower().endswith((".png", ".jpg", ".jpeg", ".gif")):
            url = get_image_url(img)
            if url:
                return url

    return None


# ------------------------------------------------------------
# INFOBOX HELPERS (TABLE + PORTABLE INFOBOX)
# ------------------------------------------------------------

def extract_fields_from_infobox(soup):
    """
    Extract model_number, manufacturer, height from:
    - classic <table class="infobox">
    - modern <div class="portable-infobox">
    """
    model_number = None
    manufacturer = None
    height = None

    # Classic table.infobox
    table_infobox = soup.find("table", {"class": "infobox"})
    if table_infobox:
        for row in table_infobox.find_all("tr"):
            header = row.find("th")
            value = row.find("td")
            if not header or not value:
                continue

            key = header.get_text(" ", strip=True).lower()
            val = value.get_text(" ", strip=True)

            if "model" in key and model_number is None:
                model_number = val
            elif "manufacturer" in key and manufacturer is None:
                manufacturer = val
            elif "height" in key and height is None:
                height = val

    # Portable infobox (Fandom modern)
    portable = soup.find("div", class_="portable-infobox")
    if portable:
        for node in portable.find_all(["section", "div"], recursive=True):
            label = node.find(["h3", "h2", "h4", "dt"])
            value = node.find(["div", "dd", "p"])
            if not label or not value:
                continue

            key = label.get_text(" ", strip=True).lower()
            val = value.get_text(" ", strip=True)

            if "model" in key and model_number is None:
                model_number = val
            elif "manufacturer" in key and manufacturer is None:
                manufacturer = val
            elif "height" in key and height is None:
                height = val

    return model_number, manufacturer, height


# ------------------------------------------------------------
# MAIN SCRAPER
# ------------------------------------------------------------

def get_mobile_suit(name):
    name = name.lower()

    # Search for matching pages
    params = {
        "action": "query",
        "list": "search",
        "srsearch": name,
        "format": "json",
        "origin": "*"
    }

    response = requests.get(WIKI_API, params=params)
    response.raise_for_status()
    pages = response.json().get("query", {}).get("search", [])

    results = []

    for page in pages:
        title = page["title"]

        # Fetch page HTML for infobox fields
        parse_params = {
            "action": "parse",
            "page": title,
            "prop": "text",
            "format": "json",
            "origin": "*"
        }

        parse_response = requests.get(WIKI_API, params=parse_params)
        parse_response.raise_for_status()
        parsed = parse_response.json()

        html = parsed.get("parse", {}).get("text", {}).get("*", "")
        soup = BeautifulSoup(html, "html.parser")

        model_number, manufacturer, height = extract_fields_from_infobox(soup)

        data = {
            "title": title,
            "wiki_url": f"https://gundam.fandom.com/wiki/{title.replace(' ', '_')}",
            "image_url": None,
            "model_number": model_number,
            "manufacturer": manufacturer,
            "height": height,
        }

        # Get a verified working image URL
        data["image_url"] = get_best_image(title)

        results.append(data)

    return results
