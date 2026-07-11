import sys
import re
from typing import List
from concurrent.futures import ThreadPoolExecutor
from src.models import Apartment
from src.scrapers.utils import fetch_html

def scrape_wohnen_project(p_url: str) -> List[Apartment]:
    try:
        p_html = fetch_html(p_url)
        if not p_html:
            return []

        # Parse H1 for project title
        h1_m = re.search(r"<h1[^>]*>(.*?)</h1>", p_html, re.DOTALL)
        h1_text = "Wohnen.at Project"
        if h1_m:
            h1_text = re.sub(r"<[^>]+>", "", h1_m.group(1)).strip()
            h1_text = " ".join(h1_text.split())

        # Extract location from URL or H1
        zip_city_m = re.search(r"(\d{4}-wien)", p_url.lower())
        location = zip_city_m.group(1).replace("-", " ").title() if zip_city_m else "Wien"

        # Parse rows inside app-RealtyListBlock
        rows = re.findall(r"<tr[^>]*class=\"[^\"]*app-RealtyListBlock-row[^\"]*\"[^>]*>(.*?)</tr>", p_html, re.DOTALL)
        
        apartments: List[Apartment] = []
        for idx, row in enumerate(rows):
            try:
                # Top Number
                top_m = re.search(r"class=\"app-RealtyListBlock-cell--TopNumber\"[^>]*>(.*?)</td>", row, re.DOTALL)
                top_str = ""
                if top_m:
                    top_str = re.sub(r"<[^>]+>", "", top_m.group(1)).replace("&nbsp;", " ").strip()
                    top_str = " ".join(top_str.split())

                # Rooms
                rooms_m = re.search(r"class=\"app-RealtyListBlock-cell--RoomCount\"[^>]*>(.*?)</td>", row, re.DOTALL)
                rooms = 2
                if rooms_m:
                    rooms_text = re.sub(r"<[^>]+>", "", rooms_m.group(1)).replace("&nbsp;", " ").strip()
                    rooms_text = " ".join(rooms_text.split())
                    digit_m = re.search(r"\d+", rooms_text)
                    if digit_m:
                        rooms = int(digit_m.group(0))

                # Area (size_sqm)
                area_m = re.search(r"class=\"app-RealtyListBlock-cell--Area\"[^>]*>(.*?)</td>", row, re.DOTALL)
                area = 0.0
                if area_m:
                    area_text = re.sub(r"<[^>]+>", "", area_m.group(1)).replace("&nbsp;", " ").strip()
                    area_text = " ".join(area_text.split())
                    num_m = re.search(r"[\d\.,]+", area_text)
                    if num_m:
                        num_str = num_m.group(0).replace(".", "").replace(",", ".")
                        area = float(num_str)

                # Price (TotalRent)
                rent_m = re.search(r"class=\"app-RealtyListBlock-cell--TotalRent\"[^>]*>(.*?)</td>", row, re.DOTALL)
                rent = 0.0
                if rent_m:
                    rent_text = re.sub(r"<[^>]+>", "", rent_m.group(1)).replace("&nbsp;", " ").strip()
                    rent_text = " ".join(rent_text.split())
                    num_m = re.search(r"€\s*([\d\.,]+)", rent_text)
                    if not num_m:
                        num_m = re.search(r"[\d\.,]+", rent_text)
                    if num_m:
                        num_str = num_m.group(1 if len(num_m.groups()) > 0 else 0).replace(".", "").replace(",", ".")
                        rent = float(num_str)

                # Link
                link_m = re.search(r"href=\"([^\"]+)\"[^>]*data-router-target=\"rolv2:sidebar\"", row)
                if not link_m:
                    link_m = re.search(r"href=\"([^\"]+)\"", row)
                link = p_url
                if link_m:
                    link = "https://www.wohnen.at" + link_m.group(1) if link_m.group(1).startswith("/") else link_m.group(1)

                # Listing ID from details link
                slug_m = re.search(r"bestandseinheiten/([a-zA-Z0-9-]+)", link)
                listing_id = slug_m.group(1) if slug_m else f"w-{top_str.replace(' ', '-').lower()}"

                title = f"{h1_text} - Top {top_str}" if top_str else h1_text

                if rent <= 0:
                    print(f"Skipping Wohnen.at listing {listing_id} due to invalid or unparsed price.", file=sys.stderr)
                    continue
                if area <= 0:
                    print(f"Skipping Wohnen.at listing {listing_id} due to invalid or unparsed size.", file=sys.stderr)
                    continue

                apartments.append(Apartment(
                    source="Wohnen.at",
                    listing_id=listing_id,
                    title=title,
                    location=location,
                    price=rent,
                    size_sqm=area,
                    rooms=rooms,
                    url=link,
                    available_immediately=True
                ))
            except Exception as e:
                print(f"Error parsing individual Wohnen.at row: {e}", file=sys.stderr)
                continue

        return apartments
    except Exception as e:
        print(f"Error parsing Wohnen.at project {p_url}: {e}", file=sys.stderr)
        return []

def scrape_wohnen() -> List[Apartment]:
    main_url = "https://www.wohnen.at/immobilienangebot/genossenschaftswohnung/filter/v1-mt:rent-oc:residential/"
    
    main_html = fetch_html(main_url)
    if not main_html:
        print("Wohnen.at main filter page returned empty.", file=sys.stderr)
        return []

    try:
        # Extract project links
        hrefs = re.findall(r"href=\"([^\"]+)\"", main_html)
        project_links = []
        for h in hrefs:
            # We want subpages ending in 'wien' (e.g. schumanngasse-64-1170-wien/)
            if "/immobilienangebot/genossenschaftswohnung/" in h and h.strip("/").endswith("wien"):
                full_link = "https://www.wohnen.at" + h if h.startswith("/") else h
                if full_link not in project_links:
                    project_links.append(full_link)

        if not project_links:
            print("No project links found on Wohnen.at.", file=sys.stderr)
            return []

        print(f"Found project links to scrape: {project_links}", file=sys.stderr)

        all_apartments: List[Apartment] = []
        # Scraping projects in parallel using a ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=3) as executor:
            results = executor.map(scrape_wohnen_project, project_links)
            for res in results:
                all_apartments.extend(res)

        if all_apartments:
            print(f"Successfully scraped {len(all_apartments)} real Wohnen.at listings.", file=sys.stderr)
            return all_apartments
        else:
            print("No apartments parsed from Wohnen.at projects.", file=sys.stderr)
            return []

    except Exception as e:
        print(f"Wohnen.at parsing failed: {e}", file=sys.stderr)
        return []
