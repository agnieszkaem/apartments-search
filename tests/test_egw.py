import unittest
from unittest.mock import patch
import sys

sys.path.append('.')
from src.scrapers.egw import scrape_egw, parse_price
from src.models import Apartment

class TestEGWScraper(unittest.TestCase):

    def test_parse_price(self):
        self.assertEqual(parse_price("€ 1.234,50"), 1234.5)
        self.assertEqual(parse_price("452,02 m²"), 452.02)
        self.assertEqual(parse_price("1200"), 1200.0)
        self.assertEqual(parse_price("invalid"), 0.0)

    @patch('src.scrapers.egw.fetch_html')
    def test_scrape_egw_success(self, mock_fetch):
        # Page 1 Mock HTML with one listing
        page_1_html = """
        <html>
        <body>
            <li class="thumblist__item">
                <div class="thumb thumb--unit">
                    <div class="thumb__content">
                        <h2 class="h2 thumb__heading">
                            <a href="/suche/680-2-zimmer-wohnung-mit-balkon-top-11" class="thumb__headinglink">2-Zimmer-Wohnung mit Balkon, Top 11</a>
                        </h2>
                        <div class="thumb__subheading">Nikolaus Pacassi-Gasse 2-6 / Haus 2, 2700 Wiener Neustadt</div>
                        <div class="thumb__infos">
                            Nutzfläche: <strong>62,22 m²</strong><br>
                            Zimmer: <strong>2</strong><br>
                            Miete brutto: <strong>€ 704,43</strong>
                        </div>
                    </div>
                </div>
            </li>
        </body>
        </html>
        """
        
        # Page 2 Mock HTML (empty list) to stop the pagination loop
        page_2_html = "<html><body></body></html>"

        def fetch_side_effect(url):
            if "page=2" in url:
                return page_2_html
            else:
                return page_1_html

        mock_fetch.side_effect = fetch_side_effect

        results = scrape_egw()

        self.assertEqual(len(results), 1)
        apt = results[0]
        self.assertEqual(apt.source, "EGW")
        self.assertEqual(apt.listing_id, "680")
        self.assertEqual(apt.title, "2-Zimmer-Wohnung mit Balkon, Top 11")
        self.assertEqual(apt.location, "Nikolaus Pacassi-Gasse 2-6 / Haus 2, 2700 Wiener Neustadt")
        self.assertEqual(apt.price, 704.43)
        self.assertEqual(apt.size_sqm, 62.22)
        self.assertEqual(apt.rooms, 2)
        self.assertEqual(apt.url, "https://www.egw.at/suche/680-2-zimmer-wohnung-mit-balkon-top-11")

    @patch('src.scrapers.egw.fetch_html')
    def test_scrape_egw_empty(self, mock_fetch):
        mock_fetch.return_value = None
        results = scrape_egw()
        self.assertEqual(results, [])

if __name__ == '__main__':
    unittest.main()
