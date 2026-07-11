from dataclasses import dataclass, asdict
from typing import Optional

@dataclass
class Apartment:
    source: str
    listing_id: str
    title: str
    location: str
    price: float
    size_sqm: float
    rooms: int
    url: str
    available_immediately: bool = True
    is_mock: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def stable_key(self) -> str:
        """
        Generates a stable duplicate rule key:
        1. Website listing ID if the site provides one.
        2. Otherwise a normalized URL.
        3. Otherwise a fallback fingerprint from title, location, price, and size.
        """
        if self.listing_id:
            return f"{self.source}:{self.listing_id}"
        if self.url:
            return self.url.strip().lower()
        # fallback fingerprint
        title_slug = self.title.replace(" ", "").lower()
        loc_slug = self.location.replace(" ", "").lower()
        return f"{self.source}:{title_slug}:{loc_slug}:{self.price}:{self.size_sqm}"
