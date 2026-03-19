# Standard library
from concurrent.futures import ThreadPoolExecutor

# Third-party libraries
from bs4 import BeautifulSoup

# Local application imports
from .utils import cached_get, fix_relative_links
from .google_images import get_first_google_image


WIKI_API = "https://gundam.fandom.com/api.php"


def parse_infobox(title):
    """Extract series information from wiki infobox."""
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

        episodes = None

        # Lighter selector: only .pi-data rows
        for row in soup.select(".pi-data"):
            label = row.find(class_="pi-data-label")
            value = row.find(class_="pi-data-value")

            if not label or not value:
                continue

            key = label.get_text(strip=True).lower()
            val = value.get_text(" ", strip=True)

            if "episodes" in key:
                episodes = val

        # Extract Synopsis section as well as update formating
        synopsis = fix_relative_links(extract_section_text(soup, "Synopsis"))

        return episodes, synopsis

    except Exception as e:
        print("Wiki parse error:", e)
        return None, None


def extract_section_text(soup, header_title):
    """
    Extracts the HTML content of a section starting from a header
    (h2/h3/etc.) until the next header of the same level.
    Preserves paragraph and list formatting.
    """
    header = None

    # Find the header that matches the requested title
    for h in soup.find_all(["h2", "h3"]):
        title = h.get_text(" ", strip=True).lower()
        if header_title.lower() in title:
            header = h
            break

    if not header:
        return None

    content = []
    for sibling in header.find_next_siblings():
        if sibling.name in ["h2", "h3"]:
            break

        # Preserve paragraphs and lists as HTML
        if sibling.name in ["p", "ul", "ol"]:
            content.append(str(sibling))
            continue

        # Handle wrapped content (div, figure, aside)
        if sibling.name in ["div", "figure", "aside"]:
            inner = sibling.find(["p", "ul", "ol"])
            if inner:
                content.append(str(inner))
            continue

        # Fallback: wrap plain text in <p>
        text = sibling.get_text(" ", strip=True)
        if text:
            content.append(f"<p>{text}</p>")

    return "\n".join(content).strip() or None


def process_page(page):
    title = page["title"]
    wiki_url = f"https://gundam.fandom.com/wiki/{title.replace(' ', '_')}"

    episodes, synopsis = parse_infobox(title)
    google_image = get_first_google_image(title + " gundam anime")

    return {
        "title": title,
        "wiki_url": wiki_url,
        "google_image": google_image,
        "episodes": episodes,
        "synopsis": synopsis,
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

    # Limit to top result
    pages = pages[:1]

    # Parallelize processing of each page
    with ThreadPoolExecutor(max_workers=3) as executor:
        results = list(executor.map(process_page, pages))

    return results
