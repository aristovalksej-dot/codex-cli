"""Web browsing tools — fetch and parse web pages."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from codex_cli.tools.base import Tool

_HTTP_TIMEOUT = 30.0
_MAX_CONTENT_LENGTH = 100000


def _clean_text(text: str) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(lines).strip()


class FetchWebpageTool(Tool):
    name = "fetch_webpage"
    description = (
        "Fetch a web page and return its text content. "
        "Strips HTML and returns readable text with links. "
        "Useful for reading documentation, articles, and web content."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "The URL to fetch"},
            "extract_links": {
                "type": "boolean",
                "description": "Also extract and list all links on the page (default false)",
            },
        },
        "required": ["url"],
    }

    async def execute(self, url: str, extract_links: bool = False, **_: Any) -> str:
        parsed = urlparse(url)
        if not parsed.scheme:
            url = "https://" + url

        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=_HTTP_TIMEOUT,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    )
                },
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
        except httpx.HTTPStatusError as e:
            return f"Error: HTTP {e.response.status_code} fetching {url}"
        except httpx.RequestError as e:
            return f"Error fetching {url}: {e}"

        content_type = response.headers.get("content-type", "")
        if "text/html" not in content_type and "text/plain" not in content_type:
            return f"Fetched {url} — content type: {content_type} (not text/html)"

        html = response.text
        soup = BeautifulSoup(html, "lxml")

        for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "svg"]):
            tag.decompose()

        title = soup.title.string.strip() if soup.title and soup.title.string else "(no title)"
        text = _clean_text(soup.get_text())

        if len(text) > _MAX_CONTENT_LENGTH:
            text = text[:_MAX_CONTENT_LENGTH] + "\n\n... [content truncated]"

        parts = [f"Title: {title}", f"URL: {url}", "---", text]

        if extract_links:
            links: list[str] = []
            for a in soup.find_all("a", href=True):
                href = a["href"]
                link_text = a.get_text(strip=True)[:80]
                full_url = urljoin(url, href)
                if full_url.startswith(("http://", "https://")):
                    links.append(f"  [{link_text}]({full_url})")
            if links:
                parts.append("\n--- Links ---")
                parts.extend(links[:100])

        return "\n".join(parts)


class SearchWebTool(Tool):
    name = "search_web"
    description = (
        "Search the web using DuckDuckGo HTML search and return results. "
        "Returns titles, URLs, and snippets for the top results."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "num_results": {
                "type": "integer",
                "description": "Number of results to return (default: 8, max: 20)",
            },
        },
        "required": ["query"],
    }

    async def execute(self, query: str, num_results: int = 8, **_: Any) -> str:
        num_results = min(max(num_results, 1), 20)
        url = "https://html.duckduckgo.com/html/"
        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=_HTTP_TIMEOUT,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    )
                },
            ) as client:
                response = await client.post(url, data={"q": query})
                response.raise_for_status()
        except Exception as e:
            return f"Error searching: {e}"

        soup = BeautifulSoup(response.text, "lxml")
        results: list[str] = []

        for item in soup.select(".result"):
            title_el = item.select_one(".result__title a")
            snippet_el = item.select_one(".result__snippet")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            href = title_el.get("href", "")
            snippet = snippet_el.get_text(strip=True) if snippet_el else ""
            results.append(f"  {len(results) + 1}. {title}\n     URL: {href}\n     {snippet}")
            if len(results) >= num_results:
                break

        if not results:
            return f"No results found for: {query}"
        return f"Search results for: {query}\n\n" + "\n\n".join(results)
