import sys
import re
from typing import List
from src.models import Apartment
from src.scrapers.utils import fetch_html

def parse_price(val_str: str) -> float:
    val_str = val_str.strip()
    if "," in val_str:
        # Standard Austrian formatting: e.g. "1.234,50" -> "1234.50"
        val_str = val_str.replace(".", "").replace(",", ".")
    else:
        # e.g. "452.02" or "1200"
        # If it has a dot and the part after the dot has exactly 3 digits, it's likely a thousands separator (e.g. "1.200")
        if "." in val_str:
            parts = val_str.split(".")
            if len(parts[-1]) == 3:
                val_str = "".join(parts)
    try:
        return float(val_str)
    except ValueError:
        return 0.0

def scrape_siedlungsunion() -> List[Apartment]:
    url = "https://www.siedlungsunion.at/wohnen/sofort"
    
    html = fetch_html(url)
    if not html:
        print("Siedlungs Union fetch returned empty.", file=sys.stderr)
        return []

    try:
        apartments: List[Apartment] = []

        # Find all article containers
        articles = re.findall(r'<article\s+class="[^"]*uk-article[^"]*">(.*?)</article>', html, re.DOTALL)
        
        for idx, art in enumerate(articles):
            try:
                # 1. Link / Suffix
                link_m = re.search(r'href="(/wohnen/sofort/[^\"]+)"', art)
                if not link_m:
                    continue
                relative_link = link_m.group(1)
                full_link = "https://www.siedlungsunion.at" + relative_link
                
                # Listing ID is the last part of the URL path
                listing_id = relative_link.split("/")[-1]
                if not listing_id:
                    listing_id = f"su-{idx+1}"

                # 2. Address / Title
                title_m = re.search(r'<a href="/wohnen/sofort/[^\"]+">\s*(.*?)\s*</a>', art, re.DOTALL)
                address = title_m.group(1).strip() if title_m else f"Siedlungs Union Apartment {idx+1}"
                
                # Clean up nested tags or HTML entities in the title if any
                address = re.sub(r'<[^>]+>', '', address).strip()
                address = address.replace("&nbsp;", " ")

                # Extract location and title from address
                if "," in address:
                    parts = address.split(",", 1)
                    location = parts[0].strip()
                    title = parts[1].strip()
                else:
                    location = "Wien"
                    title = address

                # 3. Rooms
                rooms_m = re.search(r'(\d+)\s*Zimmer', art)
                rooms = int(rooms_m.group(1)) if rooms_m else 2

                # 4. Size (sqm)
                size_m = re.search(r'([\d\.,]+)\s*m<sup>2</sup>', art)
                if not size_m:
                    # Fallback in case of raw m² or other formats
                    size_m = re.search(r'([\d\.,]+)\s*(?:m²|qm)', art)
                
                size = 0.0
                if size_m:
                    size_str = size_m.group(1).replace(",", ".")
                    size = float(size_str)

                # 5. Price (Euro)
                # Matches digit string containing dots or commas before the euro icon
                price_m = re.search(r'([\d\.,\s]+)<i\s+class="[^"]*uk-icon-euro[^"]*">', art)
                if not price_m:
                    price_m = re.search(r'([\d\.,\s]+)€', art)
                
                price = 0.0
                if price_m:
                    price = parse_price(price_m.group(1))

                if price <= 0:
                    print(f"Skipping Siedlungs Union listing {listing_id} due to invalid or unparsed price.", file=sys.stderr)
                    continue
                if size <= 0:
                    print(f"Skipping Siedlungs Union listing {listing_id} due to invalid or unparsed size.", file=sys.stderr)
                    continue

                apartments.append(Apartment(
                    source="Siedlungs Union",
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
                print(f"Error parsing Siedlungs Union listing element: {e}", file=sys.stderr)
                continue

        if apartments:
            print(f"Successfully scraped {len(apartments)} real Siedlungs Union listings.", file=sys.stderr)
            return apartments
        else:
            print("No apartments parsed from Siedlungs Union HTML.", file=sys.stderr)
            return []

    except Exception as e:
        print(f"Siedlungs Union parsing failed: {e}", file=sys.stderr)
        return []
