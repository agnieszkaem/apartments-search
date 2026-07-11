import sys
import re
import json
import html as html_lib
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
        if "." in val_str:
            parts = val_str.split(".")
            if len(parts[-1]) == 3:
                val_str = "".join(parts)
    try:
        return float(val_str)
    except ValueError:
        return 0.0

def scrape_oesw() -> List[Apartment]:
    main_url = "https://www.oesw.at/immobilienangebot/sofort-wohnen.html?objectType=1&financingType=2"
    
    main_html = fetch_html(main_url)
    if not main_html:
        print("ÖSW main page fetch returned empty.", file=sys.stderr)
        return []

    try:
        apartments: List[Apartment] = []

        # Find all data-objlist-url entries on the main page
        # Example: data-objlist-url="/immobilienangebot/sofort-wohnen/mhimmo/Wohnhaus/1030-wien-leopold-boehm-strasse-5-1.html?type=1338&amp;cHash=206edb8f103d6f1ea6406f8612e0b338"
        project_urls = re.findall(r'data-objlist-url="([^"]+)"', main_html)
        if not project_urls:
            print("No project URLs found on ÖSW main page.", file=sys.stderr)
            return []

        for p_url in project_urls:
            try:
                p_url_decoded = html_lib.unescape(p_url)
                
                # Check if this project is strictly inside Vienna (Wien)
                # Vienna postcodes are 1xxx. Let's find any 4-digit code and check if it starts with '1'.
                postcodes = re.findall(r'\b(\d{4})\b', p_url_decoded)
                is_vienna = False
                if postcodes:
                    if any(pc.startswith('1') for pc in postcodes):
                        is_vienna = True
                else:
                    if 'wien' in p_url_decoded.lower():
                        is_vienna = True

                if not is_vienna:
                    # Skip non-Vienna projects immediately without querying sub-pages
                    continue

                # Fetch the sub-page JSON containing flat listings for this project
                sub_page_url = "https://www.oesw.at" + p_url_decoded
                sub_page_json_str = fetch_html(sub_page_url)
                if not sub_page_json_str:
                    continue

                try:
                    sub_data = json.loads(sub_page_json_str)
                except Exception as je:
                    print(f"Failed to parse JSON for ÖSW project sub-page: {je}", file=sys.stderr)
                    continue

                if not sub_data.get("success"):
                    continue

                content = sub_data.get("content", "")
                if not content:
                    continue

                # Unescape escaped quotes/slashes in the raw content string
                content_clean = content.replace('\\"', '"').replace('\\/', '/')

                # Extract individual flat list items
                blocks = re.findall(r'<li[^>]*>(.*?)</li>', content_clean, re.DOTALL)
                for b in blocks:
                    try:
                        # Detail link
                        link_m = re.search(r'href="([^"]+)"', b)
                        if not link_m:
                            continue
                        
                        relative_flat_link = html_lib.unescape(link_m.group(1))
                        full_flat_link = "https://www.oesw.at" + relative_flat_link

                        # Try to extract the erpId to use as listing ID
                        erp_id_m = re.search(r'erpId%5D=([^&"]+)', relative_flat_link)
                        if not erp_id_m:
                            erp_id_m = re.search(r'erpId=([^&"]+)', relative_flat_link)
                        
                        listing_id = erp_id_m.group(1) if erp_id_m else relative_flat_link.split("/")[-1]

                        # Unit details (e.g. "Stock 21 • Top 319")
                        unit_m = re.search(r'<h4>(.*?)</h4>', b, re.DOTALL)
                        unit_info = ""
                        if unit_m:
                            unit_info = html_lib.unescape(unit_m.group(1)).strip()
                            unit_info = re.sub(r'<[^>]+>', '', unit_info)
                            unit_info = re.sub(r'\s*•\s*', ', ', unit_info)
                            unit_info = re.sub(r'\s*,\s*', ', ', unit_info)
                            unit_info = re.sub(r'\s+', ' ', unit_info).strip()

                        # Price from sub-page as fallback/primary
                        price_m = re.search(r'pro Monat:\s*(?:€|EUR|&euro;)?\s*([\d\.,]+)', b, re.IGNORECASE)
                        sub_price = parse_price(price_m.group(1)) if price_m else 0.0

                        # Fetch individual flat detail page to get size, rooms, exact address
                        detail_html = fetch_html(full_flat_link)
                        if not detail_html:
                            continue

                        # Extract exact size (Größe)
                        size_m = re.search(r'Größe:\s*</strong>\s*([\d\.,]+)', detail_html, re.IGNORECASE)
                        size = parse_price(size_m.group(1)) if size_m else 0.0

                        # Extract rooms (Zimmer)
                        rooms_m = re.search(r'Zimmer:\s*</strong>\s*(\d+)', detail_html, re.IGNORECASE)
                        rooms = int(rooms_m.group(1)) if rooms_m else 2

                        # Extract price pro Monat (Kosten pro Monat) from detail page
                        price_detail_m = re.search(r'Kosten pro Monat:\s*</strong>\s*(?:€|EUR|&euro;)?\s*([\d\.,]+)', detail_html, re.IGNORECASE)
                        price = parse_price(price_detail_m.group(1)) if price_detail_m else sub_price

                        # Extract address (adr-1 is postcode/city, adr-2 is street)
                        adr1_m = re.search(r'class="adr-1">\s*(.*?)\s*</span>', detail_html, re.DOTALL)
                        adr1 = adr1_m.group(1).strip() if adr1_m else "Wien"
                        adr1 = re.sub(r'<[^>]+>', '', adr1)

                        adr2_m = re.search(r'class="adr-2">\s*(.*?)\s*</h2>', detail_html, re.DOTALL)
                        adr2 = adr2_m.group(1).strip() if adr2_m else ""
                        adr2 = re.sub(r'<[^>]+>', '', adr2)

                        # Skip if it turns out the address postcode is not in Vienna
                        detail_postcodes = re.findall(r'\b(\d{4})\b', adr1)
                        if detail_postcodes:
                            if not any(pc.startswith('1') for pc in detail_postcodes):
                                continue

                        street_address = f"{adr2}, {unit_info}" if adr2 and unit_info else (adr2 if adr2 else adr1)
                        title = f"{street_address}"

                        apartments.append(Apartment(
                            source="ÖSW",
                            listing_id=listing_id,
                            title=title,
                            location=adr1,
                            price=price,
                            size_sqm=size,
                            rooms=rooms,
                            url=full_flat_link,
                            available_immediately=True,
                            is_mock=False
                        ))

                    except Exception as fe:
                        print(f"Error parsing ÖSW flat item: {fe}", file=sys.stderr)
                        continue

            except Exception as pe:
                print(f"Error scraping ÖSW project {p_url}: {pe}", file=sys.stderr)
                continue

        print(f"Successfully scraped {len(apartments)} real ÖSW listings.", file=sys.stderr)
        return apartments

    except Exception as e:
        print(f"ÖSW scraper parsing failed: {e}", file=sys.stderr)
        return []
