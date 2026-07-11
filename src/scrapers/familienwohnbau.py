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

def scrape_familienwohnbau() -> List[Apartment]:
    url = "https://familienwohnbau.at/de/immobilien"
    
    html = fetch_html(url)
    if not html:
        print("Familien Wohnbau fetch returned empty.", file=sys.stderr)
        return []

    try:
        apartments: List[Apartment] = []

        # Find all <a> cards pointing to /de/objekt/
        cards = re.findall(r'<a\s+href="(/de/objekt/[^\"]+)"\s+class="[^"]*bg-white[^"]*">(.*?)</a>', html, re.DOTALL)
        
        for idx, (relative_link, block) in enumerate(cards):
            try:
                url_lower = relative_link.lower()
                block_lower = block.lower()

                # Filter out garage spaces, office space, commercial space, parking spaces
                if any(kw in url_lower for kw in ['garage', 'stellplatz', 'abstellplatz', 'gewerbe', 'buero', 'hobby', 'studenten']):
                    continue
                
                # Must be a rental property ("miete")
                is_miete = 'miete' in url_lower or 'miete' in block_lower
                if not is_miete:
                    continue

                # Clean up relative link to full link
                full_link = "https://familienwohnbau.at" + relative_link

                # Listing ID is the last part of the URL path
                listing_id = relative_link.split("/")[-1]
                if not listing_id:
                    listing_id = f"fwb-{idx+1}"

                # 1. Title / Header
                title_m = re.search(r'class="uppercase tracking-wide text-sm font-bold text-gray-700">\s*(.*?)\s*</p>', block, re.DOTALL)
                title = title_m.group(1).strip() if title_m else f"Familien Wohnbau Apartment {idx+1}"
                title = re.sub(r'<[^>]+>', '', title)
                title = re.sub(r'\s+', ' ', title)

                # 2. Address & Location
                addr_m = re.search(r'class="text-gray-700 pt-1">\s*(.*?)\s*</p>', block, re.DOTALL)
                addr = addr_m.group(1).strip() if addr_m else ""
                addr = re.sub(r'<[^>]+>', '', addr)
                addr = re.sub(r'\s+', ' ', addr)

                # Extract location (Wien, Lanzendorf, etc.)
                full_address = addr if addr else title
                if "," in full_address:
                    location = full_address.split(",")[0].strip()
                else:
                    # Look for 4 digit Austrian zip code + city name
                    zip_city_m = re.search(r'(\d{4}\s+[a-zA-ZäöüÄÖÜß]+)', full_address)
                    if zip_city_m:
                        location = zip_city_m.group(1).strip()
                    else:
                        location = "Wien"

                # Restrict strictly to Vienna (Wien)
                is_vienna = False
                postcodes = re.findall(r'\b(\d{4})\b', full_address + " " + relative_link)
                if postcodes:
                    if any(pc.startswith('1') for pc in postcodes):
                        is_vienna = True
                else:
                    if 'wien' in full_address.lower() or 'wien' in location.lower() or 'wien' in title.lower():
                        is_vienna = True

                if not is_vienna:
                    continue

                # 3. Price
                price_m = re.search(r'class="text-2xl text-primary italic font-semibold pt-3">\s*(.*?)\s*</p>', block, re.DOTALL)
                price_str = price_m.group(1).strip() if price_m else ""
                price_str = re.sub(r'\s+', ' ', price_str)

                price = 0.0
                val_m = re.search(r'€\s*([\d\.,]+)', price_str)
                if val_m:
                    price = parse_price(val_m.group(1))

                # Skip if no valid price is specified (or price is unreasonably high)
                if price <= 0.0 or price > 10000:
                    continue

                # 4. Rooms
                rooms = 2  # Default fallback
                rooms_m = re.search(r'class="text-gray-900">\s*(\d+)\s*</span>\s*Zimmer', block, re.IGNORECASE)
                if rooms_m:
                    rooms = int(rooms_m.group(1))
                else:
                    rooms_m2 = re.search(r'(\d+)\s*Zimmer', block, re.IGNORECASE)
                    if rooms_m2:
                        rooms = int(rooms_m2.group(1))

                # 5. Size (sqm)
                size = 55.0  # Default fallback
                size_m = re.search(r'class="text-gray-900">\s*([\d\.,]+)\s*</span>\s*m²', block, re.IGNORECASE)
                if size_m:
                    size = parse_price(size_m.group(1))
                else:
                    size_m2 = re.search(r'([\d\.,]+)\s*m²', block, re.IGNORECASE)
                    if size_m2:
                        size = parse_price(size_m2.group(1))

                if price <= 0:
                    print(f"Skipping Familien Wohnbau listing {listing_id} due to invalid or unparsed price.", file=sys.stderr)
                    continue
                if size <= 0:
                    print(f"Skipping Familien Wohnbau listing {listing_id} due to invalid or unparsed size.", file=sys.stderr)
                    continue

                apartments.append(Apartment(
                    source="Familien Wohnbau",
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
                print(f"Error parsing Familien Wohnbau listing card: {e}", file=sys.stderr)
                continue

        if apartments:
            print(f"Successfully scraped {len(apartments)} real Familien Wohnbau listings.", file=sys.stderr)
            return apartments
        else:
            print("No apartments parsed from Familien Wohnbau HTML.", file=sys.stderr)
            return []

    except Exception as e:
        print(f"Familien Wohnbau parsing failed: {e}", file=sys.stderr)
        return []
