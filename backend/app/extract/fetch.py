"""Descarga una página y extrae el texto principal (con headings en markdown)."""

import hashlib
import logging
from dataclasses import dataclass

import httpx
import trafilatura

from app.config import get_settings

log = logging.getLogger(__name__)

MIN_TEXT_CHARS = 800


@dataclass
class ExtractedDoc:
    url: str
    title: str | None
    text: str

    @property
    def content_hash(self) -> str:
        normalized = " ".join(self.text.split())
        return hashlib.sha256(normalized.encode()).hexdigest()


async def fetch_html(url: str) -> str:
    settings = get_settings()
    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=30,
        headers={"User-Agent": settings.user_agent, "Accept-Language": "en,es;q=0.8"},
    ) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.text


async def fetch_html_browser(url: str) -> str | None:
    """Fallback para páginas renderizadas con JS. Requiere `uv sync --extra browser` + `playwright install chromium`."""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        log.info("playwright no instalado; sin fallback de navegador")
        return None
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        try:
            page = await browser.new_page(user_agent=get_settings().user_agent)
            await page.goto(url, wait_until="networkidle", timeout=45_000)
            return await page.content()
        finally:
            await browser.close()


def extract_text(html: str, url: str) -> ExtractedDoc:
    text = trafilatura.extract(
        html,
        url=url,
        output_format="markdown",
        include_comments=False,
        include_tables=True,
        favor_recall=True,
    ) or ""
    meta = trafilatura.extract_metadata(html, default_url=url)
    title = meta.title if meta else None
    return ExtractedDoc(url=url, title=title, text=text.strip())


async def fetch_document(url: str, html: str | None = None) -> ExtractedDoc:
    """Obtiene y extrae `url`. Si se pasa `html` (p. ej. un snapshot de Wayback) no se descarga."""
    doc = extract_text(html if html is not None else await fetch_html(url), url)
    if html is None and len(doc.text) < MIN_TEXT_CHARS:
        rendered = await fetch_html_browser(url)
        if rendered:
            alt = extract_text(rendered, url)
            if len(alt.text) > len(doc.text):
                doc = alt
    if not doc.text:
        raise ValueError(f"No se pudo extraer texto de {url}")
    return doc
