import re
from typing import List
from src.models import Apartment
from src.config import Config

def apply_filters(apartments: List[Apartment], config: Config) -> List[Apartment]:
    filtered = []
    max_price = config.max_price
    min_size = config.min_size_sqm
    min_rooms = config.min_rooms
    loc_contains = config.location_contains
    immediate_only = config.immediate_only

    for apt in apartments:
        #  max price
        if max_price is not None and apt.price > max_price:
            continue
        
        #  min size
        if min_size is not None and apt.size_sqm < min_size:
            continue

        #  min rooms
        if min_rooms is not None and apt.rooms < min_rooms:
            continue

        #  location
        if loc_contains:
            # split by comma, pipe, or semicolon to support multiple target locations
            terms = [t.strip().lower() for t in re.split(r'[,|;]', loc_contains) if t.strip()]
            if terms:
                matched = False
                for term in terms:
                    #  handle "Wien" to avoid matching "Wiener Neustadt", "Wiener Neudorf", etc.
                    if term == "wien":
                        if re.search(r'\bwien\b', apt.location.lower()) or re.search(r'\bwien\b', apt.title.lower()):
                            matched = True
                            break
                    else:
                        if term in apt.location.lower() or term in apt.title.lower():
                            matched = True
                            break
                if not matched:
                    continue

        # immediate availability sofort verfuegbar
        if immediate_only and not apt.available_immediately:
            continue

        filtered.append(apt)

    return filtered
