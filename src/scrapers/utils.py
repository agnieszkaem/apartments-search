import sys
import urllib.request
import urllib.error
from typing import Optional

def fetch_html(url: str) -> Optional[str]:
    """
    Fetches the HTML of a URL.
    Tries to use `requests` first if installed, falls back to standard `urllib.request`.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        import requests
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            return response.text
        else:
            print(f"requests fetch returned status code {response.status_code}", file=sys.stderr)
    except ImportError:
        pass
    except Exception as e:
        print(f"requests fetch error: {e}", file=sys.stderr)

    # Fallback to standard urllib
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            return response.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        print(f"urllib HTTP error fetching {url}: {e.code} {e.reason}", file=sys.stderr)
    except urllib.error.URLError as e:
        print(f"urllib network error fetching {url}: {e.reason}", file=sys.stderr)
    except Exception as e:
        print(f"urllib generic error fetching {url}: {e}", file=sys.stderr)

    return None
