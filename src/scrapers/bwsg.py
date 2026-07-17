import sys
import re
import html as html_lib
from typing import List
from src.models import Apartment
from src.scrapers.utils import fetch_html

def parse_price(val_str: str) -> float:
    # HTML tags strip
    val_str = re.sub(r'<[^>]+>', '', val_str)
    val_str = val_str.replace("€", "").replace("m²", "").strip()
    val_str = val_str.replace("\xa0", " ").replace("&nbsp;", " ")
    if "," in val_str:
        val_str = val_str.replace(".", "").replace(",", ".")
    try:
        num_m = re.search(r'[\d\.]+', val_str)
        if num_m:
            return float(num_m.group(0))
        return 0.0
    except ValueError:
        return 0.0

def scrape_bwsg() -> List[Apartment]:
    search_url = "https://www.bwsg.at/immobilien/immobilie-suchen/?_vermarktungsart=miete&_objektart=wohnung&_ort=wien"
    
    apartments: List[Apartment] = []
    
    print("Starting BWSG scraper...", file=sys.stderr)
    print(f"Fetching BWSG search page: {search_url}", file=sys.stderr)
    
    html_content = fetch_html(search_url)
    if not html_content:
        print("Failed to fetch BWSG search page.", file=sys.stderr)
        return []
        
    # all listing blocks
    blocks = re.findall(r'<div class=\"col-md-12\"\s+data-objektnummer=\"([^\"]+)\">(.*?)</a>\s*</div>', html_content, re.DOTALL)
    print(f"Found {len(blocks)} listing blocks on BWSG search page.", file=sys.stderr)
    
    for obj_num, block_html in blocks:
        try:
            # 1. Listing ID
            listing_id = obj_num.strip()
            
            # 2. URL
            link_m = re.search(r'href=\"([^\"]+)\"', block_html)
            url = link_m.group(1).strip() if link_m else ""
            if not url:
                continue
                
            # 3. Title
            title_m = re.search(r'<h2 class=\"res_immobiliensuche__immobilien__item__content__title\">([^<]+)</h2>', block_html)
            title = html_lib.unescape(title_m.group(1).strip()) if title_m else "BWSG Apartment"
            title = re.sub(r'\s+', ' ', title)
            
            # 4. Details text (contains size, rooms, and optional terrace/balcon)
            details_m = re.search(r'<span>([^<]+)</span>', block_html)
            details_text = details_m.group(1).strip() if details_m else ""
            
            # Parse size from details text
            size_m = re.search(r'([\d\.,]+)\s*m²', details_text)
            size = 0.0
            if size_m:
                size = parse_price(size_m.group(1))
                
            # rooms from details text
            rooms_m = re.search(r'(\d+)\s*Zimmer', details_text, re.I)
            rooms = 2
            if rooms_m:
                rooms = int(rooms_m.group(1))
                
            # 5. Price
            price_m = re.search(r'class=\"res_immobiliensuche__immobilien__item__content__meta__preis\">\s*([^<]+)', block_html)
            price = parse_price(price_m.group(1)) if price_m else 0.0
            
            # 6. Initial Location
            location_m = re.search(r'<i class=\"icon-location-narrow\"[^>]*></i>\s*(\d+)\s*<span[^>]*>([^<]+)</span>', block_html, re.DOTALL)
            zip_code = location_m.group(1).strip() if location_m else ""
            city = location_m.group(2).strip() if location_m else ""
            
            location = f"{zip_code} {city}".strip()
            if not location:
                location = "Wien"
                
            print(f"Fetching detail page for BWSG listing {listing_id}: {url}", file=sys.stderr)
            detail_html = fetch_html(url)
            if detail_html:
                address_m = re.search(r'<div class=\"res_address\">\s*<p>(.*?)</p>', detail_html, re.DOTALL)
                if address_m:
                    precise_address = html_lib.unescape(address_m.group(1).strip())
                    precise_address = re.sub(r'\s+', ' ', precise_address)
                    if precise_address:
                        location = precise_address
                        
            apartments.append(Apartment(
                source="BWSG",
                listing_id=listing_id,
                title=title,
                location=location,
                price=price,
                size_sqm=size,
                rooms=rooms,
                url=url,
                available_immediately=True,
                is_mock=False
            ))
            print(f"Successfully parsed BWSG listing: {title} ({location}) - {price}€", file=sys.stderr)
        except Exception as e:
            print(f"Error parsing BWSG listing block {obj_num}: {e}", file=sys.stderr)
            continue
            
    print(f"BWSG scraper complete. Total listings parsed: {len(apartments)}", file=sys.stderr)
    return apartments
