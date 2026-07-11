import sys
import re
import html as html_lib
from typing import List
from src.models import Apartment
from src.scrapers.utils import fetch_html

def parse_price(val_str: str) -> float:
    # Remove currency symbols, space, and m² suffix if any
    val_str = val_str.replace("€", "").replace("m²", "").strip()
    if "," in val_str:
        # e.g. "1.234,50" -> "1234.50"
        val_str = val_str.replace(".", "").replace(",", ".")
    else:
        if "." in val_str:
            parts = val_str.split(".")
            if len(parts[-1]) == 3:
                val_str = "".join(parts)
    try:
        return float(val_str)
    except ValueError:
        return 0.0

def scrape_egw() -> List[Apartment]:
    page = 1
    apartments: List[Apartment] = []
    seen_urls = set()
    
    print("Starting EGW scraper...", file=sys.stderr)
    
    while True:
        url = f"https://www.egw.at/suche?page={page}" if page > 1 else "https://www.egw.at/suche"
        print(f"Fetching EGW page {page}...", file=sys.stderr)
        html_content = fetch_html(url)
        if not html_content:
            print(f"EGW page {page} fetch returned empty.", file=sys.stderr)
            break
            
        items = re.findall(r'<li class="thumblist__item">(.*?)</li>', html_content, re.DOTALL)
        if not items:
            print(f"No listings found on EGW page {page}. Stopping pagination.", file=sys.stderr)
            break
            
        page_new_count = 0
        for item in items:
            m_link = re.search(r'<h2[^>]*class="[^"]*thumb__heading[^"]*"[^>]*>\s*<a href="([^"]+)"[^>]*>(.*?)</a>', item, re.DOTALL)
            if not m_link:
                continue
            link = m_link.group(1).strip()
            title = html_lib.unescape(m_link.group(2).strip()).replace('\xa0', ' ')
            
            # Extract address
            m_sub = re.search(r'<div class="thumb__subheading">(.*?)</div>', item, re.DOTALL)
            address = html_lib.unescape(m_sub.group(1).strip()) if m_sub else "Wien"
            
            # Extract size, rooms, price
            m_size = re.search(r'Nutzfläche:\s*<strong>(.*?)</strong>', item, re.IGNORECASE)
            m_rooms = re.search(r'Zimmer:\s*<strong>(.*?)</strong>', item, re.IGNORECASE)
            m_price = re.search(r'Miete brutto:\s*<strong>(.*?)</strong>', item, re.IGNORECASE)
            
            size_str = m_size.group(1).strip() if m_size else ""
            rooms_str = m_rooms.group(1).strip() if m_rooms else ""
            price_str = m_price.group(1).strip() if m_price else ""
            
            # Skip if basic fields are missing
            if not size_str or not price_str:
                continue
                
            size = parse_price(size_str)
            price = parse_price(price_str)
            rooms = int(rooms_str) if rooms_str.isdigit() else 2
            
            # Skip invalid listings
            if price <= 0:
                print(f"Skipping EGW listing {link} due to invalid or unparsed price.", file=sys.stderr)
                continue
            if size <= 0:
                print(f"Skipping EGW listing {link} due to invalid or unparsed size.", file=sys.stderr)
                continue
                
            full_link = "https://www.egw.at" + link if link.startswith("/") else link
            if full_link in seen_urls:
                continue
                
            seen_urls.add(full_link)
            
            # Extract listing ID
            listing_id_m = re.search(r'/suche/(\d+)', link)
            listing_id = listing_id_m.group(1) if listing_id_m else link.split("/")[-1]
            
            apartments.append(Apartment(
                source="EGW",
                listing_id=listing_id,
                title=title,
                location=address,
                price=price,
                size_sqm=size,
                rooms=rooms,
                url=full_link,
                available_immediately=True,
                is_mock=False
            ))
            page_new_count += 1
            
        print(f"Page {page} parsed, added {page_new_count} listings.", file=sys.stderr)
        if page_new_count == 0:
            print("No new unique listings found on this page. Stopping pagination.", file=sys.stderr)
            break
        page += 1
        
    print(f"EGW scraper complete. Scraped {len(apartments)} total listings.", file=sys.stderr)
    return apartments
