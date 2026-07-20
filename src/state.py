import os
import json
from typing import List, Set

class State:
    def __init__(self, filepath: str = "state.json"):
        if not os.path.exists(filepath):
            possible_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), filepath)
            if os.path.exists(possible_path):
                filepath = possible_path

        self.filepath = filepath
        self.seen_keys: Set[str] = set()
        self.load()

    def load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self.seen_keys = set(data)
            except Exception as e:
                print(f"Error loading state {self.filepath}: {e}")
                self.seen_keys = set()
        else:
            self.seen_keys = set()

        #optinal - load from db to keep them fully in-sync
        try:
            from src.db import is_db_configured, get_seen_keys_from_db
            if is_db_configured():
                db_keys = get_seen_keys_from_db()
                if db_keys:
                    self.seen_keys.update(db_keys)
                    print(f"Synced {len(db_keys)} seen keys from Neon database.")
        except Exception as e:
            print(f"Note: database seen sync skipped: {e}")

    def is_new(self, key: str) -> bool:
        return key not in self.seen_keys

    def mark_seen(self, keys: List[str]):
        for key in keys:
            self.seen_keys.add(key)
        self.save()
        
        # sync to db to keep them fully in-sync
        try:
            from src.db import is_db_configured, save_notified_keys_to_db
            if is_db_configured():
                save_notified_keys_to_db(keys)
                print(f"Successfully saved {len(keys)} notified keys to Neon database.")
        except Exception as e:
            print(f"Note: database seen sync save skipped: {e}")

    def save(self):
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(sorted(list(self.seen_keys)), f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving state {self.filepath}: {e}")
