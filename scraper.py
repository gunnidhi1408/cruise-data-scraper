import json
import os
import re
import time

import pandas as pd
from playwright.sync_api import sync_playwright


URL = "https://disneycruise.disney.go.com/en-in/"
OUTPUT_DIR = "output"
RAW_JSON = os.path.join(OUTPUT_DIR, "disney_cruises_raw.json")
FINAL_CSV = os.path.join(OUTPUT_DIR, "disney_cruises.csv")


# ============================================================
# EXTRACT ALL CURRENTLY LOADED CRUISE CARDS
# ============================================================

def extract_all_cards(page):
    return page.evaluate("""
        () => {
            const cards = document.querySelectorAll(
                "div.product-card-primary-wrapper"
            );

            const getText = (card, selector) => {
                const element = card.querySelector(selector);

                if (!element) {
                    return "";
                }

                return element.textContent.trim();
            };

            const getAttribute = (card, selector, attribute) => {
                const element = card.querySelector(selector);

                if (!element) {
                    return "";
                }

                return element.getAttribute(attribute) || "";
            };

            return Array.from(cards).map(card => ({
                cruise_name: getText(
                    card,
                    ".product-card-content__name"
                ),

                destination: getText(
                    card,
                    ".product-card-content__sailing-to"
                ),

                price: getText(
                    card,
                    ".wrapper-price__pricing"
                ),

                currency: getText(
                    card,
                    ".wrapper-price__currency"
                ),

                guests: getText(
                    card,
                    ".total-guests-number__guests-label"
                ),

                special_offer: getText(
                    card,
                    ".chip-label"
                ),

                available_dates: getAttribute(
                    card,
                    ".product-card-footer-wrapper__btn span",
                    "aria-label"
                ),

                image: getAttribute(
                    card,
                    "img.hero-image",
                    "src"
                )
            }));
        }
    """)


# ============================================================
# CLEAN DATA
# ============================================================

def clean_text(value):
    """Normalize whitespace while preserving the actual text."""
    if value is None:
        return ""

    return re.sub(r"\s+", " ", str(value)).strip()


def clean_special_offer(value):
    """
    Clean the special-offer field while keeping
    the actual offer text shown on the cruise card.
    """

    value = clean_text(value)

    if not value:
        return "N/A"

    unwanted_text = [
        "for you as part of this special offer.",
        "for you as part of this special offer",
        "Disney Cruise Line will select your stateroom.",
        "Disney Cruise Line will select your stateroom",
        "Learn More"
    ]

    for text in unwanted_text:
        value = value.replace(text, "")

    value = clean_text(value)

    if not value:
        return "N/A"

    return value


def clean_data(records):
    cleaned_records = []

    for record in records:

        cruise_name = clean_text(
            record.get("cruise_name", "")
        )

        destination = clean_text(
            record.get("destination", "")
        )

        price = clean_text(
            record.get("price", "")
        )

        currency = clean_text(
            record.get("currency", "")
        )

        guests = clean_text(
            record.get("guests", "")
        )

        available_dates = clean_text(
            record.get("available_dates", "")
        )

        image = clean_text(
            record.get("image", "")
        )

        special_offer = clean_special_offer(
            record.get("special_offer", "")
        )

        # ----------------------------------------------------
        # Location
        # ----------------------------------------------------
        # Keep the raw website destination whenever available.
        # If the website destination field is empty,
        # extract the departure location from the cruise name.
        # Example:
        # "3-Night Cruise from Singapore" -> "Singapore"
        # ----------------------------------------------------

        location = destination

        if not location:
            match = re.search(
                r"\bfrom\s+(.+)$",
                cruise_name,
                flags=re.IGNORECASE
            )

            if match:
                location = clean_text(match.group(1))

        # Skip records without a cruise name.
        if not cruise_name:
            continue

        # Skip records where location cannot be determined.
        if not location:
            continue

        cleaned_records.append({
            "cruise_name": cruise_name,
            "location": location,
            "price": price,
            "currency": currency,
            "guests": guests,
            "special_offer": special_offer,
            "available_dates": available_dates,
            "image": image
        })

    # --------------------------------------------------------
    # Remove duplicate records
    # --------------------------------------------------------

    unique_records = []
    seen = set()

    for record in cleaned_records:

        key = (
            record["cruise_name"],
            record["location"],
            record["price"],
            record["currency"],
            record["guests"],
            record["available_dates"]
        )

        if key not in seen:
            seen.add(key)
            unique_records.append(record)

    return unique_records


# ============================================================
# MAIN SCRAPER
# ============================================================

