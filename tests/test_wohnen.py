import unittest
from unittest.mock import patch
import sys

sys.path.append('.')
from src.scrapers.wohnen import scrape_wohnen
from src.models import Apartment

class TestWohnenScraper(unittest.TestCase):

    @patch('src.scrapers.wohnen.fetch_html')
    def test_scrape_wohnen_success(self, mock_fetch):
        # We need two levels of fetch_html:
        # First call is the main URL. We'll return project links.
        # Subsequent calls are the project URLs. We'll return the details rows.
        
        main_html = """
        <html>
        <body>
            <div class="listings">
                <a href="/immobilienangebot/genossenschaftswohnung/schumanngasse-64-1170-wien/">Link 1</a>
                <a href="/immobilienangebot/genossenschaftswohnung/other-project-1220-wien/">Link 2</a>
            </div>
        </body>
        </html>
        """

        project_html_1 = """
        <html>
        <body>
            <h1>Schumanngasse 64</h1>
            <table>
                <tr class="app-RealtyListBlock-row">
                    <td class="app-RealtyListBlock-cell--TopNumber">3</td>
                    <td class="app-RealtyListBlock-cell--RoomCount">2 Zimmer</td>
                    <td class="app-RealtyListBlock-cell--Area">58,0 m²</td>
                    <td class="app-RealtyListBlock-cell--TotalRent">€ 680,00</td>
                    <td><a href="/bestandseinheiten/schumann-top3">Details</a></td>
                </tr>
            </table>
        </body>
        </html>
        """

        project_html_2 = """
        <html>
        <body>
            <h1>Other Project</h1>
            <table>
                <tr class="app-RealtyListBlock-row">
                    <td class="app-RealtyListBlock-cell--TopNumber">12</td>
                    <td class="app-RealtyListBlock-cell--RoomCount">3 Zimmer</td>
                    <td class="app-RealtyListBlock-cell--Area">74,50 m²</td>
                    <td class="app-RealtyListBlock-cell--TotalRent">€ 890,00</td>
                    <td><a href="/bestandseinheiten/other-top12">Details</a></td>
                </tr>
            </table>
        </body>
        </html>
        """

        # Set side_effect of mock_fetch to handle main page and subsequent project details page fetches
        mock_fetch.side_effect = lambda url: {
            "https://www.wohnen.at/immobilienangebot/genossenschaftswohnung/filter/v1-mt:rent-oc:residential/": main_html,
            "https://www.wohnen.at/immobilienangebot/genossenschaftswohnung/schumanngasse-64-1170-wien/": project_html_1,
            "https://www.wohnen.at/immobilienangebot/genossenschaftswohnung/other-project-1220-wien/": project_html_2,
        }.get(url, None)

        results = scrape_wohnen()
        self.assertEqual(len(results), 2)

        # Verify first item
        apt1 = results[0]
        self.assertEqual(apt1.source, "Wohnen.at")
        self.assertEqual(apt1.listing_id, "schumann-top3")
        self.assertEqual(apt1.title, "Schumanngasse 64 - Top 3")
        self.assertEqual(apt1.location, "1170 Wien")
        self.assertEqual(apt1.price, 680.0)
        self.assertEqual(apt1.size_sqm, 58.0)
        self.assertEqual(apt1.rooms, 2)

        # Verify second item
        apt2 = results[1]
        self.assertEqual(apt2.source, "Wohnen.at")
        self.assertEqual(apt2.listing_id, "other-top12")
        self.assertEqual(apt2.title, "Other Project - Top 12")
        self.assertEqual(apt2.location, "1220 Wien")
        self.assertEqual(apt2.price, 890.0)
        self.assertEqual(apt2.size_sqm, 74.5)
        self.assertEqual(apt2.rooms, 3)

    @patch('src.scrapers.wohnen.fetch_html')
    def test_scrape_wohnen_empty(self, mock_fetch):
        mock_fetch.return_value = None
        results = scrape_wohnen()
        self.assertEqual(results, [])

if __name__ == '__main__':
    unittest.main()
