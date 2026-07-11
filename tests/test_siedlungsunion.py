import unittest
from unittest.mock import patch
import sys

sys.path.append('.')
from src.scrapers.siedlungsunion import scrape_siedlungsunion
from src.models import Apartment

class TestSiedlungsUnionScraper(unittest.TestCase):

    @patch('src.scrapers.siedlungsunion.fetch_html')
    def test_scrape_siedlungsunion_success(self, mock_fetch):
        # Provide real-looking Siedlungs Union html representation
        mock_html = """
        <html>
        <body>
            <article class="uk-article uk-width-1-1 ">
                <div class="uk-width-1-1">
                    <div class="uk-grid settlers-estate">
                        <div class="uk-width-2-3">
                            <div class="uk-width-3-4">
                                <a href="/wohnen/sofort/1220-wien-langobardenstrasse-59-1-2-14">
                                    1220 Wien, Langobardenstrasse 59/1/2/14
                                </a>
                            </div>
                        </div>
                        <div class="uk-width-1-3 settlers-wohnen-properities">
                            <div class="uk-grid uk-text-center">
                                <div class="uk-width-2-10">
                                    <i class="uk-icon-key"></i>
                                    <div class="uk-text-bold">1 Zimmer</div>
                                </div>
                                <div class="uk-width-4-10">
                                    <i class="uk-icon-arrows-h"></i>
                                    <div class="uk-text-bold">48.06 m<sup>2</sup></div>
                                </div>
                                <div class="uk-width-4-10">
                                    <i class="uk-icon-money"></i>
                                    <div class="uk-text-bold">452.02 <i class="uk-icon-euro"></i></div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </article>
            <article class="uk-article uk-width-1-1 ">
                <div class="uk-width-1-1">
                    <div class="uk-grid settlers-estate">
                        <div class="uk-width-2-3">
                            <div class="uk-width-3-4">
                                <a href="/wohnen/sofort/1100-wien-leibnizgasse-68-2-eg-3">
                                    1100 Wien, Leibnizgasse 68/2/EG/3
                                </a>
                            </div>
                        </div>
                        <div class="uk-width-1-3 settlers-wohnen-properities">
                            <div class="uk-grid uk-text-center">
                                <div class="uk-width-2-10">
                                    <i class="uk-icon-key"></i>
                                    <div class="uk-text-bold">2 Zimmer</div>
                                </div>
                                <div class="uk-width-4-10">
                                    <i class="uk-icon-arrows-h"></i>
                                    <div class="uk-text-bold">76.45 m<sup>2</sup></div>
                                </div>
                                <div class="uk-width-4-10">
                                    <i class="uk-icon-money"></i>
                                    <div class="uk-text-bold">777.91 <i class="uk-icon-euro"></i></div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </article>
        </body>
        </html>
        """
        mock_fetch.return_value = mock_html

        results = scrape_siedlungsunion()
        self.assertEqual(len(results), 2)
        
        # Verify first item
        apt1 = results[0]
        self.assertEqual(apt1.source, "Siedlungs Union")
        self.assertEqual(apt1.listing_id, "1220-wien-langobardenstrasse-59-1-2-14")
        self.assertEqual(apt1.title, "Langobardenstrasse 59/1/2/14")
        self.assertEqual(apt1.location, "1220 Wien")
        self.assertEqual(apt1.price, 452.02)
        self.assertEqual(apt1.size_sqm, 48.06)
        self.assertEqual(apt1.rooms, 1)
        self.assertEqual(apt1.url, "https://www.siedlungsunion.at/wohnen/sofort/1220-wien-langobardenstrasse-59-1-2-14")

        # Verify second item
        apt2 = results[1]
        self.assertEqual(apt2.source, "Siedlungs Union")
        self.assertEqual(apt2.listing_id, "1100-wien-leibnizgasse-68-2-eg-3")
        self.assertEqual(apt2.title, "Leibnizgasse 68/2/EG/3")
        self.assertEqual(apt2.location, "1100 Wien")
        self.assertEqual(apt2.price, 777.91)
        self.assertEqual(apt2.size_sqm, 76.45)
        self.assertEqual(apt2.rooms, 2)
        self.assertEqual(apt2.url, "https://www.siedlungsunion.at/wohnen/sofort/1100-wien-leibnizgasse-68-2-eg-3")

    @patch('src.scrapers.siedlungsunion.fetch_html')
    def test_scrape_siedlungsunion_empty_or_fail(self, mock_fetch):
        # Test empty HTML return
        mock_fetch.return_value = None
        results = scrape_siedlungsunion()
        self.assertEqual(results, [])

        # Test no articles matched
        mock_fetch.return_value = "<html><body>No apartments here!</body></html>"
        results = scrape_siedlungsunion()
        self.assertEqual(results, [])

if __name__ == '__main__':
    unittest.main()
