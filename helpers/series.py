# Standard library
from concurrent.futures import ThreadPoolExecutor

# Third-party libraries
from bs4 import BeautifulSoup

# Local application imports
from .utils import cached_get
from .google_images import get_first_google_image


WIKI_API = "https://gundam.fandom.com/api.php"


def parse_infobox(title):
    """Extract series information from wiki infobox."""
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

        aired = None
        episodes = None

        # Lighter selector: only .pi-data rows
        for row in soup.select(".pi-data"):
            label = row.find(class_="pi-data-label")
            value = row.find(class_="pi-data-value")

            if not label or not value:
                continue

            key = label.get_text(strip=True).lower()
            val = value.get_text(" ", strip=True)

            if "aired" in key:
                aired = val
            elif "episodes" in key:
                episodes = val

        return aired, episodes

    except Exception as e:
        print("Wiki parse error:", e)
        return None, None


def process_page(page):
    title = page["title"]
    wiki_url = f"https://gundam.fandom.com/wiki/{title.replace(' ', '_')}"

    aired, episodes = parse_infobox(title)
    google_image = get_first_google_image(title + " gundam anime")

    return {
        "title": title,
        "wiki_url": wiki_url,
        "google_image": google_image,
        "aired": aired,
        "episodes": episodes,
    }


def get_series(name):
    """Search Gundam Wiki and return structured series data."""
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
