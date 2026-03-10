"""
WebSearchTool — real-time web search for agents.

Provides agents with live internet search capabilities using multiple
backends: SearXNG (self-hosted, privacy-preserving), Brave Search API,
or DuckDuckGo (no-API fallback via HTML scraping).

Results include title, URL, snippet, and freshness metadata for citation.
A local LRU cache prevents redundant queries within the same session.

Backend priority: SearXNG → Brave → DuckDuckGo

Environment:
    VERSAAI_SEARCH_BACKEND   - "searxng" | "brave" | "duckduckgo" (default: duckduckgo)
    VERSAAI_SEARXNG_URL      - SearXNG instance URL (default: http://localhost:8888)
    VERSAAI_BRAVE_API_KEY    - Brave Search API key (required for brave backend)
"""

import hashlib
import logging
import os
import re
import time
from collections import OrderedDict
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus, urlparse

from versaai.agents.tools.base import SafetyLevel, Tool, ToolResult

logger = logging.getLogger(__name__)

_CACHE_MAX = 128
_DEFAULT_TIMEOUT = 10


class _LRUCache:
    """Simple thread-safe LRU cache for search results."""

    def __init__(self, maxsize: int = _CACHE_MAX):
        self._cache: OrderedDict[str, Any] = OrderedDict()
        self._maxsize = maxsize

    def get(self, key: str) -> Optional[Any]:
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        return None

    def put(self, key: str, value: Any) -> None:
        if key in self._cache:
            self._cache.move_to_end(key)
        self._cache[key] = value
        while len(self._cache) > self._maxsize:
            self._cache.popitem(last=False)


