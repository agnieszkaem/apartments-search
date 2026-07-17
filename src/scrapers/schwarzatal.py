import sys
import re
import html as html_lib
from typing import List
from src.models import Apartment
from src.scrapers.utils import fetch_html

def parse_price(val_str: str) -> float:
    # currency symbols, space, and m² suffix if any
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
        # first occurrence of a number sequence
        num_m = re.search(r'[\d\.]+', val_str)
        if num_m:
            return float(num_m.group(0))
        return 0.0
    except ValueError:
        return 0.0

def scrape_schwarzatal() -> List[Apartment]:
    #  filtered URL provided by the user
    specific_url = "https://www.schwarzatal.at/immobiliensuche?tx_pfimmo_immolist%5B__referrer%5D%5B%40extension%5D=PfImmo&tx_pfimmo_immolist%5B__referrer%5D%5B%40controller%5D=Object&tx_pfimmo_immolist%5B__referrer%5D%5B%40action%5D=list&tx_pfimmo_immolist%5B__referrer%5D%5Barguments%5D=YToxOntzOjk6Im5ld0ZpbHRlciI7YTo2OntzOjQ6ImNpdHkiO3M6NDoiV2llbiI7czo5OiJkaXN0cmljdHMiO3M6MDoiIjtzOjU6InByaWNlIjtzOjM6IjgwMCI7czo0OiJzaXplIjtzOjA6IiI7czo1OiJzdGF0ZSI7czoxOiIxIjtzOjQ6InR5cGUiO3M6MzoiMXwxIjt9fQ%3D%3Dba613e784fb793a98a6ae7e4f1b976f6b73efc9a&tx_pfimmo_immolist%5B__referrer%5D%5B%40request%5D=%7B%22%40extension%22%3A%22PfImmo%22%2C%22%40controller%22%3A%22Object%22%2C%22%40action%22%3A%22list%22%7D9ed709514450a88e9770f25cf293d2dfb3724262&tx_pfimmo_immolist%5B__trustedProperties%5D=%7B%22newFilter%22%3A%7B%22price%22%3A1%2C%22size%22%3A1%2C%22state%22%3A1%2C%22districts%22%3A%5B1%2C1%2C1%2C1%2C1%2C1%2C1%2C1%2C1%2C1%2C1%2C1%2C1%2C1%5D%2C%22city%22%3A1%2C%22equipment%22%3A%5B1%2C1%2C1%2C1%2C1%2C1%2C1%2C1%2C1%2C1%2C1%2C1%5D%2C%22openareas%22%3A%5B1%5D%2C%22subject%22%3A1%7D%7Dc49c60a76967b78beb2050d70aee23c5bbf8737a&tx_pfimmo_immolist%5BnewFilter%5D%5Btype%5D=1%7C1&tx_pfimmo_immolist%5BnewFilter%5D%5Bprice%5D=800&tx_pfimmo_immolist%5BnewFilter%5D%5Bsize%5D=&tx_pfimmo_immolist%5BnewFilter%5D%5Bstate%5D=1&tx_pfimmo_immolist%5BnewFilter%5D%5Bdistricts%5D=&tx_pfimmo_immolist%5BnewFilter%5D%5Bcity%5D="
    
    # base URL fallback/supplement to make sure we parse available test items
    base_url = "https://www.schwarzatal.at/immobiliensuche"
    
    apartments: List[Apartment] = []
    seen_urls = set()
    
    print("Starting Schwarzatal scraper...", file=sys.stderr)
    
    # fetch both - comprehensive
    urls_to_try = [specific_url, base_url]
    
    for url in urls_to_try:
        is_base = (url == base_url)
        print(f"Fetching Schwarzatal URL ({'base' if is_base else 'filtered'})...", file=sys.stderr)
        html_content = fetch_html(url)
        
        if not html_content:
            print(f"Schwarzatal fetch returned empty for: {url}", file=sys.stderr)
            continue
            
        parts = html_content.split('class="immo-item"')
        if len(parts) <= 1:
            #  single quotes or general regex
            parts = re.split(r'class\s*=\s*["\']immo-item["\']', html_content)
            
        if len(parts) <= 1:
            print(f"No listings found on Schwarzatal page: {url}", file=sys.stderr)
            continue
            
        added_from_url = 0
        for part in parts[1:]:
            # link to detail page
            m_link = re.search(r'href\s*=\s*["\']([^"\']+)["\']', part)
            if not m_link:
                continue
            link = m_link.group(1).strip()
            
            m_head = re.search(r'<div class="headline">\s*(.*?)\s*</div>', part, re.DOTALL)
            headline = html_lib.unescape(m_head.group(1).strip()) if m_head else "Schwarzatal Apartment"
            headline = re.sub(r'\s+', ' ', headline)
            
            # Size
            m_size = re.search(r'<span class="size">\s*(.*?)\s*</span>', part, re.DOTALL)
            size_str = m_size.group(1).strip() if m_size else ""
            
            # Rooms
            m_rooms = re.search(r'<span class="rooms">\s*(.*?)\s*</span>', part, re.DOTALL)
            rooms_str = m_rooms.group(1).strip() if m_rooms else ""
            
            # Price
            m_price = re.search(r'<span class="price">\s*(.*?)\s*</span>', part, re.DOTALL)
            price_str = m_price.group(1).strip() if m_price else ""
            
            size = parse_price(size_str) if size_str else 0.0
            price = parse_price(price_str) if price_str else 0.0
            
            #  number of rooms
            rooms = 2
            if rooms_str:
                rooms_num_m = re.search(r'\d+', rooms_str)
                if rooms_num_m:
                    rooms = int(rooms_num_m.group(0))
            
            # stable link
            full_link = "https://www.schwarzatal.at" + link if link.startswith("/") else link
            if full_link in seen_urls:
                continue
                
            seen_urls.add(full_link)
            
            # listing ID e.g., `/immobiliensuche/details/2062-seefeld-kadolz-seefeld-8013` -> `2062-seefeld-kadolz-seefeld-8013`
            listing_id = link.split("/")[-1] if "/" in link else link
            if "?" in listing_id:
                listing_id = listing_id.split("?")[0]
                
            apartments.append(Apartment(
                source="Schwarzatal",
                listing_id=listing_id,
                title=headline,
                location=headline, 
                price=price,
                size_sqm=size,
                rooms=rooms,
                url=full_link,
                available_immediately=True,
                is_mock=False
            ))
            added_from_url += 1
            
        print(f"Added {added_from_url} listings from Schwarzatal URL ({'base' if is_base else 'filtered'}).", file=sys.stderr)
        
    print(f"Schwarzatal scraper complete. Total unique listings: {len(apartments)}", file=sys.stderr)
    return apartments
