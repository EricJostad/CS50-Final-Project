# Standard library
import os
from functools import lru_cache

# Third-party libraries
from serpapi import GoogleSearch

# Load environment variables
from dotenv import load_dotenv
load_dotenv()


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

    return None
