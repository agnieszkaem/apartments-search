import unittest
from unittest.mock import patch
import sys

sys.path.append('.')
from src.scrapers.oesw import scrape_oesw, parse_price
from src.models import Apartment

class TestOESWScraper(unittest.TestCase):

    def test_parse_price(self):
        self.assertEqual(parse_price("1.234,50"), 1234.5)
        self.assertEqual(parse_price("452,02"), 452.02)
        self.assertEqual(parse_price("1200"), 1200.0)
        self.assertEqual(parse_price("invalid"), 0.0)

    @patch('src.scrapers.oesw.fetch_html')
    def test_scrape_oesw_success(self, mock_fetch):
        # 1. Main Page HTML containing:
        # - A Vienna project (1030 Wien, Leopold-Böhm-Straße)
        # - A non-Vienna project (2320 Schwechat, Lanzendorf)
        main_html = """
        <html>
        <body>
            <li data-objlist-url="/immobilienangebot/sofort-wohnen/mhimmo/Wohnhaus/1030-wien-leopold-boehm-strasse-5-1.html?type=1338&amp;cHash=206edb8f103d6f1ea6406f8612e0b338">
                <a href="/immobilienangebot/projektdetail/mhimmo/anzeigen/Wohnhaus/1030-wien-leopold-boehm-strasse-5-1.html"></a>
            </li>
            <li data-objlist-url="/immobilienangebot/sofort-wohnen/mhimmo/Wohnhaus/2320-schwechat-lanzendorf-gasse.html?type=1338&amp;cHash=abcd1234">
                <a href="/immobilienangebot/projektdetail/mhimmo/anzeigen/Wohnhaus/2320-schwechat-lanzendorf-gasse.html"></a>
            </li>
        </body>
        </html>
        """

        # 2. Sub-page JSON content for Vienna project
        sub_page_json = """
        {
            "success": true,
            "count": 1,
            "content": "\\n <li class=\\\"flat-row\\\">\\n <a href=\\\"/immobilienangebot/objektdetail/mhimmo/anzeigen/Wohnung.html?tx_mhimmo_pi1%5BerpId%5D=mock-id-123&amp;cHash=mockhash\\\">\\n <h4>Stock 21 &bull; Top 319</h4>\\n <div class=\\\"desc-1\\\">pro Monat: € 757,75</div>\\n </a>\\n </li>\\n"
        }
        """

        # 3. Detail Page HTML for the individual flat
        detail_html = """
        <html>
        <body>
            <span class="adr-1">1030 Wien</span>
            <h2 class="adr-2">Leopold-Böhm-Straße 5</h2>
            <div><strong class="dark">Größe: </strong>47.57m<sup>2</sup></div>
            <div><strong class="dark">Zimmer: </strong>2</div>
            <div><strong class="dark">Kosten pro Monat: </strong>€ 757,75</div>
        </body>
        </html>
        """

        # Define side effects for fetch_html based on requested URLs
        def fetch_side_effect(url):
            if "sofort-wohnen.html" in url:
                return main_html
            elif "leopold-boehm-strasse" in url:
                return sub_page_json
            elif "objektdetail" in url:
                return detail_html
            return None

        mock_fetch.side_effect = fetch_side_effect

        results = scrape_oesw()

        # Check results
        # Should filter out Schwechat/Lanzendorf project before querying its sub-page
        self.assertEqual(len(results), 1)

        apt = results[0]
        self.assertEqual(apt.source, "ÖSW")
        self.assertEqual(apt.listing_id, "mock-id-123")
        self.assertEqual(apt.title, "Leopold-Böhm-Straße 5, Stock 21, Top 319")
        self.assertEqual(apt.location, "1030 Wien")
        self.assertEqual(apt.price, 757.75)
        self.assertEqual(apt.size_sqm, 47.57)
        self.assertEqual(apt.rooms, 2)
        self.assertEqual(apt.url, "https://www.oesw.at/immobilienangebot/objektdetail/mhimmo/anzeigen/Wohnung.html?tx_mhimmo_pi1%5BerpId%5D=mock-id-123&cHash=mockhash")

    @patch('src.scrapers.oesw.fetch_html')
    def test_scrape_oesw_empty(self, mock_fetch):
        mock_fetch.return_value = None
        results = scrape_oesw()
        self.assertEqual(results, [])

if __name__ == '__main__':
    unittest.main()
