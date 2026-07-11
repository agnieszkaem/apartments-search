import sys
import re
from typing import List
from concurrent.futures import ThreadPoolExecutor
from src.models import Apartment
from src.scrapers.utils import fetch_html

def scrape_oevw_page(page_num: int) -> List[Apartment]:
    url = f"https://www.oevw.at/suche?page={page_num}" if page_num > 1 else "https://www.oevw.at/suche"
    html = fetch_html(url)
    if not html:
        return []

    apartments: List[Apartment] = []
    # Split by thumblist__item
    parts = html.split('<li class="thumblist__item">')[1:]

    for idx, part in enumerate(parts):
        try:
            # Discard anything after the main list's closing tag for the last item to prevent leaking into footer
            if idx == len(parts) - 1:
                part = part.split('</ul>')[0]

            card_content = part

            # Title
            title_m = re.search(r'class=\"thumb__heading[^\"]*\"[^>]*>(.*?)</div>', card_content)
            title = title_m.group(1).strip() if title_m else ''
            if not title:
                continue

            # Location - extract and clean info
            loc_m = re.search(r'class=\"thumb__info small\"[^>]*>(.*?)</div>', card_content)
            location = 'Wien'
            if loc_m:
                info_text = loc_m.group(1).strip()
                loc_parts = [p.strip() for p in re.split(r'[–—\-]', info_text) if p.strip()]
                if loc_parts:
                    location = loc_parts[-1]

            # Size
            size_m = re.search(r'(\d+)\s*m²', card_content)
            size = float(size_m.group(1)) if size_m else 0.0

            # Price
            price_m = re.search(r'€\s*([\d\.,]+)', card_content)
            price = 0.0
            if price_m:
                price_str = price_m.group(1).replace('.', '').replace(',', '.')
                price = float(price_str)

            # Rooms
            rooms_m = re.search(r'(\d+)\s*Zimmer', card_content)
            rooms = int(rooms_m.group(1)) if rooms_m else 2

            # Link
            link_m = re.search(r'href=\"([^\"]+)\" class=\"stretched-link', card_content)
            if not link_m:
                link_m = re.search(r'href=\"([^\"]+)\"', card_content)
            link = 'https://www.oevw.at' + link_m.group(1) if link_m and link_m.group(1).startswith('/') else 'https://www.oevw.at/suche'

            # Listing ID
            listing_id = f'oevw-p{page_num}-{idx+1}'
            id_m = re.search(r'/suche/(\d+)', link)
            if id_m:
                listing_id = id_m.group(1)

            if price <= 0:
                print(f"Skipping OeVW listing {listing_id} due to invalid or unparsed price.", file=sys.stderr)
                continue
            if size <= 0:
                print(f"Skipping OeVW listing {listing_id} due to invalid or unparsed size.", file=sys.stderr)
                continue

            apartments.append(Apartment(
                source="OeVW",
                listing_id=listing_id,
                title=title,
                location=location,
                price=price,
                size_sqm=size,
                rooms=rooms,
                url=link,
                available_immediately=True
            ))
        except Exception as e:
            print(f"Error parsing OeVW card: {e}", file=sys.stderr)
            continue
            
    return apartments

def scrape_oevw() -> List[Apartment]:
    try:
        pages = [1, 2, 3, 4, 5]
        all_apartments: List[Apartment] = []
        seen_ids = set()

        with ThreadPoolExecutor(max_workers=5) as executor:
            results = executor.map(scrape_oevw_page, pages)
            for res in results:
                for ap in res:
                    if ap.listing_id not in seen_ids:
                        seen_ids.add(ap.listing_id)
                        all_apartments.append(ap)

        if all_apartments:
            print(f"Successfully scraped {len(all_apartments)} real OeVW listings across pages.", file=sys.stderr)
            return all_apartments
        else:
            print("No apartments parsed from OeVW HTML.", file=sys.stderr)
            return []

    except Exception as e:
        print(f"OeVW parsing failed: {e}", file=sys.stderr)
        return []

