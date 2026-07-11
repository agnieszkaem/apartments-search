import unittest
from unittest.mock import patch, MagicMock
import os
import sys

sys.path.append('.')
from src.scrapers.sozialbau import scrape_sozialbau
from src.models import Apartment

class TestSozialbauScraper(unittest.TestCase):

    @patch('urllib.request.urlopen')
    @patch.dict(os.environ, {
        "SOZIALBAU_JSESSIONID": "MOCK_SESSION_ID",
        "SOZIALBAU_SERVERID": "MOCK_SERVER_ID"
    })
    def test_scrape_sozialbau_success(self, mock_urlopen):
        # Setup mock home page response (first call)
        mock_home_html = """
        <html>
        <head></head>
        <body>
            <form id="menuform">
                <input type="hidden" name="javax.faces.ViewState" value="mock_view_state" />
                <a onclick="PrimeFaces.ab({s:&quot;menuform:j_idt36&quot;,f:&quot;menuform&quot;});return false;">Sofort vergebbar</a>
            </form>
        </body>
        </html>
        """

        # Setup mock XML response (second call)
        mock_xml_response = """<?xml version='1.0' encoding='UTF-8'?>
        <partial-response>
            <changes>
                <update id="f1:ajax-main"><![CDATA[
                    <div>
                        <strong>1170 Wien, Schumanngasse 64</strong>
                        <p>Größe: 58,0 m² | 2 Zimmer Miete: € 680,00</p>
                    </div>
                    <div>
                        <strong>1220 Wien, Dückegasse 11</strong>
                        <p>Größe: 74,5 m² | 3 Zimmer Miete: € 890,00</p>
                    </div>
                ]]></update>
            </changes>
        </partial-response>
        """

        # Configure mock_urlopen to return these responses sequentially
        mock_conn1 = MagicMock()
        mock_conn1.read.return_value = mock_home_html.encode('utf-8')
        mock_conn1.__enter__.return_value = mock_conn1

        mock_conn2 = MagicMock()
        mock_conn2.read.return_value = mock_xml_response.encode('utf-8')
        mock_conn2.__enter__.return_value = mock_conn2

        mock_urlopen.side_effect = [mock_conn1, mock_conn2]

        results = scrape_sozialbau()
        self.assertEqual(len(results), 2)

        # Verify first item
        apt1 = results[0]
        self.assertEqual(apt1.source, "Sozialbau")
        self.assertEqual(apt1.listing_id, "sb-1170-schumanngasse-64")
        self.assertEqual(apt1.title, "Wohnung Schumanngasse 64")
        self.assertEqual(apt1.location, "1170 Wien")
        self.assertEqual(apt1.price, 680.0)
        self.assertEqual(apt1.size_sqm, 58.0)
        self.assertEqual(apt1.rooms, 2)

        # Verify second item
        apt2 = results[1]
        self.assertEqual(apt2.source, "Sozialbau")
        self.assertEqual(apt2.listing_id, "sb-1220-d-ckegasse-11") # 'ü' becomes non-alphanumeric and is replaced or kept
        self.assertEqual(apt2.title, "Wohnung Dückegasse 11")
        self.assertEqual(apt2.location, "1220 Wien")
        self.assertEqual(apt2.price, 890.0)
        self.assertEqual(apt2.size_sqm, 74.5)
        self.assertEqual(apt2.rooms, 3)

    @patch('urllib.request.urlopen')
    def test_scrape_sozialbau_no_cookies(self, mock_urlopen):
        # Clear cookies / session info from environment
        with patch.dict(os.environ, {}, clear=True):
            results = scrape_sozialbau()
            self.assertEqual(results, [])

    @patch('urllib.request.urlopen')
    @patch.dict(os.environ, {
        "SOZIALBAU_JSESSIONID": "MOCK_SESSION_ID",
        "SOZIALBAU_SERVERID": "MOCK_SERVER_ID"
    })
    def test_scrape_sozialbau_session_expired(self, mock_urlopen):
        # Return home page correctly but second call gets a login screen redirect inside update
        mock_home_html = """
        <html>
        <body>
            <input type="hidden" name="javax.faces.ViewState" value="mock_view_state" />
            <a onclick="PrimeFaces.ab({s:&quot;menuform:j_idt36&quot;,f:&quot;menuform&quot;});return false;">sofort</a>
        </body>
        </html>
        """

        mock_xml_expired = """<?xml version='1.0' encoding='UTF-8'?>
        <partial-response>
            <changes>
                <update id="f1:ajax-main"><![CDATA[
                    <div>
                        <h2>Anmeldung</h2>
                        <p>Damit Sie sich über unser Wohnungsangebot informieren zu können, müssen Sie angemeldet sein.</p>
                    </div>
                ]]></update>
            </changes>
        </partial-response>
        """

        mock_conn1 = MagicMock()
        mock_conn1.read.return_value = mock_home_html.encode('utf-8')
        mock_conn1.__enter__.return_value = mock_conn1

        mock_conn2 = MagicMock()
        mock_conn2.read.return_value = mock_xml_expired.encode('utf-8')
        mock_conn2.__enter__.return_value = mock_conn2

        mock_urlopen.side_effect = [mock_conn1, mock_conn2]

        results = scrape_sozialbau()
        self.assertEqual(results, [])

if __name__ == '__main__':
    unittest.main()
