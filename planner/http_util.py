"""Small HTTP helper. Stdlib only."""

import urllib.error
import urllib.parse
import urllib.request

from planner.config import USER_AGENT


class FetchError(Exception):
    """A page or API could not be read."""


def _ascii_url(url: str) -> str:
    """Encode spaces and punctuation so the request line stays ASCII."""
    parts = urllib.parse.urlsplit(url)
    path = urllib.parse.quote(parts.path, safe="/%")
    query = urllib.parse.quote(parts.query, safe="=&?/%")
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, path, query, ""))


def get_text(url: str, timeout: float = 20) -> str:
    request = urllib.request.Request(
        _ascii_url(url),
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            charset = response.headers.get_content_charset() or "utf-8"
            return raw.decode(charset, "replace")
    except urllib.error.HTTPError as exc:
        raise FetchError(f"{url} returned HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise FetchError(f"{url} could not be reached ({exc.reason})") from exc
    except TimeoutError as exc:
        raise FetchError(f"{url} timed out") from exc
