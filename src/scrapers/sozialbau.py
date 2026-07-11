import os
import sys
import re
import urllib.request
import urllib.parse
from typing import List
from src.models import Apartment

def scrape_sozialbau() -> List[Apartment]:
    # 1. Retrieve session cookies from environment variables
    cookie_str = os.getenv("SOZIALBAU_COOKIE")
    jsessionid = os.getenv("SOZIALBAU_JSESSIONID")
    serverid = os.getenv("SOZIALBAU_SERVERID")

    # If user provided separate variables, combine them
    if not cookie_str and jsessionid and serverid:
        cookie_str = f"JSESSIONID={jsessionid}; SERVERID={serverid}"

    # If still no cookie, return empty list
    if not cookie_str:
        print("Sozialbau session cookie (SOZIALBAU_COOKIE or SOZIALBAU_JSESSIONID & SOZIALBAU_SERVERID) is not set in the environment.", file=sys.stderr)
        return []

    url = "https://angebote.sozialbau.at/sobitvX/htmlprospect/home.xhtml"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Cookie": cookie_str
    }

    try:
        # Step 1: Initial GET to fetch the dynamic ViewState and menu button source ID
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            html = response.read().decode("utf-8", errors="ignore")

        # Extract ViewState
        view_state_m = re.search(r'name="javax\.faces\.ViewState"[^>]*value="([^"]+)"', html)
        if not view_state_m:
            view_state_m = re.search(r"name='javax\.faces\.ViewState'[^>]*value='([^']+)'", html)
        
        if not view_state_m:
            print("Failed to extract javax.faces.ViewState from Sozialbau page. Check cookie validity.", file=sys.stderr)
            return []
        
        view_state = view_state_m.group(1)

        # Extract the source ID for 'Sofort verfügbar' menu item
        source_id = "menuform:j_idt29"  # Default fallback
        matches = re.finditer(r'<a[^>]*onclick=\"PrimeFaces\.ab\(\{s:&quot;([^&]+)&quot;,f:&quot;menuform&quot;.*?\}\);return false;\"[^>]*>(.*?)</a>', html, re.DOTALL)
        found = False
        for m in matches:
            label = re.sub(r'<[^>]+>', '', m.group(2)).strip()
            if 'sofort' in label.lower():
                source_id = m.group(1)
                found = True
                break
        
        if not found:
            matches = re.finditer(r"<a[^>]*onclick='PrimeFaces\.ab\(\{s:\x22([^\x22]+)\x22,f:\x22menuform\x22.*?\}\);return false;'[^>]*>(.*?)</a>", html, re.DOTALL)
            for m in matches:
                label = re.sub(r'<[^>]+>', '', m.group(2)).strip()
                if 'sofort' in label.lower():
                    source_id = m.group(1)
                    found = True
                    break

        print(f"Executing Sozialbau live scrape using view_state={view_state} and source_id={source_id}", file=sys.stderr)

        # Step 2: Perform PrimeFaces AJAX POST request to click 'Sofort verfügbar'
        post_data = {
            'javax.faces.partial.ajax': 'true',
            'javax.faces.source': source_id,
            'javax.faces.partial.execute': source_id,
            'javax.faces.partial.render': 'f1:ajax-main',
            source_id: source_id,
            'menuform': 'menuform',
            'javax.faces.ViewState': view_state
        }
        
        payload = urllib.parse.urlencode(post_data).encode("utf-8")
        
        post_headers = {
            "User-Agent": headers["User-Agent"],
            "Cookie": cookie_str,
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Faces-Request": "partial/ajax",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": url
        }

        post_req = urllib.request.Request(url, data=payload, headers=post_headers, method="POST")
        with urllib.request.urlopen(post_req, timeout=15) as pr:
            resp_xml = pr.read().decode("utf-8", errors="ignore")

        # Extract update content of f1:ajax-main from JSF XML response
        update_m = re.search(r'<update id=\"f1:ajax-main\">\s*<!\[CDATA\[(.*?)\]\]>\s*</update>', resp_xml, re.DOTALL)
        if not update_m:
            print("No f1:ajax-main update section found in Sozialbau XML response.", file=sys.stderr)
            return []

        cdata_content = update_m.group(1)

        # Check if we were redirected to Login/Register screen
        if "Damit Sie sich über unser Wohnungsangebot informieren zu können" in cdata_content or "Anmeldung" in cdata_content:
            print("Sozialbau cookies provided are expired or invalid. Authenticated session was rejected.", file=sys.stderr)
            return []

        # Step 3: Parse apartments using space-normalized text extraction and strong-tag pairing
        # Replace HTML tags with spaces to avoid layout changes splitting words for size/rooms/price regex
        text = re.sub(r'<[^>]+>', ' ', cdata_content)
        text = text.replace('&nbsp;', ' ').replace('&#160;', ' ')
        text = ' '.join(text.split())

        # Match pattern: Size m 2 | Rooms Zimmer € Price
        flat_pattern = r'(\d+[\.,]?\d*)\s*(?:m\s*2|m²|m2)\s*\|\s*(\d+)\s*Zimmer\s*(?:Miete:\s*|Miete\s*:\s*)?€\s*([\d\.,]+)'
        matches = list(re.finditer(flat_pattern, text, re.IGNORECASE))
        
        # Extract addresses from strong tags
        strongs = re.findall(r'<strong>(.*?)</strong>', cdata_content, re.DOTALL)
        strongs = [re.sub(r'<[^>]+>', '', s).strip() for s in strongs]
        strongs = [' '.join(s.split()) for s in strongs]

        apartments: List[Apartment] = []

        for idx, match in enumerate(matches):
            try:
                size = float(match.group(1).replace(',', '.'))
                rooms = int(match.group(2))
                price = float(match.group(3).replace('.', '').replace(',', '.'))
                
                # Pair with strong tag address by index if available
                address = strongs[idx] if idx < len(strongs) else ""
                zip_code = "1000"
                street = ""

                if address:
                    addr_match = re.search(r'^(\d{4})\s+([^,]+),\s*(.*)$', address)
                    if addr_match:
                        zip_code = addr_match.group(1)
                        city = addr_match.group(2).strip().title()
                        street = addr_match.group(3).strip()
                        location = f"{zip_code} {city}"
                        title = f"Wohnung {street}"
                    else:
                        location = address
                        title = f"Sozialbau {rooms} Zimmer Wohnung"
                else:
                    location = "Wien"
                    title = f"Sozialbau {rooms} Zimmer Wohnung - {size}m²"

                listing_id = f"sb-live-{idx+1}"
                if address and street:
                    clean_street = re.sub(r'[^a-zA-Z0-9]', '-', street).lower()
                    listing_id = f"sb-{zip_code}-{clean_street}"

                apartments.append(Apartment(
                    source="Sozialbau",
                    listing_id=listing_id,
                    title=title,
                    location=location,
                    price=price,
                    size_sqm=size,
                    rooms=rooms,
                    url=url,
                    available_immediately=True
                ))
            except Exception as e:
                print(f"Error parsing individual Sozialbau listing: {e}", file=sys.stderr)
                continue

        if apartments:
            print(f"Successfully scraped {len(apartments)} real Sozialbau listings using active session.", file=sys.stderr)
            return apartments
        else:
            print("No active listings found on Sozialbau portal. They might have no immediate apartments.", file=sys.stderr)
            return []

    except Exception as e:
        print(f"Sozialbau scraper failed with exception: {e}", file=sys.stderr)
        return []
