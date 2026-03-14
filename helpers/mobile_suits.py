# Standard library
import re
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache   # <-- added

# Third-party libraries
from bs4 import BeautifulSoup

# Local application imports
from .utils import cached_get
from .google_images import get_first_google_image


WIKI_API = "https://gundam.fandom.com/api.php"


def parse_title_model_and_name(title):
    """
    Parse a Gundam Wiki page title into:
    - official model number
    - mobile suit name (AKA)

    Expected formats:
      "OZ-00MS2B Tallgeese III"
      "RX-78-2 Gundam"
      "MS-06S Zaku II"
    """

    # Remove any parenthetical disambiguation like "(Mobile Suit)"
    clean = re.sub(r"\s*\(.*?\)\s*", "", title).strip()

    # Split on first space: model number is always the first token
    parts = clean.split(" ", 1)

    if len(parts) == 1:
        # No model number found, fallback
        return None, clean

    model, name = parts[0], parts[1]
    return model, name


def extract_appearances_from_html(soup):
    """
    Scan the entire page HTML for appearance categories like:
    Television, OVA, Movie, Manga, Game, etc.
    Returns a dict: { "Television": [...], "OVA": [...], ... }
    """

    categories = {
        "Television": [],
        "OVA": [],
        "Movie": [],
        "Manga": [],
        "Novel": [],
        "Game": [],
        "Video Game": [],
    }

    # Look for section headers (h2, h3, etc.)
    for header in soup.find_all(["h2", "h3"]):
        title = header.get_text(" ", strip=True).lower()

        for cat in categories:
            if cat.lower() in title:
                # Find the next <ul> after the header
                ul = header.find_next("ul")
                if ul:
                    items = [li.get_text(" ", strip=True)
                             for li in ul.find_all("li")]
                    categories[cat] = items

    return categories


#  Cache wiki link resolutions to avoid redundant API calls for the same title
@lru_cache(maxsize=512)
def get_wiki_link(title):
    params = {
        "action": "query",
        "list": "search",
        "srsearch": title,
        "format": "json",
        "origin": "*"
    }

    resp = cached_get(WIKI_API, params=params).json()
    results = resp.get("query", {}).get("search", [])

    if not results:
        return None

    best = results[0]["title"]
    return f"https://gundam.fandom.com/wiki/{best.replace(' ', '_')}"


def link_appearances(appearances):
    links = {}

    for category, items in appearances.items():
        linked_items = []
        for item in items:
            linked_items.append({
                "title": item,
                "wiki_url": get_wiki_link(item)
            })
        links[category] = linked_items

    return links


def parse_infobox(title):
    """Extract model number, manufacturer, unit type, appearances, and gunpla kits."""
    params = {
        "action": "parse",
        "page": title,
        "prop": "text",
        "section": 0,
        "format": "json",
        "origin": "*"
    }

    try:
        resp = cached_get(WIKI_API, params=params)
        parsed = resp.json()

        html = parsed.get("parse", {}).get("text", {}).get("*", "")
        soup = BeautifulSoup(html, "html.parser")

        appearances_raw = extract_appearances_from_html(soup)

        # Enrich appearances with wiki links where possible
        appearances = link_appearances(appearances_raw)

        model_number = None
        manufacturer = None
        unit_type = None
        gunpla = []

        # Infobox parsing
        for row in soup.select(".pi-data"):
            label = row.find(class_="pi-data-label")
            value = row.find(class_="pi-data-value")

            if not label or not value:
                continue

            key = label.get_text(strip=True).lower()
            # normalize whitespace
            key = " ".join(key.split())

            val = value.get_text(" ", strip=True)
            val = " ".join(part for part in val.split()
                           if not part.startswith("["))

            if any(k in key for k in ["model", "designation", "official"]):
                if model_number is None:
                    model_number = val

            elif "manufacturer" in key:
                manufacturer = val

            elif any(k in key for k in [
                "unit type", "type", "classification", "role",
                "mobile suit type", "ms type"
            ]):
                unit_type = val

        # Gunpla section parsing
        gunpla_header = soup.find(id="Gunpla")
        if gunpla_header:
            ul = gunpla_header.find_next("ul")
            if ul:
                gunpla = [li.get_text(" ", strip=True)
                          for li in ul.find_all("li")]

        return model_number, manufacturer, unit_type, appearances, gunpla

    except Exception as e:
        print("Wiki parse error:", e)
        return None, None, None, {}, []


def process_page(page):
    title = page["title"]
    wiki_url = f"https://gundam.fandom.com/wiki/{title.replace(' ', '_')}"

    # Parse model + name from title
    official_model, aka_name = parse_title_model_and_name(title)

    # Infobox fields (optional fallback)
    model_number, manufacturer, unit_type, appearances, gunpla = parse_infobox(
        title)

    google_image = get_first_google_image(title + " gundam")

    return {
        "title": title,
        "unit_type": unit_type,
        "appearances": appearances,
        "gunpla": gunpla,
        "wiki_url": wiki_url,
        "google_image": google_image,
        "model_number": model_number or official_model,
        "official_model": official_model,
        "aka_name": aka_name,
        "manufacturer": manufacturer,
    }


def get_mobile_suit(name):
    """Search Gundam Wiki and return structured mobile suit data."""
    name = name.lower()

    params = {
        "action": "query",
        "list": "search",
        "srsearch": name,
        "format": "json",
        "origin": "*"
    }

    response = cached_get(WIKI_API, params=params)
    pages = response.json().get("query", {}).get("search", [])

    # Limit to top result
    pages = pages[:1]

    # Parallelize processing of each page
    with ThreadPoolExecutor(max_workers=3) as executor:
        results = list(executor.map(process_page, pages))

    return results
