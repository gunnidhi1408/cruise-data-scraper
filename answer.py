import json
import re

JSON_FILE = "output/disney_cruises_raw.json"

# Load original scraper data
with open(JSON_FILE, "r", encoding="utf-8") as f:
    cruises = json.load(f)

# ---------------------------------------------------------
# (i) How many total cruises are there for the Pacific?
# ---------------------------------------------------------
pacific_count = 0

for cruise in cruises:
    destination = cruise.get("destination", "").lower()
    cruise_name = cruise.get("cruise_name", "").lower()

    if "pacific" in destination or "pacific" in cruise_name:
        pacific_count += 1


# ---------------------------------------------------------
# (ii) How many total cruises are there?
# ---------------------------------------------------------
total_cruises = len(cruises)


# ---------------------------------------------------------
# (iii) How many holiday cruises are there?
# ---------------------------------------------------------
holiday_count = 0

for cruise in cruises:
    cruise_name = cruise.get("cruise_name", "").lower()
    destination = cruise.get("destination", "").lower()
    special_offer = cruise.get("special_offer", "").lower()

    if (
        "holiday" in cruise_name
        or "holiday" in destination
        or "holiday" in special_offer
    ):
        holiday_count += 1


# ---------------------------------------------------------
# (iv) How many cruises offer more than 2 dates?
# ---------------------------------------------------------
more_than_2_dates = 0

for cruise in cruises:
    available_dates = cruise.get("available_dates", "")

    # Example:
    # "Show 64 Dates"
    # "Show 12 Dates"
    match = re.search(r"(\d+)\s+Dates?", available_dates, re.IGNORECASE)

    if match:
        date_count = int(match.group(1))

        if date_count > 2:
            more_than_2_dates += 1


# ---------------------------------------------------------
# (v) Miami and London departure ports
# ---------------------------------------------------------
miami_count = 0
london_count = 0

for cruise in cruises:
    cruise_name = cruise.get("cruise_name", "").lower()

    if "from miami" in cruise_name:
        miami_count += 1

    if "from london" in cruise_name:
        london_count += 1


# ---------------------------------------------------------
# PRINT ANSWERS
# ---------------------------------------------------------
print("\n" + "=" * 60)
print("DISNEY CRUISE ASSIGNMENT ANSWERS")
print("=" * 60)

print(f"(i)   Pacific destination cruises    : {pacific_count}")
print(f"(ii)  Total cruises                  : {total_cruises}")
print(f"(iii) Holiday cruises                : {holiday_count}")
print(f"(iv)  Cruises with >2 booking dates  : {more_than_2_dates}")
print(f"(v)   Miami departure cruises        : {miami_count}")
print(f"      London departure cruises       : {london_count}")

print("=" * 60)