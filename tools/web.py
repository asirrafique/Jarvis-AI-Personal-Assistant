"""
Jarvis Web Tools
================

Safe web-search and URL-opening tools.

Public tools:
    search_web(query, max_results=5)
    open_url(url)
"""

from __future__ import annotations

import logging
import re
import webbrowser
from html import unescape
from html.parser import HTMLParser
from typing import Any, Dict
from urllib.parse import parse_qs, unquote, urlparse

import requests


logger = logging.getLogger("jarvis.web")


# ============================================================
# CONFIGURATION
# ============================================================

DEFAULT_TIMEOUT = 10
MAX_RESULTS = 10

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 "
    "(KHTML, like Gecko) "
    "Chrome/151.0.0.0 Safari/537.36"
)

SEARCH_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": (
        "text/html,"
        "application/xhtml+xml,"
        "application/xml;q=0.9,"
        "*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}


# ============================================================
# TEXT HELPERS
# ============================================================

def _clean_html_text(text: str) -> str:
    """Normalize extracted HTML text."""

    if not isinstance(text, str):
        return ""

    text = unescape(text)

    # Remove remaining HTML tags.
    text = re.sub(r"<[^>]+>", " ", text)

    # Normalize whitespace.
    text = re.sub(r"\s+", " ", text)

    return text.strip()


# ============================================================
# URL HELPERS
# ============================================================

def _clean_url(url: str) -> str:
    """
    Normalize common URL formatting.

    Supports:

        https://example.com
        https\\://example.com
        [https://example.com](https://example.com)
        <https://example.com>
        "https://example.com"
    """

    if not isinstance(url, str):
        return ""

    url = unescape(url).strip()

    if not url:
        return ""

    # Fix LLM escaping.
    url = url.replace(r"\:", ":")
    url = url.replace(r"\_", "_")

    # Markdown:
    # [label](https://example.com)
    match = re.match(
        r"^\[[^\]]*\]\((https?://.+?)\)$",
        url,
        flags=re.IGNORECASE,
    )

    if match:
        url = match.group(1).strip()

    # Generic markdown URL.
    match = re.match(
        r"^\[[^\]]+\]\((.+?)\)$",
        url,
        flags=re.IGNORECASE,
    )

    if match:
        candidate = match.group(1).strip()

        if candidate.lower().startswith(
            ("http://", "https://")
        ):
            url = candidate

    # Angle brackets.
    if url.startswith("<") and url.endswith(">"):
        url = url[1:-1].strip()

    # Quotes.
    if len(url) >= 2 and url[0] in {"'", '"'}:
        if url[-1] == url[0]:
            url = url[1:-1].strip()

    # Remove surrounding whitespace.
    return url.strip()


def _is_valid_http_url(url: str) -> bool:
    """Return True only for valid HTTP/HTTPS URLs."""

    if not isinstance(url, str):
        return False

    url = _clean_url(url)

    if not url:
        return False

    try:
        parsed = urlparse(url)
    except Exception:
        return False

    return (
        parsed.scheme.lower() in {"http", "https"}
        and bool(parsed.netloc)
    )


def _extract_redirect_url(url: str) -> str:
    """
    Extract destination URLs from common search-engine
    redirect URLs.
    """

    if not isinstance(url, str):
        return ""

    url = unescape(url).strip()

    if not url:
        return ""

    # Protocol-relative URL.
    if url.startswith("//"):
        url = "https:" + url

    # Decode repeatedly.
    for _ in range(3):
        decoded = unquote(url)

        if decoded == url:
            break

        url = decoded

    try:
        parsed = urlparse(url)
    except Exception:
        return _clean_url(url)

    query = parse_qs(parsed.query)

    redirect_keys = (
        "uddg",
        "url",
        "u",
        "target",
        "dest",
        "destination",
        "redirect",
        "redirect_url",
    )

    for key in redirect_keys:
        values = query.get(key)

        if not values:
            continue

        candidate = values[0]

        if _is_valid_http_url(candidate):
            return _clean_url(candidate)

    return _clean_url(url)


