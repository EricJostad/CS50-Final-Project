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
        wiki_url = f"https://gundam.fandom.com/wiki/{title.replace(' ', '_')}"

        # Step 1: Get the file page for the main image
        file_params = {
            "action": "query",
            "titles": title,
            "prop": "images",
            "format": "json",
            "origin": "*"
        }

        file_resp = requests.get(WIKI_API, params=file_params).json()
        pages_dict = file_resp.get("query", {}).get("pages", {})

        image_url = None

        # Step 2: Find the first image file name
        for _, p in pages_dict.items():
            images = p.get("images", [])
            if images:
                file_title = images[0]["title"]  # e.g. "File:Tallgeese.png"

                # Step 3: Fetch the file page HTML (not blocked)
                file_page_url = f"https://gundam.fandom.com/wiki/{file_title.replace(' ', '_')}"
                file_html = requests.get(file_page_url).text
                file_soup = BeautifulSoup(file_html, "html.parser")

                # Step 4: Extract the CDN image URL
                full_img = file_soup.find("a", class_="image")
                if full_img:
                    img = full_img.find("img")
                    if img:
                        src = img.get("src")
                        if src.startswith("//"):
                            src = "https:" + src
                        image_url = src

        # Step 5: Extract text fields (your existing logic)
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

        model_number = None
        manufacturer = None
        height = None

        for row in soup.select(".pi-data, tr"):
            label = row.find(class_="pi-data-label") or row.find("th")
            value = row.find(class_="pi-data-value") or row.find("td")

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

        results.append({
            "title": title,
            "wiki_url": wiki_url,
            "image_url": image_url,
            "model_number": model_number,
            "manufacturer": manufacturer,
            "height": height,
        })

    return results
