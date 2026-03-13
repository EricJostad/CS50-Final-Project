# Standard library
import re
from concurrent.futures import ThreadPoolExecutor

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


def parse_infobox(title):
    """Extract model number, aka title, and manufacturer from wiki infobox."""
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

        model_number = None
        manufacturer = None

        for row in soup.select(".pi-data"):
            label = row.find(class_="pi-data-label")
            value = row.find(class_="pi-data-value")

            if not label or not value:
                continue

            key = label.get_text(strip=True).lower()
            val = value.get_text(" ", strip=True)

            # Remove reference markers like [1]
            val = " ".join(part for part in val.split()
                           if not part.startswith("["))

            # Match model number variants
            if any(k in key for k in ["model", "designation", "official"]):
                if model_number is None:
                    model_number = val

            elif "manufacturer" in key:
                manufacturer = val

        return model_number, manufacturer

    except Exception as e:
        print("Wiki parse error:", e)
        return None, None


def process_page(page):
    title = page["title"]
    wiki_url = f"https://gundam.fandom.com/wiki/{title.replace(' ', '_')}"

    # Parse model + name from title
    official_model, aka_name = parse_title_model_and_name(title)

    # Infobox fields (optional fallback)
    model_number, manufacturer = parse_infobox(title)

    google_image = get_first_google_image(title + " gundam")

    return {
        "title": title,
        "wiki_url": wiki_url,
        "google_image": google_image,
        # fallback to title if model number not found in infobox
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

    # Limit to top 3
    pages = pages[:3]

    # Parallelize processing of each page
    with ThreadPoolExecutor(max_workers=3) as executor:
        results = list(executor.map(process_page, pages))

    return results