# ============================================================
# SEARCH URL FILTERING
# ============================================================

SEARCH_ENGINE_HOSTS = {
    "google.com",
    "www.google.com",
    "bing.com",
    "www.bing.com",
    "search.yahoo.com",
    "yahoo.com",
    "www.yahoo.com",
    "duckduckgo.com",
    "www.duckduckgo.com",
    "html.duckduckgo.com",
    "lite.duckduckgo.com",
}


def _is_search_engine_url(url: str) -> bool:
    """Reject search-engine/navigation URLs."""

    if not _is_valid_http_url(url):
        return True

    try:
        hostname = (
            urlparse(_clean_url(url))
            .netloc
            .lower()
            .split(":")[0]
        )
    except Exception:
        return True

    return hostname in SEARCH_ENGINE_HOSTS


# ============================================================
# CHALLENGE DETECTION
# ============================================================

def _is_challenge_response(
    response: requests.Response,
) -> bool:
    """Detect common anti-bot/challenge responses."""

    try:
        status = response.status_code
    except Exception:
        return False

    if status in {202, 403, 429}:
        return True

    try:
        text = response.text.lower()
    except Exception:
        return False

    markers = (
        "challenge-form",
        "anomaly.js",
        "captcha",
        "are you a robot",
        "unusual traffic",
        "verify you are human",
        "bot detection",
        "automated queries",
        "sorry/index",
    )

    return any(
        marker in text
        for marker in markers
    )


# ============================================================
# RESULT NORMALIZATION
# ============================================================

def _normalize_result(
    title: str,
    url: str,
    snippet: str = "",
) -> Dict[str, str] | None:
    """Normalize one search result."""

    title = _clean_html_text(title)
    url = _extract_redirect_url(url)
    snippet = _clean_html_text(snippet)

    if not title:
        return None

    if not _is_valid_http_url(url):
        return None

    if _is_search_engine_url(url):
        return None

    return {
        "title": title,
        "url": url,
        "snippet": snippet,
    }


def _deduplicate_results(
    results: list[Dict[str, str]],
    max_results: int,
) -> list[Dict[str, str]]:
    """Remove invalid and duplicate URLs."""

    output: list[Dict[str, str]] = []
    seen: set[str] = set()

    for result in results:

        if not isinstance(result, dict):
            continue

        url = _clean_url(
            result.get("url", "")
        )

        if not _is_valid_http_url(url):
            continue

        if _is_search_engine_url(url):
            continue

        key = url.rstrip("/").lower()

        if key in seen:
            continue

        seen.add(key)

        normalized = {
            "title": _clean_html_text(
                result.get("title", "")
            ),
            "url": url,
            "snippet": _clean_html_text(
                result.get("snippet", "")
            ),
        }

        if not normalized["title"]:
            continue

        output.append(normalized)

        if len(output) >= max_results:
            break

    return output


# ============================================================
# DUCKDUCKGO PARSER
# ============================================================

class _DuckDuckGoParser(HTMLParser):
    """Parser for DuckDuckGo HTML results."""

    def __init__(self) -> None:
        super().__init__()

        self.results: list[Dict[str, str]] = []

        self.current_url: str | None = None

        self.capture_title = False
        self.capture_snippet = False

        self.title_parts: list[str] = []
        self.snippet_parts: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:

        attributes = dict(attrs)

        classes = (
            attributes.get("class")
            or ""
        )

        class_list = set(
            classes.split()
        )

        # Result title.
        if (
            tag == "a"
            and "result__a" in class_list
        ):
            href = (
                attributes.get("href")
                or ""
            )

            href = _extract_redirect_url(href)

            if not _is_valid_http_url(href):
                return

            if _is_search_engine_url(href):
                return

            self.current_url = href
            self.title_parts = []
            self.capture_title = True

            return

        # Result snippet.
        if (
            self.current_url
            and "result__snippet" in class_list
        ):
            self.snippet_parts = []
            self.capture_snippet = True

    def handle_endtag(
        self,
        tag: str,
    ) -> None:

        if (
            self.capture_title
            and tag == "a"
        ):
            self.capture_title = False

            title = _clean_html_text(
                "".join(
                    self.title_parts
                )
            )

            if self.current_url:
                result = _normalize_result(
                    title=title,
                    url=self.current_url,
                    snippet="",
                )

                if result:
                    self.results.append(
                        result
                    )

            self.title_parts = []

            return

        if (
            self.capture_snippet
            and tag in {
                "div",
                "span",
                "a",
            }
        ):
            self.capture_snippet = False

            snippet = _clean_html_text(
                "".join(
                    self.snippet_parts
                )
            )

            if self.results:
                self.results[-1]["snippet"] = snippet

            self.snippet_parts = []

    def handle_data(
        self,
        data: str,
    ) -> None:

        if self.capture_title:
            self.title_parts.append(data)

        elif self.capture_snippet:
            self.snippet_parts.append(data)


