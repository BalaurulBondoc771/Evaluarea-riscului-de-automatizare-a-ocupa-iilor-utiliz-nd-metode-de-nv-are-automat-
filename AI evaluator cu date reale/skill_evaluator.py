"""
skill_evaluator.py — AI 2: Evaluator avansat al riscului de automatizare.

Arhitectura de scoring este hibridă:
  1. GPT-4o analizează skill-urile și propune un scor sugerat.
  2. O formulă deterministă calculează un scor pe baza distribuției riscurilor per skill.
  3. Scorul final = 50% deterministic + 50% GPT — mai transparent și reproductibil.

Câmpuri returnate pentru transparență științifică:
  finalAutomationScore — scorul final hibrid (afișat)
  gptSuggestedScore    — ce a propus GPT-4o
  deterministicScore   — ce a calculat formula
  scoringMethod        — "hybrid_50_deterministic_50_gpt"
  skillsSource         — "gpt_estimated" sau "dataset_esco"
  scoreChange          — recalculat întotdeauna: final - initial (nu e preluat din GPT)
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Optional

_HERE = Path(__file__).parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

_DEMO_FILE = Path(__file__).parent / "demo_results.json"

try:
    from openai import OpenAI
    _OPENAI_AVAILABLE = True
except ImportError:
    _OPENAI_AVAILABLE = False

# Cache de advancement-uri externe — opțional, fallback silențios
try:
    import advancement_store as _store
    import advancement_ranker as _ranker
    _STORE_AVAILABLE = True
except ImportError:
    _STORE_AVAILABLE = False
    _store = None  # type: ignore[assignment]
    _ranker = None  # type: ignore[assignment]


# ── System prompt ─────────────────────────────────────────────────────────────
_SYSTEM_PROMPT = (
    "Ești un analist expert al pieței muncii, specializat în evaluarea riscului "
    "de automatizare al ocupațiilor. Analizezi ocupații din perspectivă economică "
    "și tehnologică, oferind evaluări structurate și formulate probabilistic.\n\n"
    "Regulă critică: returnezi EXCLUSIV un obiect JSON valid, fără text suplimentar.\n"
    "Toate câmpurile de text trebuie scrise în limba română.\n"
    "Nu faci predicții absolute. Folosești formulări probabilistice: "
    "\"estimarea sugerează\", \"prezintă risc mai ridicat/scăzut\", \"este posibil ca\"."
)


# ── Prompt template ───────────────────────────────────────────────────────────
_PROMPT_TEMPLATE = """\
Analizează riscul de automatizare pentru ocupația: "{job_title}"

Date inițiale (AI 1 — model LightGBM antrenat pe date ESCO):
  • Scor inițial: {initial_score}/100
  • Explicație inițială: {initial_explanation}
{extra_context}
Returnează EXACT un obiect JSON cu această structură (fără text înainte sau după):

{{
  "gptSuggestedScore": <integer 0-100 — scorul pe care îl sugerezi tu>,
  "confidenceLevel": <"low" | "medium" | "high">,
  "skillAnalysis": [
    {{
      "skill": "<denumirea skill-ului în română>",
      "difficulty": <"low" | "medium" | "high" — dificultatea de automatizare>,
      "automationRisk": <"low" | "medium" | "high">,
      "reason": "<explicație scurtă în română — max 2 propoziții>"
    }}
  ],
  "vulnerableSkills": ["<skill>", ...],
  "protectedSkills": ["<skill>", ...],
  "relevantTechnologicalAdvancements": [
    {{
      "title": "<titlul avanstamentului tehnologic>",
      "affectedSkills": ["<skill>"],
      "maturity": <"emerging" | "growing" | "high">,
      "impact": <"low" | "medium" | "high">,
      "reason": "<de ce afectează aceste skill-uri — max 2 propoziții în română>"
    }}
  ],
  "finalExplanation": "<explicație clară, academică, 3-5 propoziții în română>",
  "scoreAdjustmentReason": "<de ce scorul final diferă de cel inițial — 1-2 propoziții>",
  "recommendations": [
    {{
      "skill": "<skill recomandat pentru reducerea riscului, în română>",
      "reason": "<de ce reduce riscul — 1 propoziție>"
    }}
  ],
  "confidenceReason": "<de ce nivelul de încredere este acesta — 1-2 propoziții>",
  "replacementRisk": <integer 0-100 — probabilitatea înlocuirii COMPLETE a jobului>,
  "aiImpactScore": <integer 0-100 — gradul în care AI va MODIFICA modul de lucru, chiar fără înlocuire>,
  "transferableSkills": ["<skill transferabil în alte domenii>", ...],
  "alternativeOccupations": [
    {{
      "title": "<ocupație alternativă cu risc mai scăzut, în română>",
      "reason": "<de ce e mai puțin expusă — 1 propoziție>"
    }}
  ]
}}

