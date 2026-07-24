import sys
import re
import json
import urllib.request
import urllib.parse
import html as html_lib
from typing import List
from src.models import Apartment
from src.config import Config

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

def scrape_arwag() -> List[Apartment]:
    load_url = "https://www.arwag.at/immobiliensuche/lazylist/load/Realties"
    view_url = "https://www.arwag.at/immobiliensuche/lazylist/view/Realties"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest"
    }
    
    apartments: List[Apartment] = []
    
    print("Starting ARWAG scraper...", file=sys.stderr)
    
    try:
        config = Config()
        max_price = config.max_price or 1100.0
    except Exception as ce:
        print(f"Could not load config in ARWAG scraper: {ce}", file=sys.stderr)
        max_price = 1100.0
    
    context_dict = {
        "filter_marketingType": "rent",
        "filter_occupancy": "residential",
        "filter_totalRent_max": max_price
    }
    
    params = {
        "context": json.dumps(context_dict),
        "ids": []
    }
    encoded_params = urllib.parse.urlencode(params)
    full_load_url = f"{load_url}?{encoded_params}"
    
    print(f"Fetching ARWAG matching IDs from: {full_load_url}", file=sys.stderr)
    try:
        req = urllib.request.Request(full_load_url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as res:
            load_data = json.loads(res.read().decode("utf-8"))
            items = load_data.get("list", [])
            print(f"ARWAG found {len(items)} matching listings.", file=sys.stderr)
            
            if not items:
                return []
                
            view_tokens = [item.get("viewToken") for item in items if item.get("viewToken")]
            if not view_tokens:
                print("No view tokens found for ARWAG listings.", file=sys.stderr)
                return []
                
            view_params_serialized = {
                "context": json.dumps(context_dict),
                "viewTokens": json.dumps(view_tokens),
                "viewType": "default"
            }
            encoded_view_params = urllib.parse.urlencode(view_params_serialized)
            full_view_url = f"{view_url}?{encoded_view_params}"
            
            print(f"Fetching ARWAG listing details (views) from: {view_url}", file=sys.stderr)
            view_req = urllib.request.Request(full_view_url, headers=headers)
            with urllib.request.urlopen(view_req, timeout=15) as view_res:
                view_data = json.loads(view_res.read().decode("utf-8"))
                views_list = view_data.get("views", [])
                print(f"Received {len(views_list)} details views from ARWAG.", file=sys.stderr)
                
                for view_entry in views_list:
                    try:
                        view_html = view_entry.get("view", "")
                        realty_id = str(view_entry.get("id"))
                        
                        if not view_html:
                            continue
                            
                        # title
                        headline_m = re.search(r'<h3[^>]*class="app-ObjectBlockEntry-headline"[^>]*>(.*?)</h3>', view_html, re.DOTALL | re.I)
                        title = headline_m.group(1).strip() if headline_m else "ARWAG Apartment"
                        title = html_lib.unescape(title)
                        title = re.sub(r'\s+', ' ', title).replace("&nbsp;", " ").strip()
                        
                        #location
                        address_m = re.search(r'<p[^>]*class="app-ObjectBlockEntry-address"[^>]*>(.*?)</p>', view_html, re.DOTALL | re.I)
                        location = ""
                        if address_m:
                            # strip tags, normalize spaces
                            location_raw = address_m.group(1)
                            location_clean = re.sub(r'<[^>]+>', ' ', location_raw)
                            location = html_lib.unescape(location_clean)
                            location = re.sub(r'\s+', ' ', location).replace("&nbsp;", " ").strip()
                        if not location:
                            location = "Wien"
                            
                        #  size
                        size_m = re.search(r'Fläche:.*?<strong[^>]*>(.*?)</strong>', view_html, re.DOTALL | re.I)
                        size = 0.0
                        if size_m:
                            size_str = html_lib.unescape(size_m.group(1).strip())
                            size = parse_price(size_str)
                            
                        # price
                        price_m = re.search(r'(?:Miete|Kosten|Preis):.*?<strong[^>]*>(.*?)</strong>', view_html, re.DOTALL | re.I)
                        price = 0.0
                        if price_m:
                            price_str = html_lib.unescape(price_m.group(1).strip())
                            price = parse_price(price_str)
                            
                        # rooms
                        rooms_m = re.search(r'Zimmer:.*?<strong[^>]*>(.*?)</strong>', view_html, re.DOTALL | re.I)
                        rooms = 2  # default fallback
                        if rooms_m:
                            rooms_str = html_lib.unescape(rooms_m.group(1).strip())
                            try:
                                rooms = int(re.sub(r'[^\d]', '', rooms_str))
                            except:
                                rooms = 2
                                
                        # Parse Details URL
                        links = re.findall(r'href="([^"]+)"', view_html)
                        url = "https://www.arwag.at/immobiliensuche/"
                        for link in links:
                            if "/immobilien/" in link:
                                url = "https://www.arwag.at" + link if link.startswith("/") else link
                                break
                                
                        # Skip if price or size is invalid/missing
                        if price <= 0.0:
                            print(f"Skipping ARWAG listing {realty_id} due to invalid or unparsed price.", file=sys.stderr)
                            continue
                        if size <= 0.0:
                            print(f"Skipping ARWAG listing {realty_id} due to invalid or unparsed size.", file=sys.stderr)
                            continue
                            
                        apartments.append(Apartment(
                            source="ARWAG",
                            listing_id=realty_id,
                            title=title,
                            location=location,
                            price=price,
                            size_sqm=size,
                            rooms=rooms,
                            url=url,
                            available_immediately=True,
                            is_mock=False
                        ))
                        print(f"Successfully parsed ARWAG listing: {title} ({location}) - {price}€, {size}m²", file=sys.stderr)
                    except Exception as item_err:
                        print(f"Error parsing ARWAG listing item: {item_err}", file=sys.stderr)
                        continue
                        
    except Exception as e:
        print(f"ARWAG scraping failed: {e}", file=sys.stderr)
        
    print(f"ARWAG scraper complete. Total listings parsed: {len(apartments)}", file=sys.stderr)
    return apartments
