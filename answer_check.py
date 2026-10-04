import json

with open("output/disney_cruises_raw.json", "r", encoding="utf-8") as f:
    cruises = json.load(f)

print("\n--- CRUISES CONTAINING HOLIDAY ---")
for c in cruises:
    text = str(c).lower()
    if "holiday" in text:
        print(c)

print("\n--- CRUISES CONTAINING MIAMI ---")
for c in cruises:
    text = str(c).lower()
    if "miami" in text:
        print(c)

print("\n--- CRUISES CONTAINING LONDON ---")
for c in cruises:
    text = str(c).lower()
    if "london" in text:
        print(c)