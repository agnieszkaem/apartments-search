import sys
import os
from typing import List
from datetime import datetime

# parent directory is in path 
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import Config
from src.models import Apartment
from src.filters import apply_filters
from src.dedupe import deduplicate_listings
from src.state import State
from src.mailer import send_notification_email

# scrapers
from src.scrapers.gesiba import scrape_gesiba
from src.scrapers.sozialbau import scrape_sozialbau
from src.scrapers.wohnen import scrape_wohnen
from src.scrapers.oevw import scrape_oevw
from src.scrapers.siedlungsunion import scrape_siedlungsunion
from src.scrapers.familienwohnbau import scrape_familienwohnbau
from src.scrapers.oesw import scrape_oesw
from src.scrapers.egw import scrape_egw

def run_pipeline():
    print("Starting Apartment Monitor run...")


    # 1. load config
    config = Config()
    print(f"Loaded config filters: max_price={config.max_price}€, min_size={config.min_size_sqm}m², min_rooms={config.min_rooms} rooms")
    print(f"Enabled sources: {config.sources}")

    # 2. fetch and parse from enabled sources
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
            else:
                print(f"Unknown or unsupported source: {source}")
        except Exception as e:
            print(f"Error scraping source {source}: {e}")

    print(f"Total raw listings fetched: {len(all_raw_listings)}")

    # 3. deduplicate listings from this run
    unique_listings = deduplicate_listings(all_raw_listings)
    print(f"Unique listings in this run: {len(unique_listings)}")

    # 4. apply user filters
    filtered_listings = apply_filters(unique_listings, config)
    print(f"Filtered listings matching criteria: {len(filtered_listings)}")

    # 5. filter out already-seen listings from state.json
    state = State()
    new_listings: List[Apartment] = []
    for apt in filtered_listings:
        if state.is_new(apt.stable_key):
            new_listings.append(apt)

    print(f"New matches never seen before: {len(new_listings)}")

    # 6. if new matches, send email and save state
    if new_listings:
        print(f"Sending email notification for {len(new_listings)} new matches...")
        email_sent = send_notification_email(new_listings)
        
        if email_sent:
            # Mark as seen and save state.json
            new_keys = [apt.stable_key for apt in new_listings]
            state.mark_seen(new_keys)
            print("Successfully updated state.json with new listing keys.")
        else:
            print("Skipped updating state.json because email sending failed.")
    else:
        print("No new matches found. No email sent.")

    print("Apartment Monitor run complete.")

if __name__ == "__main__":
    run_pipeline()