def main():

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=False
        )

        page = browser.new_page(
            viewport={
                "width": 1440,
                "height": 900
            }
        )

        print("Opening Disney Cruise website...")

        page.goto(
            URL,
            wait_until="domcontentloaded",
            timeout=120000
        )

        page.wait_for_timeout(5000)

        # ----------------------------------------------------
        # Click View Dates
        # ----------------------------------------------------

        print("Looking for View Dates...")

        view_dates = page.get_by_text(
            "View Dates",
            exact=True
        )

        view_dates.first.click(
            timeout=30000
        )

        print("View Dates clicked.")

        page.wait_for_timeout(6000)

        # ----------------------------------------------------
        # Infinite Scroll
        # ----------------------------------------------------

        print("\n" + "=" * 40)
        print("STARTING CRUISE EXTRACTION")
        print("=" * 40)

        previous_count = 0
        stable_rounds = 0

        for scroll_number in range(1, 101):

            current_count = page.locator(
                "div.product-card-primary-wrapper"
            ).count()

            print(
                f"Scroll {scroll_number:02d} | "
                f"Cards loaded: {current_count}"
            )

            # Scroll to the bottom of the page.
            page.evaluate(
                "window.scrollTo(0, document.body.scrollHeight)"
            )

            # Allow lazy-loaded cards to appear.
            page.wait_for_timeout(3500)

            new_count = page.locator(
                "div.product-card-primary-wrapper"
            ).count()

            print(
                f"           After wait: {new_count} cards"
            )

            if new_count == previous_count:
                stable_rounds += 1
            else:
                stable_rounds = 0

            previous_count = new_count

            # Stop after several rounds with no new cards.
            if stable_rounds >= 5:
                print("\nNo additional cards loaded.")
                break

        # ----------------------------------------------------
        # Final Extraction
        # ----------------------------------------------------

        print("\n" + "=" * 40)
        print("FINAL EXTRACTION")
        print("=" * 40)

        raw_records = extract_all_cards(page)

        print(
            f"Raw records extracted: {len(raw_records)}"
        )

        # ----------------------------------------------------
        # STEP 5
        # Save temporary raw JSON
        # ----------------------------------------------------

        with open(
            RAW_JSON,
            "w",
            encoding="utf-8"
        ) as json_file:

            json.dump(
                raw_records,
                json_file,
                ensure_ascii=False,
                indent=4
            )

        print(
            f"Raw data saved to: {RAW_JSON}"
        )

        # ----------------------------------------------------
        # CLEANING DATA
        # ----------------------------------------------------

        print("\n" + "=" * 40)
        print("CLEANING DATA")
        print("=" * 40)

        cleaned_records = clean_data(
            raw_records
        )

        # ----------------------------------------------------
        # Convert to DataFrame
        # ----------------------------------------------------

        columns = [
            "cruise_name",
            "location",
            "price",
            "currency",
            "guests",
            "special_offer",
            "available_dates",
            "image"
        ]

        df = pd.DataFrame(
            cleaned_records,
            columns=columns
        )

        # Replace any remaining missing values.
        df = df.fillna("N/A")

        # Remove completely empty rows.
        df = df[
            df["cruise_name"].str.strip() != ""
        ]

        # ----------------------------------------------------
        # STEP 5 VALIDATION
        # ----------------------------------------------------

        print("\n" + "=" * 40)
        print("VALIDATION")
        print("=" * 40)

        empty_counts = (
            df.isna().sum()
            +
            (df == "").sum()
        )

        duplicate_count = df.duplicated().sum()

        empty_locations = (
            df["location"].isna()
            |
            (df["location"].str.strip() == "")
        ).sum()

        print("\nEmpty fields:")
        print(empty_counts)

        print(
            f"\nDuplicate rows: {duplicate_count}"
        )

        print(
            f"Empty locations: {empty_locations}"
        )

        print(
            f"\nFinal unique records: {len(df)}"
        )

        # ----------------------------------------------------
        # STEP 6
        # Save final cleaned CSV
        # ----------------------------------------------------

        df.to_csv(
            FINAL_CSV,
            index=False,
            encoding="utf-8-sig"
        )

        print("\n" + "=" * 40)
        print("SCRAPING COMPLETE")
        print("=" * 40)

        print(
            f"CSV saved to: {FINAL_CSV}"
        )

        print("\nColumns:")

        for column in df.columns:
            print(f"- {column}")

        # ----------------------------------------------------
        # Show first 5 records
        # ----------------------------------------------------

        print("\nFirst 5 records:")

        print(
            df.head(5).to_string(
                index=False
            )
        )

        print(
            "\nPress ENTER to close browser..."
        )

        input()

        browser.close()


# ============================================================
# RUN PROGRAM
# ============================================================

if __name__ == "__main__":
    main()