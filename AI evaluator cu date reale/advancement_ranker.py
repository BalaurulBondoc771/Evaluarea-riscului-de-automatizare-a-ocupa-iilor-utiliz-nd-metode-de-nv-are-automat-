"""
advancement_ranker.py — Rankare advancement-uri după relevanță și calitate.

Combină: relevanța skill-urilor, recența, impactul estimat, puterea dovezilor
și credibilitatea sursei pentru a produce un scor compus.
"""
from __future__ import annotations

from datetime import datetime

_RELEVANCE_WEIGHT = 0.50
_RECENCY_WEIGHT   = 0.20
_IMPACT_WEIGHT    = 0.20
_EVIDENCE_WEIGHT  = 0.10

_LEVEL_SCORES = {"low": 0.2, "medium": 0.6, "high": 1.0}

# Credibilitate per tip de sursă (0..1)
_SOURCE_CREDIBILITY: dict[str, float] = {
    "openalex":             0.90,
    "arxiv":                0.85,
    "official_blog":        0.80,
    "huggingface":          0.75,
    "internal_categorized": 0.70,
    "gpt_estimated":        0.55,
    "discord":              0.40,
}


def rank_advancements(
    advancements: list[dict],
    skills: list[str],
    max_results: int = 5,
) -> list[dict]:
    """
    Returnează top `max_results` advancement-uri rankate după scor compus.

    Args:
        advancements: Mix de advancement-uri (orice sourceType).
        skills:       Skill-urile ocupației analizate (text liber).
        max_results:  Numărul maxim de rezultate returnate.

    Returns:
        Lista sortată descrescător, fără duplicate după sourceUrl.
    """
    if not advancements:
        return []

    skills_lower = [s.lower() for s in skills]
    seen_urls:   set[str] = set()
    scored: list[tuple[float, dict]] = []

    for adv in advancements:
        url = adv.get("sourceUrl", "")
        if url and url in seen_urls:
            continue
        if url:
            seen_urls.add(url)

        score = _composite_score(adv, skills_lower)
        scored.append((score, adv))

    scored.sort(key=lambda x: -x[0])
    result = []
    for score, adv in scored[:max_results]:
        entry = dict(adv)
        entry["relevanceScore"] = max(0, min(100, round(score * 100)))
        result.append(entry)
    return result


# ── Score components ──────────────────────────────────────────────────────────

def _composite_score(adv: dict, skills_lower: list[str]) -> float:
    relevance   = _relevance_score(adv, skills_lower)
    recency     = _recency_score(adv.get("publishedDate", ""))
    impact      = _level_scores(adv.get("impact",           "medium"))
    evidence    = _level_scores(adv.get("evidenceStrength", "medium"))
    credibility = _SOURCE_CREDIBILITY.get(adv.get("sourceType", "gpt_estimated"), 0.5)

    raw = (
        relevance * _RELEVANCE_WEIGHT +
        recency   * _RECENCY_WEIGHT   +
        impact    * _IMPACT_WEIGHT    +
        evidence  * _EVIDENCE_WEIGHT
    )
    return raw * credibility


def _relevance_score(adv: dict, skills_lower: list[str]) -> float:
    if not skills_lower:
        return 0.5
    text = " ".join([
        adv.get("title",   ""),
        adv.get("summary", ""),
        " ".join(adv.get("affectedSkills", [])),
    ]).lower()

    matched = sum(
        1 for skill in skills_lower
        if any(len(w) >= 4 and w in text for w in skill.split())
    )
    return min(1.0, matched / len(skills_lower))


def _recency_score(date_str: str) -> float:
    """1.0 pentru azi; scade cu 0.1 per 6 luni; minimum 0.1."""
    if not date_str:
        return 0.3
    try:
        pub      = datetime.fromisoformat(date_str[:10])
        age_days = max(0, (datetime.now() - pub).days)
        return max(0.1, 1.0 - (age_days / 180) * 0.1)
    except Exception:
        return 0.3


def _level_scores(level: str) -> float:
    return _LEVEL_SCORES.get(str(level).lower(), 0.5)
