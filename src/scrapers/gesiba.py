import sys
import re
from typing import List
from src.models import Apartment
from src.scrapers.utils import fetch_html

def scrape_gesiba() -> List[Apartment]:
    url = "https://www.gesiba.at/immobilien/wohnungen?filter%5Bverfuegbar%5D=sofort"
    
    html = fetch_html(url)
    if not html:
        print("GESIBA fetch returned empty.", file=sys.stderr)
        return []

    try:
        apartments: List[Apartment] = []

        # Extract all col-xl-4 cards
        cards = re.findall(r'<a href=\"(/immobilien/wohnungen/objekt\?objektnummer=[^\"]+)\" class=\"card\">(.*?)</a>', html, re.DOTALL)
        if not cards:
            print("No GESIBA cards matched with primary regex. Trying secondary patterns.", file=sys.stderr)
            # Fallback regex in case of minor layout variations
            cards = re.findall(r'href=\"(/immobilien/wohnungen/objekt[^\"]+)\".*?class=\"card-body\">(.*?)</div>\s*</a>', html, re.DOTALL)

        for idx, (link, content) in enumerate(cards):
            try:
                # Title
                title_m = re.search(r'<h3 class=\"card-title\">(.*?)</h3>', content)
                title = title_m.group(1).strip() if title_m else f"GESIBA Apartment {idx+1}"

                # Location
                loc_m = re.search(r'<p>(.*?)</p>', content)
                location = loc_m.group(1).strip() if loc_m else "Wien"

                # Size
                size_m = re.search(r'([\d,]+)\s*m²', content)
                size = float(size_m.group(1).replace(",", ".")) if size_m else 0.0

                # Rooms
                rooms_m = re.search(r'(\d+)\s*Zimmer', content)
                rooms = int(rooms_m.group(1)) if rooms_m else 2

                # Price
                price_m = re.search(r'ab €\s*([\d\.,]+)', content)
                price = 0.0
                if price_m:
                    price_str = price_m.group(1).replace(".", "").replace(",", ".")
                    price = float(price_str)
                else:
                    # Try raw number pattern
                    price_fallback = re.search(r'€\s*([\d\.,]+)', content)
                    if price_fallback:
                        price_str = price_fallback.group(1).replace(".", "").replace(",", ".")
                        price = float(price_str)

                # Full link
                full_link = "https://www.gesiba.at" + link

                objekt_nr_m = re.search(r'objektnummer=(\d+)', link)
                listing_id = objekt_nr_m.group(1) if objekt_nr_m else f"g-{idx+1}"

                if price <= 0:
                    print(f"Skipping GESIBA listing {listing_id} due to invalid or unparsed price.", file=sys.stderr)
                    continue
                if size <= 0:
                    print(f"Skipping GESIBA listing {listing_id} due to invalid or unparsed size.", file=sys.stderr)
                    continue

                apartments.append(Apartment(
                    source="GESIBA",
                    listing_id=listing_id,
                    title=title,
                    location=location,
                    price=price,
                    size_sqm=size,
                    rooms=rooms,
                    url=full_link,
                    available_immediately=True
                ))
            except Exception as e:
                print(f"Error parsing GESIBA listing element: {e}", file=sys.stderr)
                continue

        if apartments:
            print(f"Successfully scraped {len(apartments)} real GESIBA listings.", file=sys.stderr)
            return apartments
        else:
            print("No apartments parsed from GESIBA HTML.", file=sys.stderr)
            return []

    except Exception as e:
        print(f"GESIBA parsing failed: {e}", file=sys.stderr)
        return []

