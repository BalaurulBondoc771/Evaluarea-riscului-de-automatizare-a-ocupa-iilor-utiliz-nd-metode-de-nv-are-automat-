"""
advancement_collectors — Schema comună și clasa de bază pentru colectoare externe.

Fiecare collector implementează BaseCollector și returnează liste de dict-uri
conform schemei Advancement. Niciun collector nu aruncă excepții — returnează [].
"""
from __future__ import annotations

_VALID_LEVELS   = frozenset(("low", "medium", "high"))
_VALID_MATURITY = frozenset(("emerging", "growing", "high"))
_VALID_SOURCES  = frozenset((
    "arxiv", "openalex", "huggingface", "discord",
    "official_blog", "internal_categorized", "gpt_estimated",
))


def make_advancement(
    title: str,
    summary: str,
    source_type: str,
    source_name: str,
    source_url: str,
    published_date: str,
    affected_skills: list | None = None,
    affected_occupations: list | None = None,
    maturity: str = "emerging",
    impact: str = "medium",
    evidence_strength: str = "medium",
    adoption_readiness: str = "low",
    confidence: str = "medium",
) -> dict:
    """
    Construiește un dict Advancement validat cu valori implicite sigure.
    Trunchiază câmpurile text pentru a evita stocarea excesivă.
    """
    return {
        "title":               str(title)[:300].strip(),
        "summary":             str(summary)[:1000].strip(),
        "sourceType":          source_type if source_type in _VALID_SOURCES else "internal_categorized",
        "sourceName":          str(source_name)[:200].strip(),
        "sourceUrl":           str(source_url)[:500].strip(),
        "publishedDate":       str(published_date)[:20].strip(),
        "affectedSkills":      list(affected_skills or []),
        "affectedOccupations": list(affected_occupations or []),
        "maturity":            maturity if maturity in _VALID_MATURITY else "emerging",
        "impact":              impact if impact in _VALID_LEVELS else "medium",
        "evidenceStrength":    evidence_strength if evidence_strength in _VALID_LEVELS else "medium",
        "adoptionReadiness":   adoption_readiness if adoption_readiness in _VALID_LEVELS else "low",
        "confidence":          confidence if confidence in _VALID_LEVELS else "medium",
    }


class BaseCollector:
    """Clasă de bază pentru toți colectorii de advancement-uri externe."""

    SOURCE_TYPE: str = "unknown"

    def collect(self, max_results: int = 20) -> list[dict]:
        """
        Colectează advancement-uri din sursă externă.
        Returnează [] la eroare — nu aruncă excepții.
        """
        raise NotImplementedError

    def is_available(self) -> bool:
        """Verifică dacă sursa este accesibilă (config prezentă, rețea etc.)."""
        return True
