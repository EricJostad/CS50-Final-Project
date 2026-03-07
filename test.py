import fandom

fandom.set_wiki("gundam")

result = fandom.search("tallgeese 3", results=1)

print(result)

page = fandom.page(title=result[0][0])

print(page)

image = page.images[0]

print(image)