def _parse_duckduckgo(
    html: str,
) -> list[Dict[str, str]]:
    """Parse DuckDuckGo HTML."""

    if not isinstance(html, str):
        return []

    parser = _DuckDuckGoParser()

    try:
        parser.feed(html)
        parser.close()
    except Exception as exc:
        logger.warning(
            "DuckDuckGo parser error: %s",
            exc,
        )
        return []

    return parser.results


# ============================================================
# GOOGLE PARSER
# ============================================================

class _GoogleParser(HTMLParser):
    """Lightweight Google result parser."""

    def __init__(self) -> None:
        super().__init__()

        self.results: list[Dict[str, str]] = []

        self.current_href: str | None = None

        self.capture_title = False
        self.capture_snippet = False

        self.title_parts: list[str] = []
        self.snippet_parts: list[str] = []

        self.title_depth = 0
        self.snippet_depth = 0

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:

        attributes = dict(attrs)

        href = (
            attributes.get("href")
            or ""
        )

        classes = (
            attributes.get("class")
            or ""
        )

        class_list = set(
            classes.split()
        )

        # Anchor URL.
        if tag == "a" and href:

            cleaned = _extract_redirect_url(
                href
            )

            if (
                _is_valid_http_url(cleaned)
                and not _is_search_engine_url(cleaned)
            ):
                self.current_href = cleaned

        # Google commonly uses h3 for result titles.
        if tag == "h3":

            self.capture_title = True
            self.title_depth = 1
            self.title_parts = []

            return

        # Additional title selectors.
        if (
            tag in {"div", "span"}
            and class_list.intersection(
                {
                    "BNeawe",
                    "vvjwJb",
                }
            )
        ):
            self.capture_title = True
            self.title_depth = 1
            self.title_parts = []

        # Common snippet selectors.
        if (
            class_list.intersection(
                {
                    "VwiC3b",
                    "yXK7lf",
                    "IsZvec",
                    "aCOpRe",
                    "kb0PBd",
                }
            )
        ):
            self.capture_snippet = True
            self.snippet_depth = 1
            self.snippet_parts = []

    def handle_endtag(
        self,
        tag: str,
    ) -> None:

        if self.capture_title:

            if tag == "h3":
                self.capture_title = False

                title = _clean_html_text(
                    "".join(
                        self.title_parts
                    )
                )

                if (
                    title
                    and self.current_href
                ):
                    result = _normalize_result(
                        title=title,
                        url=self.current_href,
                        snippet="",
                    )

                    if result:
                        self.results.append(
                            result
                        )

                self.title_parts = []

        if self.capture_snippet:

            if tag in {
                "div",
                "span",
            }:
                self.capture_snippet = False

                snippet = _clean_html_text(
                    "".join(
                        self.snippet_parts
                    )
                )

                if (
                    snippet
                    and self.results
                ):
                    self.results[-1][
                        "snippet"
                    ] = snippet

                self.snippet_parts = []

    def handle_data(
        self,
        data: str,
    ) -> None:

        if self.capture_title:
            self.title_parts.append(data)

        elif self.capture_snippet:
            self.snippet_parts.append(data)


