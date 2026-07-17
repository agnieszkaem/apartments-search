import sys
import os
from typing import List
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import Config
from src.models import Apartment
from src.filters import apply_filters
from src.dedupe import deduplicate_listings
from src.state import State
from src.mailer import send_notification_email

# scrapper imports
from src.scrapers.gesiba import scrape_gesiba
from src.scrapers.sozialbau import scrape_sozialbau
from src.scrapers.wohnen import scrape_wohnen
from src.scrapers.oevw import scrape_oevw
from src.scrapers.siedlungsunion import scrape_siedlungsunion
from src.scrapers.familienwohnbau import scrape_familienwohnbau
from src.scrapers.oesw import scrape_oesw
from src.scrapers.egw import scrape_egw
from src.scrapers.schwarzatal import scrape_schwarzatal
from src.scrapers.lebenswert_wohnen import scrape_lebenswert_wohnen
from src.scrapers.bwsg import scrape_bwsg

def run_pipeline():
    print("Starting Apartment Monitor run...")


    # 1. load config
    config = Config()
    print(f"Loaded config filters: max_price={config.max_price}€, min_size={config.min_size_sqm}m², min_rooms={config.min_rooms} rooms")
    print(f"Enabled sources: {config.sources}")

    # 1.5. init DB (Neon.tech)
    db_ready = False
    try:
        from src.db import init_db, save_apartments_to_db
        db_ready = init_db()
    except Exception as db_err:
        print(f"Failed to import/init DB: {db_err}")

    # 2. fetch and parse 
    all_raw_listings: List[Apartment] = []
    
    for source in config.sources:
        source_lower = source.lower()
        print(f"Fetching listings from {source}...")
        
        try:
            if source_lower == "gesiba":
                all_raw_listings.extend(scrape_gesiba())
            elif source_lower == "sozialbau":
                all_raw_listings.extend(scrape_sozialbau())
            elif source_lower == "wohnen":
                all_raw_listings.extend(scrape_wohnen())
            elif source_lower == "oevw":
                all_raw_listings.extend(scrape_oevw())
            elif source_lower in ("siedlungsunion", "siedlungs union", "siedlungs-union"):
                all_raw_listings.extend(scrape_siedlungsunion())
            elif source_lower in ("familienwohnbau", "familien wohnbau", "familien-wohnbau"):
                all_raw_listings.extend(scrape_familienwohnbau())
            elif source_lower in ("oesw", "ösw"):
                all_raw_listings.extend(scrape_oesw())
            elif source_lower == "egw":
                all_raw_listings.extend(scrape_egw())
            elif source_lower == "schwarzatal":
                all_raw_listings.extend(scrape_schwarzatal())
            elif source_lower in ("lebenswert_wohnen", "lebenswert-wohnen", "lebenswert wohnen", "lebenswert"):
                all_raw_listings.extend(scrape_lebenswert_wohnen())
            elif source_lower == "bwsg":
                all_raw_listings.extend(scrape_bwsg())
            else:
                print(f"Unknown or unsupported source: {source}")
        except Exception as e:
            print(f"Error scraping source {source}: {e}")

    print(f"Total raw listings fetched: {len(all_raw_listings)}")

    # 3. dedup listings from this run
    unique_listings = deduplicate_listings(all_raw_listings)
    print(f"Unique listings in this run: {len(unique_listings)}")

    # 3.5. Load State BEFORE saving newly scraped listings to Neon DB
    state = State()

    # 4. user filters
    filtered_listings = apply_filters(unique_listings, config)
    print(f"Filtered listings matching criteria: {len(filtered_listings)}")

    # 5. filter out already-seen listings using the loaded State
    new_listings: List[Apartment] = []
    for apt in filtered_listings:
        if state.is_new(apt.stable_key):
            new_listings.append(apt)

    print(f"New matches never seen before: {len(new_listings)}")

    # 6. new matches, send email and save state
    if new_listings:
        print(f"Sending email notification for {len(new_listings)} new matches...")
        email_sent = send_notification_email(new_listings)
        
        if email_sent:
            # Mark them as seen and save state.json
            new_keys = [apt.stable_key for apt in new_listings]
            state.mark_seen(new_keys)
            print("Successfully updated state.json with new listing keys.")
        else:
            print("Skipped updating state.json because email sending failed.")
    else:
        print("No new matches found. No email sent.")

    # 7. save all unique listings to Neon Database for tracking, price changes, and inactivity
    if db_ready:
        try:
            print("Saving unique listings to Neon Database...")
            save_apartments_to_db(unique_listings, config.sources)
        except Exception as db_save_err:
            print(f"Error saving listings to Database: {db_save_err}")

    print("Apartment Monitor run complete.")
if __name__ == "__main__":
    run_pipeline()
