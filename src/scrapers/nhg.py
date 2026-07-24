import sys
import re
import html as html_lib
import ssl
from typing import List
from src.models import Apartment
from src.scrapers.utils import fetch_html

def parse_price(val_str: str) -> float:
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

def scrape_nhg() -> List[Apartment]:
    from src.config import Config
    
    apartments: List[Apartment] = []
    
    print("Starting NHG scraper...", file=sys.stderr)
    
    try:
        config = Config()
        location_contains = config.location_contains
    except Exception as ce:
        print(f"Could not load config in NHG scraper: {ce}", file=sys.stderr)
        location_contains = "Wien"

    if not location_contains:
        location_contains = "Wien"

    main_url = "https://www.nhg.at/angebot/"
    print(f"Fetching NHG search/map page: {main_url}", file=sys.stderr)
    
    html_content = fetch_html(main_url)
    if not html_content:
        print("Failed to fetch NHG main page.", file=sys.stderr)
        return []
        
    blocks = re.findall(r'(<div[^>]*class=["\']map__group["\'][^>]*>.*?</div>\s*</div>)', html_content, re.DOTALL)
    print(f"Found {len(blocks)} project blocks on NHG main page.", file=sys.stderr)
    
    loc_terms = [t.strip().lower() for t in re.split(r'[,|;]', location_contains) if t.strip()]
    if not loc_terms:
        loc_terms = ["wien"]

    vienna_projects = []
    for block in blocks:
        try:
            id_m = re.search(r'data-id=["\']([^"\']+)["\']', block)
            proj_id = id_m.group(1) if id_m else ""
            if not proj_id:
                continue
                
            p_m = re.search(r'<p>\s*([^<]+?)\s*</p>', block, re.DOTALL)
            location_name = html_lib.unescape(p_m.group(1).strip()) if p_m else ""
            
            h5_m = re.search(r'<h5>(.*?)</h5>', block, re.DOTALL)
            proj_title = html_lib.unescape(h5_m.group(1).strip()) if h5_m else "NHG Project"
            
            # location match
            matched = False
            for term in loc_terms:
                if term == "wien":
                    if re.search(r'\bwien\b', location_name.lower()) or re.search(r'\bwien\b', proj_title.lower()):
                        matched = True
                        break
                else:
                    if term in location_name.lower() or term in proj_title.lower():
                        matched = True
                        break
            
            if matched:
                vienna_projects.append({
                    "id": proj_id,
                    "title": proj_title,
                    "location": location_name
                })
        except Exception as be:
            print(f"Error parsing map block: {be}", file=sys.stderr)
            continue
            
    print(f"Filtered {len(vienna_projects)} projects matching '{location_contains}' to scrape.", file=sys.stderr)
    
    for proj in vienna_projects:
        detail_url = f"https://www.nhg.at/Projekte/Details/?id={proj['id']}"
        print(f"Fetching detail page for NHG project {proj['id']} ({proj['title']}): {detail_url}", file=sys.stderr)
        
        detail_html = fetch_html(detail_url)
        if not detail_html:
            print(f"Failed to fetch detail page for project {proj['id']}.", file=sys.stderr)
            continue
            
        try:
            headers_found = re.findall(r'<header[^>]*class=["\']dropdown__head[^"\']*["\'][^>]*>(.*?)</header>', detail_html, re.DOTALL)
            if not headers_found:
                continue
                
            for idx, head_html in enumerate(headers_found):
                try:
                    top_id_m = re.search(r'data-top-id=["\']([^"\']+)["\']', head_html)
                    top_id = top_id_m.group(1) if top_id_m else f"top-{idx}"
                    
                    listing_id = f"{proj['id']}-{top_id}"
                    
                    title_m = re.search(r'<strong>\s*<span>(.*?)</span>\s*</strong>', head_html, re.DOTALL)
                    if not title_m:
                        continue
                        
                    title_text = html_lib.unescape(title_m.group(1).strip())
                    
                    # size
                    size_m = re.search(r'([\d\.,]+)\s*m²', title_text)
                    size = parse_price(size_m.group(1)) if size_m else 0.0
                    
                    # rooms
                    rooms_m = re.search(r'(\d+)\s*Zimmer', title_text, re.I)
                    rooms = int(rooms_m.group(1)) if rooms_m else 2
                    
                    # price
                    price_m = re.search(r'monatliche\s*Kosten:\s*€?\s*([\d\.,]+)', title_text, re.I)
                    price = parse_price(price_m.group(1)) if price_m else 0.0
                    
                    # location
                    title_container_m = re.search(r'<div class=["\']dropdown__title["\']>(.*?)</div>', head_html, re.DOTALL)
                    location = proj['location']
                    if title_container_m:
                        container_html = title_container_m.group(1)
                        container_html_clean = re.sub(r'<strong>.*?</strong>', '', container_html, flags=re.DOTALL)
                        spans = re.findall(r'<span>(.*?)</span>', container_html_clean, re.DOTALL)
                        spans_clean = [html_lib.unescape(re.sub(r'\s+', ' ', s)).strip() for s in spans if s.strip()]
                        if spans_clean:
                            combined = ", ".join(spans_clean)
                            combined = re.sub(r'^,\s*', '', combined)
                            if combined:
                                location = combined
                                
                    # status 
                    badge_m = re.search(r'class=["\']dropdown__badge[^"\']*["\'][^>]*>(.*?)</span', head_html, re.DOTALL)
                    badge_status = html_lib.unescape(badge_m.group(1).strip()) if badge_m else "frei"
                    badge_status = re.sub(r'\s+', ' ', badge_status).strip().lower()
                    
                    # available if not rented or vergeben
                    available_immediately = ("vergeben" not in badge_status)
                    
                    apartments.append(Apartment(
                        source="NHG",
                        listing_id=listing_id,
                        title=f"{proj['title']} - {rooms} Zimmer",
                        location=location,
                        price=price,
                        size_sqm=size,
                        rooms=rooms,
                        url=detail_url,
                        available_immediately=available_immediately,
                        is_mock=False
                    ))
                    print(f"parsed NHG listing: {proj['title']} - {rooms} Zimmer ({location}) - {price}€", file=sys.stderr)
                except Exception as ue:
                    print(f"Error parsing unit {idx} in project {proj['id']}: {ue}", file=sys.stderr)
                    continue
        except Exception as pe:
            print(f"Error parsing project detail HTML {proj['id']}: {pe}", file=sys.stderr)
            continue
            
    print(f"NHG scraper complete. Total listings parsed: {len(apartments)}", file=sys.stderr)
    return apartments
