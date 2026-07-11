import unittest
from unittest.mock import patch
import sys

sys.path.append('.')
from src.scrapers.familienwohnbau import scrape_familienwohnbau, parse_price
from src.models import Apartment

class TestFamilienWohnbauScraper(unittest.TestCase):

    def test_parse_price(self):
        self.assertEqual(parse_price("1.234,50"), 1234.5)
        self.assertEqual(parse_price("452,02"), 452.02)
        self.assertEqual(parse_price("1200"), 1200.0)
        self.assertEqual(parse_price("invalid"), 0.0)

    @patch('src.scrapers.familienwohnbau.fetch_html')
    def test_scrape_familienwohnbau_success(self, mock_fetch):
        #  Familien Wohnbau HTML
        mock_html = """
        <html>
        <body>
            <div id="listings">
                <!-- Listing 1: Standard Individual Apartment -->
                <a href="/de/objekt/einen-katzensprung-von-wien-entfernt-miete-6d13da86" class="bg-white shadow-md border-t">
                    <div class="flex flex-col">
                        <div class="p-4 border-t border-gray-200">
                            <p class="uppercase tracking-wide text-sm font-bold text-gray-700">
                                einen Katzensprung von Wien entfernt MIETE
                            </p>
                            <p class="text-gray-700 pt-1">
                                2326 Lanzendorf, Untere Hauptstraße 11
                            </p>
                            <p class="text-2xl text-primary italic font-semibold pt-3">
                                € 1.760,67
                            </p>
                        </div>
                    </div>
                    <div class="flex p-4">
                        <div class="flex lg:flex-row flex-col">
                            <div class="flex-1 inline-flex items-center py-2">
                                <span class="text-gray-900">4</span> Zimmer
                            </div>
                            <div class="flex-1 inline-flex items-center py-2">
                                <span class="text-gray-900">116,19</span> m²
                            </div>
                        </div>
                    </div>
                </a>

                <!-- Listing 2: Project Summary Card (Rent) -->
                <a href="/de/objekt/1130-wien-auhofstrasse-196-miete-cbe10780" class="bg-white shadow-md border-t">
                    <div class="flex flex-col">
                        <div class="p-4 border-t border-gray-200">
                            <p class="uppercase tracking-wide text-sm font-bold text-gray-700">
                                1130 Wien Auhofstraße 196 MIETE
                            </p>
                            <p class="text-2xl text-primary italic font-semibold pt-3">
                                € 1.120,89 bis € 1.226,62
                            </p>
                        </div>
                    </div>
                    <div class="flex p-4">
                        <div class="flex-1 inline-flex items-center py-2">
                            <span class="text-gray-900">Anzahl der Einheiten: 5</span>
                        </div>
                    </div>
                </a>

                <!-- Listing 3: Excluded Garage Space -->
                <a href="/de/objekt/garagenplatz-1230-wien-a23838b5" class="bg-white shadow-md border-t">
                    <div class="flex flex-col">
                        <div class="p-4 border-t border-gray-200">
                            <p class="uppercase tracking-wide text-sm font-bold text-gray-700">
                                Garagenplatz 1230 Wien MIETE
                            </p>
                            <p class="text-2xl text-primary italic font-semibold pt-3">
                                € 90,00
                            </p>
                        </div>
                    </div>
                </a>

                <!-- Listing 4: Purchase Property (No Miete) -->
                <a href="/de/objekt/zu-hause-direkt-an-der-u3-ce2e3883" class="bg-white shadow-md border-t">
                    <div class="flex flex-col">
                        <div class="p-4 border-t border-gray-200">
                            <p class="uppercase tracking-wide text-sm font-bold text-gray-700">
                                Zu Hause direkt an der U3
                            </p>
                            <p class="text-gray-700 pt-1">
                                1110 Wien, Simmeringer Hauptstraße 153--155
                            </p>
                            <p class="text-2xl text-primary italic font-semibold pt-3">
                                € 477.000,00
                            </p>
                        </div>
                    </div>
                </a>
            </div>
        </body>
        </html>
        """
        mock_fetch.return_value = mock_html
        
        results = scrape_familienwohnbau()
        
        # Verify result counts (should exclude Lanzendorf via postcode, garages, purchase properties; include standard rentals with valid prices)
        self.assertEqual(len(results), 1)
        
        # Verify the only matched item (Vienna listing)
        apt = results[0]
        self.assertEqual(apt.source, "Familien Wohnbau")
        self.assertEqual(apt.listing_id, "1130-wien-auhofstrasse-196-miete-cbe10780")
        self.assertEqual(apt.title, "1130 Wien Auhofstraße 196 MIETE")
        self.assertEqual(apt.location, "1130 Wien")
        self.assertEqual(apt.price, 1120.89)
        self.assertEqual(apt.rooms, 2)
        self.assertEqual(apt.size_sqm, 55.0)

    @patch('src.scrapers.familienwohnbau.fetch_html')
    def test_scrape_familienwohnbau_empty(self, mock_fetch):
        mock_fetch.return_value = ""
        results = scrape_familienwohnbau()
        self.assertEqual(len(results), 0)

if __name__ == '__main__':
    unittest.main()
