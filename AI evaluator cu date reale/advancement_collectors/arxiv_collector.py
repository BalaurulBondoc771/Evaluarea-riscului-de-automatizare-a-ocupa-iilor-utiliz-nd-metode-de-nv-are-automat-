"""
arxiv_collector.py — Colector pentru lucrări recente de pe arXiv.

Interogă API-ul arXiv (fără autentificare) și returnează lucrări
relevante din domeniile AI/ML/NLP/CV/Robotics.

Endpoint: https://export.arxiv.org/api/query
Documentație: https://arxiv.org/help/api/
"""
from __future__ import annotations

import logging
import urllib.parse
import urllib.request
from datetime import datetime
from xml.etree import ElementTree as ET

from advancement_collectors import BaseCollector, make_advancement

logger = logging.getLogger(__name__)

_ATOM_NS = "http://www.w3.org/2005/Atom"

_CATEGORIES = [
    "cs.AI",   # Artificial Intelligence
    "cs.LG",   # Machine Learning
    "cs.CL",   # Computation and Language (NLP)
    "cs.CV",   # Computer Vision
    "cs.RO",   # Robotics
    "econ.GN", # General Economics (impact AI)
]

# Cuvinte cheie din titlu/abstract → skill-uri afectate (română)
_KW_SKILLS: list[tuple[list[str], list[str]]] = [
    (
        ["language model", "llm", "text generation", "chatbot", "gpt", "bert", "transformer"],
        ["redactare text", "traducere", "comunicare scrisă", "suport clienți", "copywriting", "documentare"],
    ),
    (
        ["image recognition", "object detection", "computer vision", "visual", "segmentation"],
        ["inspecție vizuală", "control calitate", "analiză imagini", "supraveghere"],
    ),
    (
        ["speech recognition", "speech synthesis", "voice", "whisper", "audio", "asr"],
        ["transcriere", "stenografie", "call center", "suport clienți vocal", "voice-over"],
    ),
    (
        ["robot", "robotics", "manipulation", "grasping", "autonomous", "cobot"],
        ["asamblare", "manipulare materiale", "operare mașini", "sudură", "ambalare"],
    ),
    (
        ["code generation", "programming", "software", "github copilot", "devin"],
        ["programare", "dezvoltare software", "debugging", "testare software"],
    ),
    (
        ["medical", "clinical", "radiology", "pathology", "diagnosis", "ehr"],
        ["documentare medicală", "asistență diagnostic", "note clinice", "codificare medicală"],
    ),
    (
        ["logistics", "supply chain", "inventory", "routing", "optimization"],
        ["logistică", "lanț de aprovizionare", "planificare", "transport", "gestiune depozit"],
    ),
    (
        ["financial", "trading", "accounting", "audit", "fraud"],
        ["analiză financiară", "contabilitate", "audit", "evaluare risc"],
    ),
    (
        ["automation", "rpa", "process", "workflow", "document"],
        ["introducere date", "procesare formulare", "arhivare", "administrație"],
    ),
    (
        ["education", "tutoring", "learning", "student", "curriculum"],
        ["predare", "tutoriat", "design curriculum", "evaluare"],
    ),
]


def _infer_skills(title: str, abstract: str) -> list[str]:
    text = (title + " " + abstract).lower()
    matched: list[str] = []
    for keywords, skills in _KW_SKILLS:
        if any(kw in text for kw in keywords):
            matched.extend(skills)
    # deduplicate păstrând ordinea
    return list(dict.fromkeys(matched))


def _parse_date(raw: str) -> str:
    return (raw or "")[:10]


def _infer_maturity(date_str: str) -> str:
    try:
        pub      = datetime.fromisoformat(date_str)
        age_days = (datetime.now() - pub.replace(tzinfo=None)).days
        if age_days < 180:
            return "emerging"
        if age_days < 730:
            return "growing"
        return "high"
    except Exception:
        return "emerging"


class ArxivCollector(BaseCollector):
    """
    Colectează lucrări recente de pe arXiv.
    Nu necesită autentificare.
    Rate limit recomandat: max 3 req/s (respectăm cu timeout=15).
    """

    SOURCE_TYPE = "arxiv"

    def __init__(
        self,
        categories: list[str] | None = None,
        max_per_category: int = 10,
    ):
        self.categories      = categories or _CATEGORIES
        self.max_per_category = max_per_category

    def collect(self, max_results: int = 50) -> list[dict]:
        results:   list[dict] = []
        seen_urls: set[str]   = set()
        per_cat = max(3, min(self.max_per_category, max_results // len(self.categories)))

        for cat in self.categories:
            try:
                batch = self._fetch_category(cat, per_cat)
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
                logger.warning("arxiv_collector: category %s failed: %s", cat, exc)

        return results

    def _fetch_category(self, category: str, max_results: int) -> list[dict]:
        query = urllib.parse.urlencode({
            "search_query": f"cat:{category}",
            "start":        0,
            "max_results":  max_results,
            "sortBy":       "submittedDate",
            "sortOrder":    "descending",
        })
        url = f"https://export.arxiv.org/api/query?{query}"
        req = urllib.request.Request(url, headers={"User-Agent": "AdvancementCollector/1.0"})

        with urllib.request.urlopen(req, timeout=15) as resp:
            xml_bytes = resp.read()

        root = ET.fromstring(xml_bytes)
        ns   = {"atom": _ATOM_NS}

        results: list[dict] = []
        for entry in root.findall("atom:entry", ns):
            try:
                title_el   = entry.find("atom:title",   ns)
                summary_el = entry.find("atom:summary", ns)
                id_el      = entry.find("atom:id",      ns)
                pub_el     = entry.find("atom:published", ns)

                title    = (title_el.text   or "").strip().replace("\n", " ")
                abstract = (summary_el.text or "").strip().replace("\n", " ")[:500]
                src_url  = (id_el.text      or "").strip()
                pub_date = _parse_date((pub_el.text or "").strip())

                skills   = _infer_skills(title, abstract)
                maturity = _infer_maturity(pub_date)

                results.append(make_advancement(
                    title=title,
                    summary=abstract,
                    source_type="arxiv",
                    source_name=f"arXiv — {category}",
                    source_url=src_url,
                    published_date=pub_date,
                    affected_skills=skills,
                    maturity=maturity,
                    impact="medium",
                    evidence_strength="medium",
                    adoption_readiness="low",
                    confidence="medium",
                ))
            except Exception as exc:
                logger.debug("arxiv_collector: parse entry failed: %s", exc)

        return results
