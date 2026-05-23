"""
advancement_pipeline.py — Orchestrator pentru colectarea advancement-urilor.

Rulează toți colectorii disponibili și salvează rezultatele în cache-ul local.
NU se apelează automat la fiecare analiză — trebuie declanșat manual
(buton în UI sau linie de comandă).

Utilizare din linia de comandă:
  python advancement_pipeline.py

Utilizare din Python:
  from advancement_pipeline import collect_all, get_cache_summary
  report = collect_all()
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import TypedDict

# Asigură că modulul poate fi importat indiferent de cwd
_HERE = Path(__file__).parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import advancement_store as store
from advancement_collectors.arxiv_collector      import ArxivCollector
from advancement_collectors.huggingface_collector import HuggingFaceCollector
from advancement_collectors.openalex_collector   import OpenAlexCollector
from advancement_collectors.rss_collector        import RssCollector
from advancement_collectors.discord_collector    import DiscordCollector

logger = logging.getLogger(__name__)


class CollectReport(TypedDict):
    total_new:   int
    by_source:   dict[str, int]
    errors:      list[str]
    duplicates_removed: int


def collect_all(
    include_arxiv:       bool = True,
    include_huggingface: bool = True,
    include_openalex:    bool = True,
    include_rss:         bool = True,
    include_discord:     bool = True,
    max_per_source:      int  = 50,
) -> CollectReport:
    """
    Rulează toți colectorii activi și salvează în cache.

    Args:
        include_*:     Activează/dezactivează fiecare sursă.
        max_per_source: Număr maxim de advancement-uri per sursă.

    Returns:
        Raport cu nr. de intrări noi, per sursă, și erori.
    """
    report: CollectReport = {
        "total_new":          0,
        "by_source":          {},
        "errors":             [],
        "duplicates_removed": 0,
    }

    collectors = []
    if include_arxiv:
        collectors.append(("arXiv",        ArxivCollector()))
    if include_huggingface:
        collectors.append(("Hugging Face", HuggingFaceCollector()))
    if include_openalex:
        collectors.append(("OpenAlex",     OpenAlexCollector()))
    if include_rss:
        collectors.append(("RSS/Bloguri",  RssCollector()))
    if include_discord:
        dc = DiscordCollector()
        if dc.is_available():
            collectors.append(("Discord", dc))

    for source_name, collector in collectors:
        try:
            logger.info("pipeline: collecting from %s …", source_name)
            advancements = collector.collect(max_results=max_per_source)
            saved = store.upsert_many(advancements)
            report["by_source"][source_name] = saved
            report["total_new"] += saved
            logger.info("pipeline: %s → %d saved", source_name, saved)
        except Exception as exc:
            msg = f"{source_name}: {exc}"
            report["errors"].append(msg)
            logger.warning("pipeline: error from %s: %s", source_name, exc)

    # Deduplicare după colectare
    removed = store.remove_duplicates()
    report["duplicates_removed"] = removed
    if removed:
        logger.info("pipeline: removed %d duplicates", removed)

    return report


def get_cache_summary() -> dict:
    """
    Returnează un rezumat al cache-ului curent.

    Returns:
        Dict cu total, per sursă, și timestamp-ul ultimei actualizări.
    """
    sources = [
        "arxiv", "huggingface", "openalex",
        "official_blog", "discord", "internal_categorized",
    ]
    by_source = {src: store.count(src) for src in sources}
    return {
        "total":        store.count(),
        "by_source":    {k: v for k, v in by_source.items() if v > 0},
        "last_updated": store.last_updated(),
    }


# ── CLI ────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    print("Pornesc colectarea advancement-urilor din surse externe …\n")
    report = collect_all()

    print(f"✓ Total intrări noi/actualizate: {report['total_new']}")
    for src, n in report["by_source"].items():
        print(f"  • {src}: {n}")
    if report["duplicates_removed"]:
        print(f"  • Duplicate eliminate: {report['duplicates_removed']}")
    if report["errors"]:
        print("\nErori:")
        for err in report["errors"]:
            print(f"  ✗ {err}")

    summary = get_cache_summary()
    print(f"\nCache total: {summary['total']} advancement-uri")
    print(f"Ultima actualizare: {summary['last_updated']}")
