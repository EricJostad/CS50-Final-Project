import fandom
import requests
from bs4 import BeautifulSoup

fandom.set_wiki("gundam")

# 1. Search for the page
result = fandom.search("wing zero", results=1)
title = result[0][0]
print("Title:", title)

# 2. Build the real wiki URL
url = f"https://gundam.fandom.com/wiki/{title.replace(' ', '_')}"
print("URL:", url)

# 3. Fetch the real HTML
html = requests.get(url).text
soup = BeautifulSoup(html, "html.parser")

# 4. Extract the infobox image
infobox = soup.find("aside", class_="portable-infobox")
figure = infobox.find("figure") if infobox else None
img = figure.find("img") if figure else None

if img:
    src = img.get("src")
    if src.startswith("//"):
        src = "https:" + src
    print("Image URL:", src)
else:
    print("No image found")
