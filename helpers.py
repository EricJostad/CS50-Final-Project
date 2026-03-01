from functools import wraps
from flask import g, request, redirect, url_for
import requests
from bs4 import BeautifulSoup

WIKI_API = "https://gundam.fandom.com/api.php"


def login_required(f):
    """Decorator that requires login for routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.user is None:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def get_mobile_suit(name):
    name = name.lower()

    # First, search for pages matching the name
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

        # Second, get the page content to extract details
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

        # Third, extract details from the infobox
        infobox = soup.find("table", {"class": "infobox"})
        data = {
            "title": title,
            "wiki_url": f"https://gundam.fandom.com/wiki/{title.replace(' ', '_')}",
            "image_url": None,
            "model_number": None,
            "manufacturer": None,
            "height": None,
        }

        # Extract image and details from the infobox if it exists
        if infobox:

            img = infobox.find("img")
            if img:
                data["image_url"] = img.get("src")

            rows = infobox.find_all("tr")
            for row in rows:
                header = row.find("th")
                value = row.find("td")
                if not header or not value:
                    continue

                key = header.text.strip().lower()
                val = value.get_text(" ", strip=True)

                if "model" in key:
                    data["model_number"] = val
                elif "manufacturer" in key:
                    data["manufacturer"] = val
                elif "height" in key:
                    data["height"] = val
        results.append(data)

    return results
