import unittest
from unittest.mock import patch
import sys

sys.path.append('.')
from src.scrapers.oevw import scrape_oevw
from src.models import Apartment

class TestOevwScraper(unittest.TestCase):

    @patch('src.scrapers.oevw.fetch_html')
    def test_scrape_oevw_success(self, mock_fetch):
        # We mock fetch_html to return search results for the pages
        mock_html = """
        <html>
        <body>
            <ul>
                <li class="thumblist__item">
                    <div class="thumb__heading">Erstbezug am Donaukanal</div>
                    <div class="thumb__info small">1030 Wien</div>
                    <div class="specs">
                        <span>60 m²</span>
                        <span>2 Zimmer</span>
                        <span>€ 750,00</span>
                    </div>
                    <a href="/suche/10552" class="stretched-link">Details</a>
                </li>
                <li class="thumblist__item">
                    <div class="thumb__heading">Dachgeschosswohnung mit Domblick</div>
                    <div class="thumb__info small">1010 Wien</div>
                    <div class="specs">
                        <span>95 m²</span>
                        <span>3 Zimmer</span>
                        <span>€ 1.250,00</span>
                    </div>
                    <a href="/suche/30911" class="stretched-link">Details</a>
                </li>
            </ul>
        </body>
        </html>
        """
        # Return mock html for page 1, empty for others
        mock_fetch.side_effect = lambda url: mock_html if "suche" in url and "page" not in url else None

        results = scrape_oevw()
        # Pages 1 to 5 are scraped in parallel. Page 1 returns 2 listings, others return empty.
        # So we expect 2 total listings.
        self.assertEqual(len(results), 2)

        # Verify first item
        apt1 = results[0]
        self.assertEqual(apt1.source, "OeVW")
        self.assertEqual(apt1.listing_id, "10552")
        self.assertEqual(apt1.title, "Erstbezug am Donaukanal")
        self.assertEqual(apt1.location, "1030 Wien")
        self.assertEqual(apt1.price, 750.0)
        self.assertEqual(apt1.size_sqm, 60.0)
        self.assertEqual(apt1.rooms, 2)

        # Verify second item
        apt2 = results[1]
        self.assertEqual(apt2.source, "OeVW")
        self.assertEqual(apt2.listing_id, "30911")
        self.assertEqual(apt2.title, "Dachgeschosswohnung mit Domblick")
        self.assertEqual(apt2.location, "1010 Wien")
        self.assertEqual(apt2.price, 1250.0)
        self.assertEqual(apt2.size_sqm, 95.0)
        self.assertEqual(apt2.rooms, 3)

    @patch('src.scrapers.oevw.fetch_html')
    def test_scrape_oevw_empty(self, mock_fetch):
        mock_fetch.return_value = None
        results = scrape_oevw()
        self.assertEqual(results, [])

if __name__ == '__main__':
    unittest.main()
