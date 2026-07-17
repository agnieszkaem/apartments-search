import sys
import re
import html as html_lib
from typing import List
from src.models import Apartment
from src.scrapers.utils import fetch_html

def parse_price(val_str: str) -> float:
    # HTML tags
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

def scrape_lebenswert_wohnen() -> List[Apartment]:
    specific_url = "https://www.lebenswert-wohnen.at/suche?f%5Ball%5D%5Bmarketing_type%5D=rent&f%5Ball%5D%5Bprice%5D%5Bmax%5D=800&f%5Ball%5D%5Brooms%5D%5Bmin%5D=2&f%5Ball%5D%5Bfederal_state%5D=134&from=623243"
    
    apartments: List[Apartment] = []
    seen_urls = set()
    
    print("Starting Lebenswert Wohnen scraper with pagination...", file=sys.stderr)
    
    print("Fetching Lebenswert Wohnen URL (filtered)...", file=sys.stderr)
    html_content = fetch_html(specific_url)
    if html_content:
        parts = html_content.split('class="realty-wrapper')
        if len(parts) <= 1:
            parts = re.split(r'class\s*=\s*["\']realty-wrapper', html_content)
        
        if len(parts) > 1:
            added = 0
            for part in parts[1:]:
                m_link = re.search(r'href\s*=\s*["\']/objekt/([^"\'\s>]+)["\']', part)
                if not m_link:
                    continue
                relative_url = "/objekt/" + m_link.group(1).strip()
                listing_id = m_link.group(1).split("?")[0]
                full_link = "https://www.lebenswert-wohnen.at" + relative_url
                if full_link in seen_urls:
                    continue
                seen_urls.add(full_link)
                
                m_title = re.search(r'<h3[^>]*>.*?<a[^>]*>(.*?)</a>.*?</h3>', part, re.DOTALL)
                title = html_lib.unescape(m_title.group(1).strip()) if m_title else "Lebenswert Wohnen Apartment"
                title = re.sub(r'\s+', ' ', title)
                
                m_zip = re.search(r'<span class="zip-city">(.*?)</span>', part, re.DOTALL)
                address = html_lib.unescape(m_zip.group(1).strip()) if m_zip else ""
                address = re.sub(r'\s+', ' ', address)
                
                m_rooms = re.search(r'info-rooms.*?class="list-item-value">(.*?)</span>', part, re.DOTALL)
                rooms_str = m_rooms.group(1).strip() if m_rooms else ""
                rooms = 2
                if rooms_str:
                    rooms_num_m = re.search(r'\d+', rooms_str)
                    if rooms_num_m:
                        rooms = int(rooms_num_m.group(0))
                        
                m_size = re.search(r'info-surface.*?class="list-item-value">(.*?)</span>', part, re.DOTALL)
                size_str = m_size.group(1).strip() if m_size else ""
                size = parse_price(size_str)
                
                m_price = re.search(r'info-price.*?class="list-item-value">(.*?)</span>', part, re.DOTALL)
                price_str = m_price.group(1).strip() if m_price else ""
                price = parse_price(price_str)
                
                apartments.append(Apartment(
                    source="Lebenswert Wohnen",
                    listing_id=listing_id,
                    title=title,
                    location=address if address else title,
                    price=price,
                    size_sqm=size,
                    rooms=rooms,
                    url=full_link,
                    available_immediately=True,
                    is_mock=False
                ))
                added += 1
            print(f"Added {added} listings from filtered search.", file=sys.stderr)

    # paginate base search results
    for page in range(1, 11):
        page_url = "https://www.lebenswert-wohnen.at/suche" if page == 1 else f"https://www.lebenswert-wohnen.at/suche/p/{page}"
        print(f"Fetching Lebenswert Wohnen page {page}...", file=sys.stderr)
        html_content = fetch_html(page_url)
        if not html_content:
            print(f"Failed to fetch page {page}, stopping pagination.", file=sys.stderr)
            break
            
        parts = html_content.split('class="realty-wrapper')
        if len(parts) <= 1:
            parts = re.split(r'class\s*=\s*["\']realty-wrapper', html_content)
            
        if len(parts) <= 1:
            print(f"No listings found on page {page}, stopping pagination.", file=sys.stderr)
            break
            
        added_from_page = 0
        for part in parts[1:]:
            m_link = re.search(r'href\s*=\s*["\']/objekt/([^"\'\s>]+)["\']', part)
            if not m_link:
                continue
                
            relative_url = "/objekt/" + m_link.group(1).strip()
            listing_id = m_link.group(1).split("?")[0]
            full_link = "https://www.lebenswert-wohnen.at" + relative_url
            
            if full_link in seen_urls:
                continue
            seen_urls.add(full_link)
            
            # Title
            m_title = re.search(r'<h3[^>]*>.*?<a[^>]*>(.*?)</a>.*?</h3>', part, re.DOTALL)
            title = html_lib.unescape(m_title.group(1).strip()) if m_title else "Lebenswert Wohnen Apartment"
            title = re.sub(r'\s+', ' ', title)
            
            # Address/Location
            m_zip = re.search(r'<span class="zip-city">(.*?)</span>', part, re.DOTALL)
            address = html_lib.unescape(m_zip.group(1).strip()) if m_zip else ""
            address = re.sub(r'\s+', ' ', address)
            
            # Rooms
            m_rooms = re.search(r'info-rooms.*?class="list-item-value">(.*?)</span>', part, re.DOTALL)
            rooms_str = m_rooms.group(1).strip() if m_rooms else ""
            rooms = 2
            if rooms_str:
                rooms_num_m = re.search(r'\d+', rooms_str)
                if rooms_num_m:
                    rooms = int(rooms_num_m.group(0))
                    
            # Size
            m_size = re.search(r'info-surface.*?class="list-item-value">(.*?)</span>', part, re.DOTALL)
            size_str = m_size.group(1).strip() if m_size else ""
            size = parse_price(size_str)
            
            # Price
            m_price = re.search(r'info-price.*?class="list-item-value">(.*?)</span>', part, re.DOTALL)
            price_str = m_price.group(1).strip() if m_price else ""
            price = parse_price(price_str)
            
            apartments.append(Apartment(
                source="Lebenswert Wohnen",
                listing_id=listing_id,
                title=title,
                location=address if address else title,
                price=price,
                size_sqm=size,
                rooms=rooms,
                url=full_link,
                available_immediately=True,
                is_mock=False
            ))
            added_from_page += 1
            
        print(f"Added {added_from_page} listings from page {page}.", file=sys.stderr)
        if added_from_page == 0:
            print(f"All listings on page {page} were duplicates or invalid, stopping pagination.", file=sys.stderr)
            break
        
    print(f"Lebenswert Wohnen scraper complete. Total unique listings: {len(apartments)}", file=sys.stderr)
    return apartments
