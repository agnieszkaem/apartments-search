from typing import List
from src.models import Apartment

def deduplicate_listings(apartments: List[Apartment]) -> List[Apartment]:
    seen_keys = set()
    unique_apartments = []
    for apt in apartments:
        key = apt.stable_key
        if key not in seen_keys:
            seen_keys.add(key)
            unique_apartments.append(apt)
    return unique_apartments
