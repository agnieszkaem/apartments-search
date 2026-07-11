import unittest
from unittest.mock import patch
import sys

sys.path.append('.')
from src.scrapers.gesiba import scrape_gesiba
from src.models import Apartment

class TestGesibaScraper(unittest.TestCase):

    @patch('src.scrapers.gesiba.fetch_html')
    def test_scrape_gesiba_success(self, mock_fetch):
        # GESIBA html representation
        mock_html = """
        <html>
        <body>
            <div class="row">
                <a href="/immobilien/wohnungen/objekt?objektnummer=9912" class="card">
                    <h3 class="card-title">Genossenschaftswohnung nahe Kurpark Oberlaa</h3>
                    <p>1100 Wien</p>
                    <span>65,2 m²</span>
                    <span>2 Zimmer</span>
                    <span>ab € 724,50</span>
                </a>
                <a href="/immobilien/wohnungen/objekt?objektnummer=8843" class="card">
                    <h3 class="card-title">Sonnige 3-Zimmer Wohnung mit Balkon</h3>
                    <p>1220 Wien</p>
                    <span>82,0 m²</span>
                    <span>3 Zimmer</span>
                    <span>ab € 945,00</span>
                </a>
            </div>
        </body>
        </html>
        """
        mock_fetch.return_value = mock_html

        results = scrape_gesiba()
        self.assertEqual(len(results), 2)
        
        # Verify first item
        apt1 = results[0]
        self.assertEqual(apt1.source, "GESIBA")
        self.assertEqual(apt1.listing_id, "9912")
        self.assertEqual(apt1.title, "Genossenschaftswohnung nahe Kurpark Oberlaa")
        self.assertEqual(apt1.location, "1100 Wien")
        self.assertEqual(apt1.price, 724.50)
        self.assertEqual(apt1.size_sqm, 65.2)
        self.assertEqual(apt1.rooms, 2)
        self.assertEqual(apt1.url, "https://www.gesiba.at/immobilien/wohnungen/objekt?objektnummer=9912")

        # Verify second item
        apt2 = results[1]
        self.assertEqual(apt2.source, "GESIBA")
        self.assertEqual(apt2.listing_id, "8843")
        self.assertEqual(apt2.title, "Sonnige 3-Zimmer Wohnung mit Balkon")
        self.assertEqual(apt2.location, "1220 Wien")
        self.assertEqual(apt2.price, 945.00)
        self.assertEqual(apt2.size_sqm, 82.0)
        self.assertEqual(apt2.rooms, 3)
        self.assertEqual(apt2.url, "https://www.gesiba.at/immobilien/wohnungen/objekt?objektnummer=8843")

    @patch('src.scrapers.gesiba.fetch_html')
    def test_scrape_gesiba_empty_or_fail(self, mock_fetch):
        # Test empty HTML return
        mock_fetch.return_value = None
        results = scrape_gesiba()
        self.assertEqual(results, [])

        # Test no cards matched
        mock_fetch.return_value = "<html><body>No apartments here!</body></html>"
        results = scrape_gesiba()
        self.assertEqual(results, [])

if __name__ == '__main__':
    unittest.main()