Criterii de evaluare per skill:
  1. Repetitivitate — task-uri rutiniere → risc ridicat
  2. Nivel de digitalizare — lucrul cu date/computere → risc ridicat
  3. Creativitate necesară — design, inovație, strategie → protejat
  4. Interacțiune umană esențială — empatie, negociere, relații → protejat
  5. Dexteritate fizică precisă — chirurgie, artizanat fin → protejat
  6. Responsabilitate legală/etică — decizii medicale, juridice → protejat
  7. Existența unor instrumente AI actuale care pot face acel lucru
  8. Bariere de adoptare (costuri, reglementări, rezistență organizațională)

Diferență esențială între cele două scoruri noi:
  replacementRisk = probabilitatea că jobul să DISPARĂ COMPLET (toate task-urile automatizabile)
  aiImpactScore   = gradul în care AI va TRANSFORMA activitățile zilnice, chiar dacă jobul nu dispare
  Exemplu: profesor — replacementRisk: 15, aiImpactScore: 70
           (profesorul nu va fi înlocuit, dar predarea, evaluarea și pregătirea se schimbă semnificativ)

Identifică 5-8 skill-uri reprezentative pentru această ocupație.
Identifică 2-4 avanstamente tehnologice relevante și existente (nu speculative).
Identifică 3-5 recomandări de skill-uri care reduc riscul de automatizare.
Identifică 2-4 skill-uri transferabile din această ocupație în alte domenii.
Identifică 2-3 ocupații alternative cu risc mai scăzut de automatizare.
Dacă nu există avanstamente relevante majore, menționează asta în finalExplanation.