def _parse_google(
    html: str,
) -> list[Dict[str, str]]:
    """Parse Google search HTML."""

    if not isinstance(html, str):
        return []

    parser = _GoogleParser()

    try:
        parser.feed(html)
        parser.close()
    except Exception as exc:
        logger.warning(
            "Google parser error: %s",
            exc,
        )
        return []

    return parser.results


# ============================================================
# BING PARSER
# ============================================================

class _BingParser(HTMLParser):
    """
    Parser for Bing HTML search results.

    Bing commonly structures organic results as:

        li.b_algo
            h2
                a href="..."
    """

    def __init__(self) -> None:
        super().__init__()

        self.results: list[Dict[str, str]] = []

        self.current_url: str | None = None

        self.capture_title = False
        self.capture_snippet = False

        self.title_parts: list[str] = []
        self.snippet_parts: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:

        attributes = dict(attrs)

        classes = (
            attributes.get("class")
            or ""
        )

        class_list = set(
            classes.split()
        )

        # Bing organic result container.
        if (
            tag == "li"
            and "b_algo" in class_list
        ):
            self.current_url = None
            self.title_parts = []
            self.snippet_parts = []
            self.capture_title = False
            self.capture_snippet = False

        # Result link.
        if tag == "a":

            href = (
                attributes.get("href")
                or ""
            )

            href = _extract_redirect_url(
                href
            )

            if (
                _is_valid_http_url(href)
                and not _is_search_engine_url(href)
            ):
                self.current_url = href

        # Result title.
        if (
            tag == "h2"
            and self.current_url
        ):
            self.capture_title = True
            self.title_parts = []

        # Result snippet.
        if (
            tag in {"p", "div"}
            and self.current_url
            and class_list.intersection(
                {
                    "b_caption",
                    "b_algoSlug",
                }
            )
        ):
            self.capture_snippet = True
            self.snippet_parts = []

    def handle_endtag(
        self,
        tag: str,
    ) -> None:

        if (
            tag == "h2"
            and self.capture_title
        ):
            self.capture_title = False

            title = _clean_html_text(
                "".join(
                    self.title_parts
                )
            )

            if (
                title
                and self.current_url
            ):
                result = _normalize_result(
                    title=title,
                    url=self.current_url,
                    snippet="",
                )

                if result:
                    self.results.append(
                        result
                    )

            self.title_parts = []

        if (
            self.capture_snippet
            and tag in {"p", "div"}
        ):
            self.capture_snippet = False

            snippet = _clean_html_text(
                "".join(
                    self.snippet_parts
                )
            )

            if (
                snippet
                and self.results
            ):
                self.results[-1][
                    "snippet"
                ] = snippet

            self.snippet_parts = []

    def handle_data(
        self,
        data: str,
    ) -> None:

        if self.capture_title:
            self.title_parts.append(data)

        elif self.capture_snippet:
            self.snippet_parts.append(data)


def _parse_bing(
    html: str,
) -> list[Dict[str, str]]:
    """Parse Bing search HTML."""

    if not isinstance(html, str):
        return []

    parser = _BingParser()

    try:
        parser.feed(html)
        parser.close()
    except Exception as exc:
        logger.warning(
            "Bing parser error: %s",
            exc,
        )
        return []

    return parser.results


# ============================================================
# YAHOO PARSER
# ============================================================

class _YahooParser(HTMLParser):
    """Parser for Yahoo organic search results."""

    def __init__(self) -> None:
        super().__init__()

        self.results: list[Dict[str, str]] = []

        self.current_url: str | None = None

        self.capture_title = False
        self.title_parts: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:

        if tag != "a":
            return

        attributes = dict(attrs)

        href = (
            attributes.get("href")
            or ""
        )

        href = _extract_redirect_url(
            href
        )

        if not _is_valid_http_url(href):
            return

        if _is_search_engine_url(href):
            return

        self.current_url = href
        self.title_parts = []
        self.capture_title = True

    def handle_endtag(
        self,
        tag: str,
    ) -> None:

        if (
            tag == "a"
            and self.capture_title
        ):
            self.capture_title = False

            title = _clean_html_text(
                "".join(
                    self.title_parts
                )
            )

            if (
                title
                and self.current_url
            ):
                result = _normalize_result(
                    title=title,
                    url=self.current_url,
                    snippet="",
                )

                if result:
                    self.results.append(
                        result
                    )

            self.current_url = None
            self.title_parts = []

    def handle_data(
        self,
        data: str,
    ) -> None:

        if self.capture_title:
            self.title_parts.append(data)


