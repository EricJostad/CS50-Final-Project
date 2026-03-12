# Standard library
from concurrent.futures import ThreadPoolExecutor

# Third-party libraries
from bs4 import BeautifulSoup

# Local application imports
from .utils import cached_get
from .google_images import get_first_google_image

WIKI_API = "https://gundam.fandom.com/api.php"


def parse_gunpla_kits(title):
    """Extract Gunpla kit list from a mobile suit wiki page."""
    params = {
        "action": "parse",
        "page": title,
        "prop": "text",
        "format": "json",
        "origin": "*"
    }

    try:
        resp = cached_get(WIKI_API, params=params)
        parsed = resp.json()

        html = parsed.get("parse", {}).get("text", {}).get("*", "")
        soup = BeautifulSoup(html, "html.parser")

        # Find the Gunpla section header
        header = None
        for h in soup.find_all(["h2", "h3"]):
            if "gunpla" in h.get_text(strip=True).lower():
                header = h
                break

        if not header:
            return []  # No kits listed

        kits = []

        # Walk through siblings until next header
        for sib in header.find_next_siblings():
            if sib.name in ["h2", "h3"]:
                break  # End of Gunpla section

            for li in sib.find_all("li"):
                text = li.get_text(" ", strip=True)
                if text:
                    kits.append(text)

        return kits

    except Exception as e:
        print("Gunpla parse error:", e)
        return []


def process_page(page):
    """Process a single wiki search result page and extract Gunpla kits."""
    title = page["title"]
    wiki_url = f"https://gundam.fandom.com/wiki/{title.replace(' ', '_')}"

    # Extract Gunpla kits
    kits = parse_gunpla_kits(title)

    # SerpAPI image (cached + fallback)
    google_image = get_first_google_image(title + " gunpla")

    return {
        "title": title,
        "wiki_url": wiki_url,
        "kits": kits,
        "google_image": google_image,
    }


def get_gunpla_kit(query):
    """
    Search for Gunpla kits by searching for mobile suits
    and extracting their Gunpla sections.
    """
    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "format": "json",
        "origin": "*"
    }

    try:
        resp = cached_get(WIKI_API, params=params)
        data = resp.json()
        pages = data.get("query", {}).get("search", [])

        # Limit to top 5 results for performance
        pages = pages[:5]

        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(process_page, pages))

        # Filter out suits with no kits
        results = [r for r in results if r["kits"]]

        return results

    except Exception as e:
        print("Wiki search error:", e)
        return []