Returnează NUMAI obiectul JSON."""


# ── Constante pentru formula deterministă ─────────────────────────────────────
_RISK_WEIGHTS = {"high": 1.0, "medium": 0.5, "low": 0.0}
_ADV_IMPACT_BONUS = {"high": 3.5, "medium": 1.5, "low": 0.5}
_MAX_ADV_BONUS = 10  # puncte maxime din avanstamente
_HYBRID_GPT_WEIGHT = 0.50
_HYBRID_DET_WEIGHT = 0.50


def evaluate_automation_risk(
    job_title: str,
    initial_score: float,
    initial_explanation: str,
    tasks: Optional[list[str]] = None,
    skills: Optional[list[str]] = None,
    openai_api_key: Optional[str] = None,
) -> dict:
    """
    AI 2: Evaluează avansat riscul de automatizare al unei ocupații.

    Flux:
      1. Apelează GPT-4o pentru analiza skill-urilor și un scor sugerat.
      2. Aplică formula deterministă pe skill-urile returnate de GPT.
      3. Calculează scorul hibrid final (50% deterministic + 50% GPT).
      4. Validează și normalizează toate câmpurile.

    Args:
        job_title:           Denumirea ocupației (din COR/ESCO)
        initial_score:       Scorul AI 1 (0-100)
        initial_explanation: Explicația generată de AI 1
        tasks:               Sarcini cunoscute (opțional — din dataset)
        skills:              Skill-uri cunoscute (opțional — din dataset ESCO)
        openai_api_key:      Cheie API OpenAI (fallback: env var OPENAI_API_KEY)

    Returns:
        Dict complet cu scor final, transparența scoringului, analiza skill-urilor.
        Dacă apare o eroare, câmpul "error" este populat și restul sunt None/[].
    """
    if not _OPENAI_AVAILABLE:
        return _error_result(
            "Librăria openai nu este instalată. Rulează: pip install openai>=1.30.0"
        )

    api_key = openai_api_key or os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return _error_result(
            "Cheia API OpenAI nu este configurată. "
            "Adaug-o în .streamlit/secrets.toml sau ca variabilă de mediu OPENAI_API_KEY."
        )

    # Sursă skill-uri: dacă vin din dataset ESCO, marcăm "dataset_esco"
    skills_source = "dataset_esco" if skills else "gpt_estimated"

    extra_lines: list[str] = []
    if tasks:
        extra_lines.append(f"  • Sarcini din dataset: {', '.join(tasks[:8])}")
    if skills:
        extra_lines.append(f"  • Skill-uri din dataset ESCO: {', '.join(skills[:12])}")

    # Adaugă advancement-uri cache-uite ca context pentru GPT (max 8 din cache, top 5 în prompt)
    cached_advancements: list[dict] = []
    cache_last_updated: str | None = None
    if _STORE_AVAILABLE and _store is not None:
        query_skills = list(skills or []) + [job_title]
        cached_advancements = _store.query_by_skills(query_skills, max_results=8)
        cache_last_updated  = _store.last_updated()
        if cached_advancements:
            # Injectăm maxim 5 în prompt pentru a nu crește costul/confuzia GPT
            prompt_adv = cached_advancements[:5]
            extra_lines.append(
                "  • Avanstamente tehnologice relevante din cache extern (surse reale):\n"
                + "\n".join(
                    f"    – [{adv.get('sourceType','?').upper()}] {adv.get('title','')} "
                    f"(impact: {adv.get('impact','?')}, publicat: {adv.get('publishedDate','?')[:7]})"
                    for adv in prompt_adv
                )
            )

    extra_context = (
        "\nDate suplimentare din dataset (surse reale):\n"
        + "\n".join(extra_lines) + "\n"
    ) if extra_lines else ""

    prompt = _PROMPT_TEMPLATE.format(
        job_title=job_title,
        initial_score=int(initial_score),
        initial_explanation=initial_explanation.strip(),
        extra_context=extra_context,
    )

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user",   "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.25,
            max_tokens=2500,
            timeout=45,
        )
        raw = response.choices[0].message.content
        gpt_raw = json.loads(raw)

    except json.JSONDecodeError as exc:
        return _error_result(f"Răspunsul AI nu este JSON valid: {exc}")
    except Exception as exc:
        return _error_result(f"Eroare la apelul API: {exc}")

    # ── Validare și normalizare ────────────────────────────────────────────────
    result = _validate_and_normalize(
        gpt_raw, initial_score, skills_source,
        cached_advancements=cached_advancements,
        cache_last_updated=cache_last_updated,
    )
    return result


# ── Funcții interne ───────────────────────────────────────────────────────────

def _validate_and_normalize(
    gpt_raw: dict,
    initial_score: float,
    skills_source: str,
    cached_advancements: list[dict] | None = None,
    cache_last_updated: str | None = None,
) -> dict:
    """
    Validează strict răspunsul GPT și calculează scorul hibrid final.

    Scorul final NU este preluat direct din GPT — este calculat hibrid:
      deterministicScore = funcție de distribuția riscurilor per skill + avanstamente
      gptSuggestedScore  = ce a propus GPT (validat și limitat 0-100)
      finalAutomationScore = round(det * 0.5 + gpt * 0.5)
      scoreChange = finalAutomationScore - initial_score  (recalculat, nu din GPT)
    """
    # ── 1. Validare skillAnalysis ──────────────────────────────────────────────
    raw_skills = gpt_raw.get("skillAnalysis", [])
    if not isinstance(raw_skills, list):
        raw_skills = []

    skill_analysis: list[dict] = []
    for item in raw_skills:
        if not isinstance(item, dict):
            continue
        skill_analysis.append({
            "skill":          str(item.get("skill", "—")),
            "difficulty":     _coerce_level(item.get("difficulty"), "medium"),
            "automationRisk": _coerce_level(item.get("automationRisk"), "medium"),
            "reason":         str(item.get("reason", "")),
        })

    # ── 2. Scor deterministic din skill-uri ───────────────────────────────────
    det_score = _compute_deterministic_score(skill_analysis, initial_score)

    # ── 3. Avanstamente și bonus ──────────────────────────────────────────────
    raw_adv = gpt_raw.get("relevantTechnologicalAdvancements", [])
    if not isinstance(raw_adv, list):
        raw_adv = []

    advancements: list[dict] = []
    for adv in raw_adv:
        if not isinstance(adv, dict):
            continue
        advancements.append({
            "title":          str(adv.get("title", "—")),
            "affectedSkills": adv.get("affectedSkills", []) if isinstance(adv.get("affectedSkills"), list) else [],
            "maturity":       _coerce_maturity(adv.get("maturity")),
            "impact":         _coerce_level(adv.get("impact"), "medium"),
            "reason":         str(adv.get("reason", "")),
            "sourceType":     "gpt_estimated",
            "sourceName":     "GPT-4o (estimat)",
            "sourceUrl":      "",
            "publishedDate":  "",
        })

    # ── Îmbogățire cu advancement-uri din cache extern ───────────────────────
    if cached_advancements and _STORE_AVAILABLE and _ranker is not None:
        all_skills = [s.get("skill", "") for s in skill_analysis]
        merged     = _ranker.rank_advancements(
            advancements + cached_advancements,
            skills=all_skills,
            max_results=6,
        )
        # Normalizare câmpuri pentru advancement-uri din cache
        normalized_cache: list[dict] = []
        for cadv in merged:
            if cadv.get("sourceType") in ("gpt_estimated",):
                normalized_cache.append(cadv)
            else:
                normalized_cache.append({
                    "title":          cadv.get("title", "—"),
                    "affectedSkills": cadv.get("affectedSkills", []),
                    "maturity":       _coerce_maturity(cadv.get("maturity")),
                    "impact":         _coerce_level(cadv.get("impact"), "medium"),
                    "reason":         cadv.get("summary", cadv.get("reason", "")),
                    "sourceType":     cadv.get("sourceType", "internal_categorized"),
                    "sourceName":     cadv.get("sourceName", ""),
                    "sourceUrl":      cadv.get("sourceUrl", ""),
                    "publishedDate":  cadv.get("publishedDate", ""),
                })
        advancements = normalized_cache

    adv_bonus = min(
        _MAX_ADV_BONUS,
        sum(_ADV_IMPACT_BONUS.get(a["impact"], 1.0) for a in advancements),
    )

    det_score_with_adv = min(100.0, det_score + adv_bonus)

    # ── 4. Scor GPT sugerat ───────────────────────────────────────────────────
    gpt_suggested_raw = gpt_raw.get("gptSuggestedScore", initial_score)
    try:
        gpt_suggested = max(0, min(100, int(gpt_suggested_raw)))
    except (ValueError, TypeError):
        gpt_suggested = int(initial_score)

    # ── 5. Scor hibrid final ──────────────────────────────────────────────────
    hybrid_raw = det_score_with_adv * _HYBRID_DET_WEIGHT + gpt_suggested * _HYBRID_GPT_WEIGHT
    final_score = max(0, min(100, round(hybrid_raw)))

    # scoreChange recalculat întotdeauna din final - initial (nu din GPT)
    score_change = final_score - round(initial_score)

    # ── 6. Câmpuri text ───────────────────────────────────────────────────────
    confidence = _coerce_level(gpt_raw.get("confidenceLevel"), "medium")

    vuln = gpt_raw.get("vulnerableSkills", [])
    prot = gpt_raw.get("protectedSkills", [])
    vulnerable_skills = [str(s) for s in vuln] if isinstance(vuln, list) else []
    protected_skills  = [str(s) for s in prot] if isinstance(prot, list) else []

    final_explanation = str(gpt_raw.get("finalExplanation", ""))
    score_adj_reason  = str(gpt_raw.get("scoreAdjustmentReason", ""))

    # ── 7. Câmpuri noi: recomandări, impact, transferabilitate ────────────────
    raw_rec = gpt_raw.get("recommendations", [])
    recommendations = [
        {"skill": str(r.get("skill", "")), "reason": str(r.get("reason", ""))}
        for r in raw_rec if isinstance(r, dict)
    ] if isinstance(raw_rec, list) else []

    confidence_reason = str(gpt_raw.get("confidenceReason", ""))

    try:
        replacement_risk = max(0, min(100, int(gpt_raw.get("replacementRisk", round(final_score * 0.65)))))
    except (ValueError, TypeError):
        replacement_risk = max(0, min(100, round(final_score * 0.65)))

    try:
        ai_impact_score = max(0, min(100, int(gpt_raw.get("aiImpactScore", min(100, round(final_score * 1.15))))))
    except (ValueError, TypeError):
        ai_impact_score = max(0, min(100, round(final_score * 1.15)))

    raw_trans = gpt_raw.get("transferableSkills", [])
    transferable_skills = [str(s) for s in raw_trans] if isinstance(raw_trans, list) else []

    raw_alt = gpt_raw.get("alternativeOccupations", [])
    alternative_occupations = [
        {"title": str(a.get("title", "")), "reason": str(a.get("reason", ""))}
        for a in raw_alt if isinstance(a, dict)
    ] if isinstance(raw_alt, list) else []

    # ── Metadata surse externe ────────────────────────────────────────────────
    _gpt_only_sources = {"gpt_estimated", "internal_categorized"}
    external_adv  = [a for a in advancements if a.get("sourceType") not in _gpt_only_sources]
    ext_used      = len(external_adv) > 0
    fallback_used = not ext_used

    return {
        "error":               None,

        # ── Scor principal ──
        "finalAutomationScore":  final_score,
        "scoreChange":           score_change,
        "confidenceLevel":       confidence,

        # ── Transparență scoring ──
        "gptSuggestedScore":     gpt_suggested,
        "deterministicScore":    round(det_score_with_adv),
        "advancementsBonus":     round(adv_bonus, 1),
        "scoringMethod":         "hybrid_50_deterministic_50_gpt",
        "skillsSource":          skills_source,

        # ── Analiza skill-urilor ──
        "skillAnalysis":                     skill_analysis,
        "vulnerableSkills":                  vulnerable_skills,
        "protectedSkills":                   protected_skills,

        # ── Avanstamente ──
        "relevantTechnologicalAdvancements": advancements,

        # ── Metadata surse externe ──
        "externalSourcesUsed":       ext_used,
        "externalAdvancementsCount": len(external_adv),
        "fallbackUsed":              fallback_used,
        "cacheLastUpdated":          cache_last_updated,

        # ── Impact și orientare ──
        "replacementRisk":       replacement_risk,
        "aiImpactScore":         ai_impact_score,
        "recommendations":       recommendations,
        "confidenceReason":      confidence_reason,
        "transferableSkills":    transferable_skills,
        "alternativeOccupations": alternative_occupations,

        # ── Explicație ──
        "finalExplanation":      final_explanation,
        "scoreAdjustmentReason": score_adj_reason,
        "limitations": (
            "Această analiză reprezintă o estimare probabilistică bazată pe informații disponibile. "
            "Nu constituie o predicție certă privind evoluția pieței muncii."
        ),
    }


def _compute_deterministic_score(skill_analysis: list[dict], initial_score: float) -> float:
    """
    Calculează un scor deterministic pe baza distribuției riscurilor per skill.

    Formula:
      skill_risk_ratio = (high*1.0 + medium*0.5 + low*0.0) / n_skills
      skill_based_score = skill_risk_ratio * 100
      deterministic = initial * 0.40 + skill_based * 0.60
    """
    if not skill_analysis:
        return float(initial_score)

    total = len(skill_analysis)
    weighted_sum = sum(
        _RISK_WEIGHTS.get(s.get("automationRisk", "medium"), 0.5)
        for s in skill_analysis
    )
    skill_risk_ratio = weighted_sum / total
    skill_based_score = skill_risk_ratio * 100

    return initial_score * 0.40 + skill_based_score * 0.60


def _coerce_level(value: object, default: str = "medium") -> str:
    """Forțează valoarea la one of: low / medium / high."""
    if str(value).lower() in ("low", "medium", "high"):
        return str(value).lower()
    return default


def _coerce_maturity(value: object) -> str:
    """Forțează valoarea la one of: emerging / growing / high."""
    if str(value).lower() in ("emerging", "growing", "high"):
        return str(value).lower()
    return "growing"


def load_demo_result(job_name: str) -> Optional[dict]:
    """
    Returnează un rezultat pre-salvat pentru modul demonstrație.

    Caută în demo_results.json un exemplu al cărui matchKeywords
    apare ca substring în denumirea ocupației primite.

    Args:
        job_name: Denumirea ocupației selectate în UI.

    Returns:
        Dict-ul result pre-calculat sau None dacă nu există potrivire.
    """
    if not _DEMO_FILE.exists():
        return None
    try:
        with open(_DEMO_FILE, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        job_lower = job_name.lower()
        for example in data.get("examples", []):
            keywords = [str(k).lower() for k in example.get("matchKeywords", [])]
            if any(kw in job_lower for kw in keywords):
                return example.get("result")
    except Exception:
        pass
    return None


def _error_result(message: str) -> dict:
    """Returnează un dict de eroare cu toate câmpurile așteptate goale."""
    return {
        "error":                             message,
        "finalAutomationScore":              None,
        "scoreChange":                       None,
        "confidenceLevel":                   None,
        "gptSuggestedScore":                 None,
        "deterministicScore":                None,
        "advancementsBonus":                 None,
        "scoringMethod":                     None,
        "skillsSource":                      None,
        "skillAnalysis":                     [],
        "vulnerableSkills":                  [],
        "protectedSkills":                   [],
        "relevantTechnologicalAdvancements": [],
        "externalSourcesUsed":               False,
        "externalAdvancementsCount":         0,
        "fallbackUsed":                      True,
        "cacheLastUpdated":                  None,
        "replacementRisk":                   None,
        "aiImpactScore":                     None,
        "recommendations":                   [],
        "confidenceReason":                  None,
        "transferableSkills":                [],
        "alternativeOccupations":            [],
        "finalExplanation":                  None,
        "scoreAdjustmentReason":             None,
        "limitations":                       None,
    }