def _parse_yahoo(
    html: str,
) -> list[Dict[str, str]]:
    """Parse Yahoo search HTML."""

    if not isinstance(html, str):
        return []

    parser = _YahooParser()

    try:
        parser.feed(html)
        parser.close()
    except Exception as exc:
        logger.warning(
            "Yahoo parser error: %s",
            exc,
        )
        return []

    return parser.results


# ============================================================
# HTTP REQUEST HELPER
# ============================================================

def _get_search_page(
    endpoint: str,
    params: Dict[str, Any],
) -> requests.Response | None:
    """Safely request a search page."""

    try:

        response = requests.get(
            endpoint,
            params=params,
            headers=SEARCH_HEADERS,
            timeout=DEFAULT_TIMEOUT,
        )

        if _is_challenge_response(
            response
        ):
            logger.warning(
                "Search challenge detected: %s HTTP %s",
                endpoint,
                response.status_code,
            )
            return None

        response.raise_for_status()

        return response

    except requests.RequestException as exc:

        logger.warning(
            "Search request failed for %s: %s",
            endpoint,
            exc,
        )

        return None


# ============================================================
# PROVIDER: DUCKDUCKGO
# ============================================================

def _search_duckduckgo(
    query: str,
    max_results: int,
) -> list[Dict[str, str]]:

    endpoints = (
        "https://html.duckduckgo.com/html/",
        "https://lite.duckduckgo.com/lite/",
    )

    for endpoint in endpoints:

        logger.info(
            "Trying DuckDuckGo: %s",
            query,
        )

        response = _get_search_page(
            endpoint,
            {"q": query},
        )

        if response is None:
            continue

        results = _parse_duckduckgo(
            response.text
        )

        results = _deduplicate_results(
            results,
            max_results,
        )

        if results:
            return results

    return []


# ============================================================
# PROVIDER: GOOGLE
# ============================================================

def _search_google(
    query: str,
    max_results: int,
) -> list[Dict[str, str]]:

    endpoint = "https://www.google.com/search"

    logger.info(
        "Trying Google: %s",
        query,
    )

    response = _get_search_page(
        endpoint,
        {
            "q": query,
            "num": max_results,
            "hl": "en",
            "filter": "0",
        },
    )

    if response is None:
        return []

    results = _parse_google(
        response.text
    )

    return _deduplicate_results(
        results,
        max_results,
    )


# ============================================================
# PROVIDER: BING
# ============================================================

def _search_bing(
    query: str,
    max_results: int,
) -> list[Dict[str, str]]:

    endpoint = "https://www.bing.com/search"

    logger.info(
        "Trying Bing: %s",
        query,
    )

    response = _get_search_page(
        endpoint,
        {
            "q": query,
            "count": max_results,
            "setlang": "en-US",
        },
    )

    if response is None:
        return []

    results = _parse_bing(
        response.text
    )

    return _deduplicate_results(
        results,
        max_results,
    )


# ============================================================
# PROVIDER: YAHOO
# ============================================================

def _search_yahoo(
    query: str,
    max_results: int,
) -> list[Dict[str, str]]:

    endpoint = "https://search.yahoo.com/search"

    logger.info(
        "Trying Yahoo: %s",
        query,
    )

    response = _get_search_page(
        endpoint,
        {
            "p": query,
        },
    )

    if response is None:
        return []

    results = _parse_yahoo(
        response.text
    )

    return _deduplicate_results(
        results,
        max_results,
    )


