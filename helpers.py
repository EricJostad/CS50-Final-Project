from functools import wraps
from flask import g, request, redirect, url_for
import requests
from bs4 import BeautifulSoup
from serpapi import GoogleSearch
import os

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

WIKI_API = "https://gundam.fandom.com/api.php"

# Required login decorator


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.user is None:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


# Google image fetcher via SerpAPI
def get_first_google_image(query):
    """Return the first Google Images result URL using SerpAPI."""

    api_key = os.getenv("SERPAPI_KEY")
    print("DEBUG SERPAPI_KEY =", api_key)  # DEBUG

    if not api_key:
        print("ERROR: SERPAPI_KEY missing from environment")
        return None

    params = {
        "engine": "google",
        "q": query,
        "tbm": "isch",  # REQUIRED for Google Images
        "api_key": api_key
    }

    try:
        search = GoogleSearch(params)
        results = search.get_dict()

        images = results.get("images_results", [])
        print("DEBUG GOOGLE IMAGES RAW =", images[:1])  # DEBUG

        if images:
            return images[0].get("original") or images[0].get("thumbnail")

        print("DEBUG: No Google images found for:", query)

    except Exception as e:
        print("SerpAPI error:", e)

    return None


# Gundam Fandom Wiki scraper
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

    response = requests.get(WIKI_API, params=params)
    response.raise_for_status()
    pages = response.json().get("query", {}).get("search", [])

    results = []

    for page in pages[:3]:  # Limit to top 3 results for performance
        title = page["title"]
        wiki_url = f"https://gundam.fandom.com/wiki/{title.replace(' ', '_')}"

        print("\n==============================")
        print("DEBUG START:", title)
        print("==============================")

        # ----------------------------------------
        # REMOVE WIKI IMAGE SCRAPING — USE NONE
        # ----------------------------------------
        image_url = None
        print("DEBUG WIKI IMAGE URL = None (disabled)")  # DEBUG

        # Extract infobox text fields
        model_number = None
        manufacturer = None
        height = None

        try:
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

        except Exception as e:
            print("Wiki parse error:", e)

        # Google Image (SerpAPI)
        google_image = get_first_google_image(title + " gundam")

        print("DEBUG GOOGLE IMAGE URL =", google_image)  # DEBUG

        # Final structured result for this page
        result_obj = {
            "title": title,
            "wiki_url": wiki_url,
            "image_url": image_url,  # always None now
            "google_image": google_image,
            "model_number": model_number,
            "manufacturer": manufacturer,
            "height": height,
        }

        print("DEBUG FINAL RESULT =", result_obj)  # DEBUG

        results.append(result_obj)

    return results
