"""
advancement_store.py — Cache local SQLite pentru advancement-uri tehnologice.

Stochează, deduplică și interogă advancement-urile colectate din surse externe
și interne. Fallback automat la [] dacă DB-ul nu este accesibil.

Locație DB: advancement_collectors/../advancements_cache.db (lângă acest fișier).
"""
from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_DB_PATH = Path(__file__).parent / "advancements_cache.db"

_DDL = """
CREATE TABLE IF NOT EXISTS advancements (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    title                TEXT    NOT NULL,
    summary              TEXT    DEFAULT '',
    source_type          TEXT    NOT NULL,
    source_name          TEXT    DEFAULT '',
    source_url           TEXT    NOT NULL UNIQUE,
    published_date       TEXT    DEFAULT '',
    affected_skills      TEXT    DEFAULT '[]',
    affected_occupations TEXT    DEFAULT '[]',
    maturity             TEXT    DEFAULT 'emerging',
    impact               TEXT    DEFAULT 'medium',
    evidence_strength    TEXT    DEFAULT 'medium',
    adoption_readiness   TEXT    DEFAULT 'low',
    confidence           TEXT    DEFAULT 'medium',
    inserted_at          TEXT    DEFAULT CURRENT_TIMESTAMP,
    updated_at           TEXT    DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_adv_source_type    ON advancements(source_type);
CREATE INDEX IF NOT EXISTS idx_adv_published_date ON advancements(published_date DESC);
"""


# ── Internals ─────────────────────────────────────────────────────────────────

def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


def _init_db() -> None:
    try:
        with _connect() as conn:
            conn.executescript(_DDL)
    except Exception as exc:
        logger.warning("advancement_store: init_db failed: %s", exc)


_init_db()


def _url_key(adv: dict) -> str:
    """Returnează URL-ul sau un hash stabil ca cheie unică."""
    url = (adv.get("sourceUrl") or "").strip()
    if url and url.startswith("http"):
        return url
    # fallback: hash pe titlu normalizat
    title = (adv.get("title") or "").lower().strip()
    return "hash://" + hashlib.md5(title.encode()).hexdigest()[:16]


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["affectedSkills"]      = json.loads(d.pop("affected_skills",  None) or "[]")
    d["affectedOccupations"] = json.loads(d.pop("affected_occupations", None) or "[]")
    d["sourceType"]          = d.pop("source_type")
    d["sourceName"]          = d.pop("source_name")
    d["sourceUrl"]           = d.pop("source_url")
    d["publishedDate"]       = d.pop("published_date")
    d["evidenceStrength"]    = d.pop("evidence_strength")
    d["adoptionReadiness"]   = d.pop("adoption_readiness")
    return d


def _jaccard(a: str, b: str) -> float:
    sa, sb = set(a.split()), set(b.split())
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


# ── Write ─────────────────────────────────────────────────────────────────────

def upsert(adv: dict) -> bool:
    """INSERT OR UPDATE pe source_url. Returnează True la succes."""
    try:
        now = datetime.now(timezone.utc).isoformat()
        url = _url_key(adv)
        with _connect() as conn:
            conn.execute("""
                INSERT INTO advancements
                    (title, summary, source_type, source_name, source_url,
                     published_date, affected_skills, affected_occupations,
                     maturity, impact, evidence_strength, adoption_readiness,
                     confidence, inserted_at, updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(source_url) DO UPDATE SET
                    title             = excluded.title,
                    summary           = excluded.summary,
                    affected_skills   = excluded.affected_skills,
                    maturity          = excluded.maturity,
                    impact            = excluded.impact,
                    updated_at        = excluded.updated_at
            """, (
                adv.get("title", ""),
                adv.get("summary", ""),
                adv.get("sourceType", ""),
                adv.get("sourceName", ""),
                url,
                adv.get("publishedDate", ""),
                json.dumps(adv.get("affectedSkills", []),      ensure_ascii=False),
                json.dumps(adv.get("affectedOccupations", []), ensure_ascii=False),
                adv.get("maturity",          "emerging"),
                adv.get("impact",            "medium"),
                adv.get("evidenceStrength",  "medium"),
                adv.get("adoptionReadiness", "low"),
                adv.get("confidence",        "medium"),
                now, now,
            ))
        return True
    except Exception as exc:
        logger.warning("advancement_store: upsert failed: %s", exc)
        return False


