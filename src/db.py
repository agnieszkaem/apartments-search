import os
import re
from datetime import datetime
from typing import List, Set, Optional

try:
    import psycopg2
    from psycopg2.extras import execute_values
    HAS_POSTGRES = True
except ImportError:
    HAS_POSTGRES = False

def get_db_url() -> str:
    return os.environ.get("DATABASE_URL", "").strip()

def is_db_configured() -> bool:
    return HAS_POSTGRES and bool(get_db_url())

def extract_district(location_str: str, title_str: str = "") -> Optional[int]:
    combined = f"{location_str or ''} {title_str or ''}".lower()
    
    # match Vienna postal codes 1010 to 1230
    zip_match = re.search(r'\b1([0-2][0-9])0\b', combined)
    if zip_match:
        dist = int(zip_match.group(1))
        if 1 <= dist <= 23:
            return dist
            
    # match '22. Bezirk' or '10. Bezirk' or '22. bez'
    bezirk_match = re.search(r'\b([1-9]|1[0-9]|2[0-3])\s*\.\s*(?:bezirk|bez)?\b', combined)
    if bezirk_match:
        return int(bezirk_match.group(1))
        
    return None

def init_db():
    if not is_db_configured():
        if not HAS_POSTGRES:
            print("psycopg2-binary is not installed. Database operations are disabled.")
        else:
            print("DATABASE_URL is not set. Database operations are disabled.")
        return False
        
    try:
        conn = psycopg2.connect(get_db_url())
        with conn.cursor() as cur:
            # 1. main apartments table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS apartments (
                    stable_key VARCHAR(255) PRIMARY KEY,
                    source VARCHAR(50) NOT NULL,
                    listing_id VARCHAR(100),
                    title VARCHAR(255) NOT NULL,
                    location TEXT,
                    district INT,
                    price NUMERIC(10, 2),
                    size_sqm NUMERIC(8, 2),
                    rooms INT,
                    url TEXT,
                    available_immediately BOOLEAN DEFAULT TRUE,
                    registered BOOLEAN DEFAULT FALSE,
                    is_active BOOLEAN DEFAULT TRUE,
                    first_seen TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    last_seen TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # indexes for optimal querying
            cur.execute("CREATE INDEX IF NOT EXISTS idx_apartments_source ON apartments(source);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_apartments_is_active ON apartments(is_active);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_apartments_district ON apartments(district);")
            
            # 2. history table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS apartment_history (
                    id SERIAL PRIMARY KEY,
                    stable_key VARCHAR(255) NOT NULL REFERENCES apartments(stable_key) ON DELETE CASCADE,
                    price NUMERIC(10, 2),
                    size_sqm NUMERIC(8, 2),
                    is_active BOOLEAN,
                    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_history_stable_key ON apartment_history(stable_key);")
            
            # 3. notified_listings table to track emailed matches 
            cur.execute("""
                CREATE TABLE IF NOT EXISTS notified_listings (
                    stable_key VARCHAR(255) PRIMARY KEY,
                    notified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            conn.commit()
            print("Database tables successfully verified/created in Neon.")
            return True
    except Exception as e:
        print(f"Error initializing database: {e}")
        return False
    finally:
        if 'conn' in locals() and conn:
            conn.close()

def save_apartments_to_db(apartments, scraped_sources: List[str] = None) -> Set[str]:
    if not is_db_configured():
        return set()
        
    new_keys = set()
    active_keys_in_run = set(apt.stable_key for apt in apartments)
    
    try:
        conn = psycopg2.connect(get_db_url())
        with conn.cursor() as cur:
            # clean up existing non-Vienna apartments from db
            cur.execute("SELECT stable_key, title, location, district FROM apartments")
            existing_db_rows = cur.fetchall()
            keys_to_delete = []
            for key, title, location, dist in existing_db_rows:
                has_vienna_term = bool(re.search(r'\bwien\b', (location or "") + " " + (title or ""), re.IGNORECASE))
                is_wiener_neustadt_or_neudorf = bool(re.search(r'\bwiener\s+(neustadt|neudorf)\b', (location or "") + " " + (title or ""), re.IGNORECASE))
                is_vienna = (dist is not None) or (has_vienna_term and not is_wiener_neustadt_or_neudorf)
                if not is_vienna:
                    keys_to_delete.append(key)
            
            if keys_to_delete:
                print(f"Deleting {len(keys_to_delete)} non-Vienna apartments from db...")
                cur.execute("DELETE FROM apartments WHERE stable_key = ANY(%s)", (keys_to_delete,))

            for apt in apartments:
                stable_key = apt.stable_key
                district = extract_district(apt.location, apt.title)
                
                # check if in Vienna
                has_vienna_term = bool(re.search(r'\bwien\b', (apt.location or "") + " " + (apt.title or ""), re.IGNORECASE))
                is_wiener_neustadt_or_neudorf = bool(re.search(r'\bwiener\s+(neustadt|neudorf)\b', (apt.location or "") + " " + (apt.title or ""), re.IGNORECASE))
                is_vienna = (district is not None) or (has_vienna_term and not is_wiener_neustadt_or_neudorf)
                
                if not is_vienna:
                    continue
                
                # check if listing already exists
                cur.execute(
                    "SELECT price, size_sqm, is_active FROM apartments WHERE stable_key = %s",
                    (stable_key,)
                )
                existing = cur.fetchone()
                
                is_new = existing is None
                if is_new:
                    new_keys.add(stable_key)
                
                # upsert main record
                cur.execute("""
                    INSERT INTO apartments (
                        stable_key, source, listing_id, title, location, district,
                        price, size_sqm, rooms, url, available_immediately, is_active, last_seen
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE, CURRENT_TIMESTAMP)
                    ON CONFLICT (stable_key) DO UPDATE SET
                        title = EXCLUDED.title,
                        location = EXCLUDED.location,
                        district = EXCLUDED.district,
                        price = EXCLUDED.price,
                        size_sqm = EXCLUDED.size_sqm,
                        rooms = EXCLUDED.rooms,
                        url = EXCLUDED.url,
                        available_immediately = EXCLUDED.available_immediately,
                        is_active = TRUE,
                        last_seen = CURRENT_TIMESTAMP;
                """, (
                    stable_key, apt.source, apt.listing_id or None, apt.title,
                    apt.location or None, district, apt.price or 0.0,
                    apt.size_sqm or 0.0, apt.rooms or 0, apt.url or None,
                    apt.available_immediately
                ))
                
                # add history snapshot if it's new
                if is_new:
                    cur.execute("""
                        INSERT INTO apartment_history (stable_key, price, size_sqm, is_active)
                        VALUES (%s, %s, %s, TRUE)
                    """, (stable_key, apt.price or 0.0, apt.size_sqm or 0.0))
                else:
                    old_price, old_size, old_active = existing
                    price_changed = abs(float(old_price) - float(apt.price or 0.0)) > 0.01
                    size_changed = abs(float(old_size) - float(apt.size_sqm or 0.0)) > 0.01
                    became_active = not old_active
                    
                    if price_changed or size_changed or became_active:
                        cur.execute("""
                            INSERT INTO apartment_history (stable_key, price, size_sqm, is_active)
                            VALUES (%s, %s, %s, TRUE)
                        """, (stable_key, apt.price or 0.0, apt.size_sqm or 0.0))
            
            # inactivate listings that are no longer visible from the scraped sources
            if scraped_sources:
                # find all currently active apartments in db for these sources that were NOT in the current run
                placeholders = ', '.join(['%s'] * len(scraped_sources))
                query = f"""
                    SELECT stable_key, price, size_sqm 
                    FROM apartments 
                    WHERE is_active = TRUE AND source IN ({placeholders})
                """
                cur.execute(query, tuple(scraped_sources))
                active_db_apts = cur.fetchall()
                
                for key, price, size in active_db_apts:
                    if key not in active_keys_in_run:
                        print(f"Listing '{key}' is no longer active (hidden by provider). Updating status to inactive.")
                        # mark inactive
                        cur.execute(
                            "UPDATE apartments SET is_active = FALSE, last_seen = CURRENT_TIMESTAMP WHERE stable_key = %s",
                            (key,)
                        )
                        cur.execute("""
                            INSERT INTO apartment_history (stable_key, price, size_sqm, is_active)
                            VALUES (%s, %s, %s, FALSE)
                        """, (key, price, size))
            
            conn.commit()
            print(f"Saved {len(apartments)} listings in DB. Found {len(new_keys)} new listings.")
            return new_keys
    except Exception as e:
        print(f"Error writing to database: {e}")
        return set()
    finally:
        if 'conn' in locals() and conn:
            conn.close()

def get_seen_keys_from_db() -> Set[str]:
    """Returns a set of all notified keys currently in the database."""
    if not is_db_configured():
        return set()
        
    try:
        conn = psycopg2.connect(get_db_url())
        with conn.cursor() as cur:
            cur.execute("SELECT stable_key FROM notified_listings")
            rows = cur.fetchall()
            return set(r[0] for r in rows)
    except Exception as e:
        print(f"Error fetching seen keys from DB: {e}")
        return set()
    finally:
        if 'conn' in locals() and conn:
            conn.close()

def save_notified_keys_to_db(keys: List[str]):
    """Saves a list of notified apartment keys to db."""
    if not is_db_configured() or not keys:
        return
        
    try:
        conn = psycopg2.connect(get_db_url())
        with conn.cursor() as cur:
            for key in keys:
                cur.execute("""
                    INSERT INTO notified_listings (stable_key)
                    VALUES (%s)
                    ON CONFLICT (stable_key) DO NOTHING
                """, (key,))
            conn.commit()
            print(f"Saved {len(keys)} notified keys to database.")
    except Exception as e:
        print(f"Error saving notified keys to DB: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()