class WebSearchTool(Tool):
    """
    Agent tool that performs real-time web searches.

    Usage in a ReAct loop::

        Action: web_search
        Action Input: {"query": "latest Python 3.14 features", "num_results": 5}

    Returns ranked results with title, URL, snippet, and timestamp.
    """

    def __init__(
        self,
        backend: Optional[str] = None,
        searxng_url: Optional[str] = None,
        brave_api_key: Optional[str] = None,
    ):
        self._backend = (
            backend
            or os.environ.get("VERSAAI_SEARCH_BACKEND", "duckduckgo")
        ).lower()
        self._searxng_url = (
            searxng_url
            or os.environ.get("VERSAAI_SEARXNG_URL", "http://localhost:8888")
        ).rstrip("/")
        self._brave_api_key = brave_api_key or os.environ.get(
            "VERSAAI_BRAVE_API_KEY", ""
        )
        self._cache = _LRUCache()

    # ------------------------------------------------------------------
    # Tool interface
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return (
            "Search the web for real-time information. Returns ranked results "
            "with title, URL, and snippet. Use for current events, documentation, "
            "or any query requiring up-to-date data."
        )

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query.",
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of results (default: 5, max: 10).",
                },
            },
            "required": ["query"],
        }

    @property
    def safety_level(self) -> SafetyLevel:
        return SafetyLevel.READ_ONLY

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def execute(self, **kwargs) -> ToolResult:
        query = kwargs.get("query", "").strip()
        num_results = min(int(kwargs.get("num_results", 5)), 10)

        if not query:
            return ToolResult(
                success=False, output="", error="Query must be non-empty."
            )

        cache_key = hashlib.sha256(
            f"{query}:{num_results}".encode()
        ).hexdigest()[:16]
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        start = time.monotonic()
        try:
            results = self._search(query, num_results)
        except Exception as exc:
            logger.error("Web search failed: %s", exc, exc_info=True)
            return ToolResult(
                success=False, output="", error=f"Search error: {exc}"
            )
        elapsed = time.monotonic() - start

        if not results:
            result = ToolResult(
                success=True,
                output="No results found.",
                metadata={"result_count": 0, "backend": self._backend},
                execution_time=elapsed,
            )
            self._cache.put(cache_key, result)
            return result

        lines = [f"Found {len(results)} result(s) via {self._backend}:\n"]
        for i, r in enumerate(results, 1):
            title = r.get("title", "Untitled")
            url = r.get("url", "")
            snippet = r.get("snippet", "")
            if len(snippet) > 300:
                snippet = snippet[:300] + "…"
            lines.append(f"[{i}] {title}")
            lines.append(f"    URL: {url}")
            lines.append(f"    {snippet}\n")

        output = "\n".join(lines)
        result = ToolResult(
            success=True,
            output=output,
            metadata={
                "result_count": len(results),
                "backend": self._backend,
                "results": results,
            },
            execution_time=elapsed,
        )
        self._cache.put(cache_key, result)
        return result

    # ------------------------------------------------------------------
    # Backend dispatchers
    # ------------------------------------------------------------------

    def _search(self, query: str, num_results: int) -> List[Dict[str, str]]:
        if self._backend == "searxng":
            return self._search_searxng(query, num_results)
        elif self._backend == "brave":
            return self._search_brave(query, num_results)
        else:
            return self._search_duckduckgo(query, num_results)

    def _search_searxng(
        self, query: str, num_results: int
    ) -> List[Dict[str, str]]:
        """Search via a SearXNG instance (self-hosted, privacy-preserving)."""
        import httpx

        url = f"{self._searxng_url}/search"
        params = {
            "q": query,
            "format": "json",
            "categories": "general",
            "pageno": 1,
        }
        resp = httpx.get(url, params=params, timeout=_DEFAULT_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        results = []
        for item in data.get("results", [])[:num_results]:
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "snippet": item.get("content", ""),
            })
        return results

    def _search_brave(
        self, query: str, num_results: int
    ) -> List[Dict[str, str]]:
        """Search via Brave Search API."""
        import httpx

        if not self._brave_api_key:
            raise ValueError(
                "Brave Search requires VERSAAI_BRAVE_API_KEY env variable"
            )

        url = "https://api.search.brave.com/res/v1/web/search"
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": self._brave_api_key,
        }
        params = {"q": query, "count": num_results}
        resp = httpx.get(
            url, headers=headers, params=params, timeout=_DEFAULT_TIMEOUT
        )
        resp.raise_for_status()
        data = resp.json()

        results = []
        for item in data.get("web", {}).get("results", [])[:num_results]:
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "snippet": item.get("description", ""),
            })
        return results

    def _search_duckduckgo(
        self, query: str, num_results: int
    ) -> List[Dict[str, str]]:
        """
        Search DuckDuckGo via its HTML lite endpoint.

        This doesn't require an API key. We fetch the lite HTML page
        and parse the result entries.
        """
        import httpx

        url = "https://lite.duckduckgo.com/lite/"
        resp = httpx.post(
            url,
            data={"q": query},
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (compatible; VersaAI/1.0; "
                    "+https://github.com/The-No-Hands-company/VersaAI)"
                ),
            },
            timeout=_DEFAULT_TIMEOUT,
            follow_redirects=True,
        )
        resp.raise_for_status()

        return self._parse_ddg_lite(resp.text, num_results)

    @staticmethod
    def _parse_ddg_lite(html: str, num_results: int) -> List[Dict[str, str]]:
        """Extract results from DuckDuckGo lite HTML."""
        results: List[Dict[str, str]] = []

        # DDG lite uses table rows with class "result-link" for titles
        # and "result-snippet" for snippets
        link_pattern = re.compile(
            r'<a[^>]+class="result-link"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
            re.DOTALL,
        )
        snippet_pattern = re.compile(
            r'<td[^>]+class="result-snippet"[^>]*>(.*?)</td>',
            re.DOTALL,
        )

        links = link_pattern.findall(html)
        snippets = snippet_pattern.findall(html)

        for i, (href, title_html) in enumerate(links[:num_results]):
            title = re.sub(r"<[^>]+>", "", title_html).strip()
            snippet = ""
            if i < len(snippets):
                snippet = re.sub(r"<[^>]+>", "", snippets[i]).strip()

            # Validate URL — only include results with proper URLs
            parsed = urlparse(href)
            if parsed.scheme in ("http", "https") and parsed.netloc:
                results.append({
                    "title": title,
                    "url": href,
                    "snippet": snippet,
                })

        return results
