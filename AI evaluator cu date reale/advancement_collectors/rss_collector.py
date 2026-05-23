"""
rss_collector.py — Colector pentru bloguri oficiale ale organizațiilor AI.

Citește feeduri RSS/Atom de la OpenAI, Anthropic, Google DeepMind, Meta AI,
Hugging Face. Nu necesită autentificare.

sourceType: "official_blog" — nu prezentate ca surse academice peer-reviewed.
"""
from __future__ import annotations

import logging
import urllib.request
from xml.etree import ElementTree as ET

from advancement_collectors import BaseCollector, make_advancement

logger = logging.getLogger(__name__)

_ATOM_NS = "http://www.w3.org/2005/Atom"

# Feed-uri RSS/Atom cunoscute pentru organizații AI
_FEEDS: list[dict] = [
    {
        "name":   "OpenAI Research",
        "url":    "https://openai.com/news/rss.xml",
        "skills": ["modele limbaj", "inteligență artificială", "cercetare AI"],
    },
    {
        "name":   "Google DeepMind Blog",
        "url":    "https://deepmind.google/blog/rss.xml",
        "skills": ["cercetare AI", "modele avansate", "robotică"],
    },
    {
        "name":   "Meta AI Research",
        "url":    "https://ai.meta.com/blog/rss.xml",
        "skills": ["cercetare AI", "computer vision", "NLP open-source"],
    },
    {
        "name":   "Anthropic Research",
        "url":    "https://www.anthropic.com/research.rss",
        "skills": ["siguranță AI", "modele limbaj", "aliniere AI"],
    },
    {
        "name":   "Hugging Face Blog",
        "url":    "https://huggingface.co/blog/feed.xml",
        "skills": ["modele open-source", "machine learning", "NLP"],
    },
    {
        "name":   "MIT Technology Review — AI",
        "url":    "https://www.technologyreview.com/feed/",
        "skills": ["inteligență artificială", "automatizare", "piața muncii"],
    },
]


def _fetch(url: str, timeout: int = 10) -> bytes | None:
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "AdvancementCollector/1.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except Exception as exc:
        logger.debug("rss_collector: fetch %s failed: %s", url, exc)
        return None


def _parse(xml_bytes: bytes) -> list[dict]:
    """Parsează RSS 2.0 sau Atom. Returnează [] la eroare."""
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return []

    items: list[dict] = []

    # RSS 2.0: <item> sub <channel>
    for item in root.iter("item"):
        title   = (item.findtext("title")       or "").strip()
        link    = (item.findtext("link")        or "").strip()
        desc    = (item.findtext("description") or "").strip()[:500]
        pubdate = (item.findtext("pubDate")     or "")[:10]
        if title and link:
            items.append({"title": title, "url": link, "summary": desc, "date": pubdate})

    if items:
        return items

    # Atom: <entry>
    ns = {"atom": _ATOM_NS}
    for entry in root.findall("atom:entry", ns):
        title_el   = entry.find("atom:title",   ns)
        link_el    = entry.find("atom:link",    ns)
        summ_el    = entry.find("atom:summary", ns) or entry.find("atom:content", ns)
        updated_el = entry.find("atom:updated", ns) or entry.find("atom:published", ns)

        title   = (title_el.text   or "").strip() if title_el is not None else ""
        link    = (link_el.get("href") or "") if link_el is not None else ""
        summary = (summ_el.text    or "").strip()[:500] if summ_el is not None else ""
        date    = (updated_el.text or "")[:10] if updated_el is not None else ""

        if title and link:
            items.append({"title": title, "url": link, "summary": summary, "date": date})

    return items


class RssCollector(BaseCollector):
    """
    Colectează articole de pe blogurile oficiale ale organizațiilor AI.
    Nu necesită autentificare.
    Notă: unele bloguri pot schimba URL-urile feedurilor fără notificare.
    """

    SOURCE_TYPE = "official_blog"

    def __init__(self, feeds: list[dict] | None = None):
        self.feeds = feeds or _FEEDS

    def collect(self, max_results: int = 40) -> list[dict]:
        results:   list[dict] = []
        seen_urls: set[str]   = set()

        for feed in self.feeds:
            xml_bytes = _fetch(feed["url"])
            if not xml_bytes:
                continue
            try:
                for item in _parse(xml_bytes):
                    url = item.get("url", "")
                    if not url or url in seen_urls:
                        continue
                    seen_urls.add(url)
                    results.append(make_advancement(
                        title=item.get("title", ""),
                        summary=item.get("summary", ""),
                        source_type="official_blog",
                        source_name=feed["name"],
                        source_url=url,
                        published_date=item.get("date", ""),
                        affected_skills=feed.get("skills", []),
                        maturity="growing",
                        impact="medium",
                        evidence_strength="medium",
                        adoption_readiness="medium",
                        confidence="medium",
                    ))
                    if len(results) >= max_results:
                        return results
            except Exception as exc:
                logger.warning("rss_collector: parse failed for %s: %s", feed["name"], exc)

        return results