# ============================================================
# PUBLIC SEARCH TOOL
# ============================================================

def search_web(
    query: str,
    max_results: int = 5,
) -> Dict[str, Any]:
    """
    Search the public web.

    Provider order:

        1. DuckDuckGo
        2. Google
        3. Bing
        4. Yahoo

    The first provider that returns usable results wins.
    """

    # --------------------------------------------------------
    # Validate query
    # --------------------------------------------------------

    if not isinstance(query, str):
        return {
            "success": False,
            "error": "Search query must be a string.",
        }

    query = query.strip()

    if not query:
        return {
            "success": False,
            "error": "Search query is required.",
        }

    # --------------------------------------------------------
    # Normalize max_results
    # --------------------------------------------------------

    try:
        max_results = int(
            max_results
        )
    except (
        TypeError,
        ValueError,
    ):
        max_results = 5

    max_results = max(
        1,
        min(
            max_results,
            MAX_RESULTS,
        ),
    )

    # --------------------------------------------------------
    # Provider chain
    # --------------------------------------------------------

    providers = [
        (
            "DuckDuckGo",
            _search_duckduckgo,
        ),
        (
            "Google",
            _search_google,
        ),
        (
            "Bing",
            _search_bing,
        ),
        (
            "Yahoo",
            _search_yahoo,
        ),
    ]

    provider_errors: list[str] = []

    for provider_name, provider in providers:

        try:

            logger.info(
                "Searching with %s: %s",
                provider_name,
                query,
            )

            results = provider(
                query,
                max_results,
            )

            if results:

                logger.info(
                    "%s returned %d result(s).",
                    provider_name,
                    len(results),
                )

                return {
                    "success": True,
                    "query": query,
                    "count": len(results),
                    "results": results,
                    "provider": provider_name,
                }

            provider_errors.append(
                f"{provider_name}: no usable results"
            )

        except Exception as exc:

            logger.warning(
                "%s provider failed: %s",
                provider_name,
                exc,
            )

            provider_errors.append(
                f"{provider_name}: {exc}"
            )

    # --------------------------------------------------------
    # All providers failed
    # --------------------------------------------------------

    logger.warning(
        "All web search providers failed: %s",
        provider_errors,
    )

    return {
        "success": False,
        "query": query,
        "count": 0,
        "results": [],
        "error": (
            "No web search provider returned "
            "usable results."
        ),
        "provider_errors": provider_errors,
    }


# ============================================================
# PUBLIC URL TOOL
# ============================================================

def open_url(
    url: str,
) -> Dict[str, Any]:
    """
    Open a validated HTTP/HTTPS URL
    in the default browser.
    """

    # --------------------------------------------------------
    # Validate type
    # --------------------------------------------------------

    if not isinstance(url, str):
        return {
            "success": False,
            "error": "URL must be a string.",
        }

    url = _clean_url(url)

    if not url:
        return {
            "success": False,
            "error": "URL is required.",
        }

    # --------------------------------------------------------
    # Validate URL
    # --------------------------------------------------------

    try:
        parsed = urlparse(url)
    except Exception as exc:
        return {
            "success": False,
            "error": f"Invalid URL: {exc}",
        }

    if parsed.scheme.lower() not in {
        "http",
        "https",
    }:
        return {
            "success": False,
            "error": (
                "Only HTTP and HTTPS URLs "
                "are allowed."
            ),
        }

    if not parsed.netloc:
        return {
            "success": False,
            "error": (
                "URL must include a valid domain."
            ),
        }

    # --------------------------------------------------------
    # Open browser
    # --------------------------------------------------------

    try:

        opened = webbrowser.open(
            url
        )

        if not opened:
            return {
                "success": False,
                "error": (
                    f"Could not open URL: {url}"
                ),
            }

        return {
            "success": True,
            "url": url,
            "message": (
                f"Opened {url}."
            ),
        }

    except Exception as exc:

        logger.exception(
            "Failed to open URL: %s",
            url,
        )

        return {
            "success": False,
            "error": (
                f"Failed to open URL: {exc}"
            ),
        }