def upsert_many(advancements: list[dict]) -> int:
    """Upsert în batch. Returnează numărul de succese."""
    return sum(1 for adv in advancements if upsert(adv))


# ── Read ──────────────────────────────────────────────────────────────────────

def _fetch_rows(source_types: list[str] | None = None, limit: int = 1000) -> list[sqlite3.Row]:
    try:
        with _connect() as conn:
            if source_types:
                placeholders = ",".join("?" * len(source_types))
                return conn.execute(
                    f"SELECT * FROM advancements WHERE source_type IN ({placeholders})"
                    f" ORDER BY published_date DESC LIMIT ?",
                    [*source_types, limit],
                ).fetchall()
            return conn.execute(
                "SELECT * FROM advancements ORDER BY published_date DESC LIMIT ?", (limit,)
            ).fetchall()
    except Exception:
        return []


def _skill_relevance(adv: dict, skills_lower: list[str]) -> float:
    text = " ".join([
        adv.get("title", ""),
        adv.get("summary", ""),
        " ".join(adv.get("affectedSkills", [])),
    ]).lower()
    score = 0.0
    for skill in skills_lower:
        for word in skill.split():
            if len(word) >= 4 and word in text:
                score += 1.0
                break
    return score


def query_by_skills(
    skills: list[str],
    max_results: int = 10,
    source_types: list[str] | None = None,
) -> list[dict]:
    """
    Returnează advancement-urile relevante pentru skill-urile date,
    rankate după overlap de cuvinte cheie.
    """
    if not skills:
        return []
    rows = _fetch_rows(source_types)
    if not rows:
        return []

    skills_lower = [s.lower() for s in skills]
    scored: list[tuple[float, dict]] = []
    for row in rows:
        adv   = _row_to_dict(row)
        score = _skill_relevance(adv, skills_lower)
        if score > 0:
            scored.append((score, adv))

    scored.sort(key=lambda x: (-x[0], x[1].get("publishedDate", "")))
    return [adv for _, adv in scored[:max_results]]


def get_all(source_type: str | None = None, max_results: int = 500) -> list[dict]:
    """Returnează toate advancement-urile cu filtru opțional de sursă."""
    rows = _fetch_rows([source_type] if source_type else None, limit=max_results)
    return [_row_to_dict(r) for r in rows]


def count(source_type: str | None = None) -> int:
    """Numărul de advancement-uri din cache."""
    try:
        with _connect() as conn:
            if source_type:
                row = conn.execute(
                    "SELECT COUNT(*) FROM advancements WHERE source_type=?", (source_type,)
                ).fetchone()
            else:
                row = conn.execute("SELECT COUNT(*) FROM advancements").fetchone()
            return int(row[0]) if row else 0
    except Exception:
        return 0


def last_updated(source_type: str | None = None) -> Optional[str]:
    """Timestamp-ul ultimei actualizări (ISO 8601)."""
    try:
        with _connect() as conn:
            if source_type:
                row = conn.execute(
                    "SELECT MAX(updated_at) FROM advancements WHERE source_type=?", (source_type,)
                ).fetchone()
            else:
                row = conn.execute("SELECT MAX(updated_at) FROM advancements").fetchone()
            return row[0] if row else None
    except Exception:
        return None


def remove_duplicates() -> int:
    """
    Șterge înregistrări cu titluri similare (Jaccard > 0.85).
    Păstrează înregistrarea mai veche (id mai mic).
    Returnează numărul de șterse.
    """
    try:
        rows   = _fetch_rows()
        seen:  list[tuple[int, str]] = []   # (id, title_lower)
        delete: list[int] = []

        for row in rows:
            rid   = row["id"]
            title = (row["title"] or "").lower().strip()
            is_dup = any(_jaccard(title, t) > 0.85 for _, t in seen)
            if is_dup:
                delete.append(rid)
            else:
                seen.append((rid, title))

        if delete:
            with _connect() as conn:
                conn.execute(
                    f"DELETE FROM advancements WHERE id IN ({','.join('?'*len(delete))})",
                    delete,
                )
        return len(delete)
    except Exception as exc:
        logger.warning("advancement_store: remove_duplicates failed: %s", exc)
        return 0
