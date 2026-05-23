"""
openalex_collector.py — Colector pentru lucrări academice de pe OpenAlex.

OpenAlex este un index open-access al literaturii academice (fără cheie API).
Rate limit recomandat: max 10 req/s (respectăm cu timeout=15).

Endpoint: https://api.openalex.org/works
Documentație: https://docs.openalex.org/
"""
from __future__ import annotations

import json
import logging
import urllib.parse
import urllib.request

from advancement_collectors import BaseCollector, make_advancement

logger = logging.getLogger(__name__)

_BASE = "https://api.openalex.org/works"

# (query text, skill-uri afectate implicite în română)
_QUERIES: list[tuple[str, list[str]]] = [
    (
        "artificial intelligence automation jobs labor market",
        ["automatizare", "piața muncii", "productivitate"],
    ),
    (
        "large language models workplace productivity",
        ["redactare text", "comunicare scrisă", "productivitate"],
    ),
    (
        "computer vision industrial automation quality control",
        ["inspecție vizuală", "control calitate", "asamblare"],
    ),
    (
        "robotic process automation workflow RPA",
        ["introducere date", "procesare formulare", "contabilitate primară"],
    ),
    (
        "machine learning financial analysis audit",
        ["analiză financiară", "contabilitate", "audit"],
    ),
    (
        "natural language processing clinical documentation medical",
        ["documentare medicală", "note clinice", "codificare medicală"],
    ),
    (
        "AI education personalized learning tutoring",
        ["predare", "tutoriat", "design curriculum"],
    ),
    (
        "autonomous robots logistics supply chain optimization",
        ["logistică", "transport", "gestiune depozit"],
    ),
    (
        "generative AI creative design image synthesis",
        ["design grafic", "ilustrație", "conținut vizual", "marketing vizual"],
    ),
    (
        "speech recognition voice synthesis call center automation",
        ["transcriere", "call center", "suport clienți vocal"],
    ),
]


def _infer_impact(citations: int) -> tuple[str, str, str]:
    """Returnează (maturity, impact, evidence_strength) în funcție de citări."""
    if citations >= 100:
        return "high", "high", "high"
    if citations >= 20:
        return "growing", "medium", "high"
    return "emerging", "low", "medium"


class OpenAlexCollector(BaseCollector):
    """
    Colectează lucrări academice relevante de pe OpenAlex.
    Nu necesită autentificare (polite pool cu mailto).
    """

    SOURCE_TYPE = "openalex"

    def __init__(
        self,
        from_year: int = 2022,
        contact_email: str = "advancement.collector@example.com",
    ):
        self.from_year      = from_year
        self.contact_email  = contact_email

    def collect(self, max_results: int = 40) -> list[dict]:
        results:   list[dict] = []
        seen_urls: set[str]   = set()
        per_query = max(3, max_results // len(_QUERIES))

        for query_text, default_skills in _QUERIES:
            try:
                batch = self._fetch_query(query_text, default_skills, per_query)
                for adv in batch:
                    url = adv.get("sourceUrl", "")
                    if url and url in seen_urls:
                        continue
                    if url:
                        seen_urls.add(url)
                    results.append(adv)
                    if len(results) >= max_results:
                        return results
            except Exception as exc:
                logger.warning("openalex_collector: query '%s…' failed: %s", query_text[:30], exc)

        return results

    def _fetch_query(self, query: str, default_skills: list[str], per_page: int) -> list[dict]:
        params = urllib.parse.urlencode({
            "search":   query,
            "filter":   f"from_publication_date:{self.from_year}-01-01,type:article",
            "sort":     "cited_by_count:desc",
            "per_page": per_page,
            "mailto":   self.contact_email,
        })
        url = f"{_BASE}?{params}"
        req = urllib.request.Request(url, headers={"User-Agent": "AdvancementCollector/1.0"})

        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        results: list[dict] = []
        for work in data.get("results", []):
            if not isinstance(work, dict):
                continue

            title    = str(work.get("display_name") or "").strip()
            pub_date = str(work.get("publication_date") or "")[:10]
            doi      = str(work.get("doi") or "")
            landing  = str(work.get("landing_page_url") or doi or "")
            citations = int(work.get("cited_by_count") or 0)

            if not title or not landing:
                continue

            maturity, impact, evidence = _infer_impact(citations)

            results.append(make_advancement(
                title=title,
                summary=f"Lucrare academică (citări: {citations}). Publicată: {pub_date}.",
                source_type="openalex",
                source_name="OpenAlex — Academic Literature",
                source_url=landing,
                published_date=pub_date,
                affected_skills=default_skills,
                maturity=maturity,
                impact=impact,
                evidence_strength=evidence,
                adoption_readiness="low",
                confidence="medium",
            ))

        return results
