"""
huggingface_collector.py — Colector pentru modele populare de pe Hugging Face Hub.

Interogă API-ul public HF Hub (fără autentificare) și returnează modele
cu impact mare din task-urile AI relevante pentru piața muncii.

Endpoint: https://huggingface.co/api/models
Documentație: https://huggingface.co/docs/hub/api
"""
from __future__ import annotations

import json
import logging
import urllib.parse
import urllib.request

from advancement_collectors import BaseCollector, make_advancement

logger = logging.getLogger(__name__)

_HF_API = "https://huggingface.co/api/models"

# Task HF → (descriere, skill-uri afectate în română)
_TASK_MAP: dict[str, tuple[str, list[str]]] = {
    "text-generation": (
        "Modele de generare text (LLM)",
        ["redactare text", "copywriting", "suport clienți", "documentare", "raportare"],
    ),
    "automatic-speech-recognition": (
        "Recunoaștere automată a vorbirii",
        ["transcriere", "stenografie", "call center", "suport clienți vocal"],
    ),
    "image-classification": (
        "Clasificare imagini (Computer Vision)",
        ["inspecție vizuală", "control calitate", "analiză imagini", "scanare documente"],
    ),
    "object-detection": (
        "Detecție obiecte (Computer Vision)",
        ["inspecție vizuală", "monitorizare", "supraveghere", "sortare"],
    ),
    "translation": (
        "Traducere automată (NLP)",
        ["traducere", "traducere simultană", "comunicare internațională"],
    ),
    "summarization": (
        "Rezumare automată de text",
        ["documentare", "raportare", "cercetare documentară", "note clinice"],
    ),
    "text-classification": (
        "Clasificare text",
        ["procesare formulare", "suport clienți", "conformitate", "analiză date"],
    ),
    "question-answering": (
        "Răspuns automat la întrebări (QA)",
        ["suport clienți", "asistență juridică", "tutoriat"],
    ),
    "token-classification": (
        "Extragere entități (NER)",
        ["analiză juridică", "procesare contracte", "codificare medicală"],
    ),
    "image-to-text": (
        "Descriere automată de imagini",
        ["scanare documente", "accesibilitate", "analiză imagini medicale"],
    ),
}


def _maturity(downloads: int) -> str:
    if downloads >= 1_000_000:
        return "high"
    if downloads >= 100_000:
        return "growing"
    return "emerging"


def _adoption(downloads: int) -> str:
    if downloads >= 1_000_000:
        return "high"
    if downloads >= 100_000:
        return "medium"
    return "low"


def _impact(likes: int) -> str:
    if likes >= 1_000:
        return "high"
    if likes >= 100:
        return "medium"
    return "low"


class HuggingFaceCollector(BaseCollector):
    """
    Colectează modele populare de pe Hugging Face Hub după task.
    Nu necesită autentificare pentru API-ul public.
    """

    SOURCE_TYPE = "huggingface"

    def __init__(
        self,
        tasks: list[str] | None = None,
        min_downloads: int = 10_000,
    ):
        self.tasks         = tasks or list(_TASK_MAP.keys())
        self.min_downloads = min_downloads

    def collect(self, max_results: int = 50) -> list[dict]:
        results:   list[dict] = []
        seen_urls: set[str]   = set()
        per_task = max(3, max_results // len(self.tasks))

        for task in self.tasks:
            try:
                batch = self._fetch_task(task, per_task)
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
                logger.warning("huggingface_collector: task %s failed: %s", task, exc)

        return results

    def _fetch_task(self, task: str, limit: int) -> list[dict]:
        params = urllib.parse.urlencode({
            "filter": task,
            "sort":   "downloads",
            "limit":  limit,
            "full":   "False",
        })
        url = f"{_HF_API}?{params}"
        req = urllib.request.Request(url, headers={"User-Agent": "AdvancementCollector/1.0"})

        with urllib.request.urlopen(req, timeout=15) as resp:
            models = json.loads(resp.read().decode("utf-8"))

        if not isinstance(models, list):
            return []

        task_label, skills = _TASK_MAP.get(task, ("Model AI", []))
        results: list[dict] = []

        for model in models:
            if not isinstance(model, dict):
                continue

            model_id  = str(model.get("modelId") or model.get("id") or "")
            downloads = int(model.get("downloads") or 0)
            likes     = int(model.get("likes")     or 0)
            created   = str(model.get("createdAt") or "")[:10]

            if downloads < self.min_downloads or not model_id:
                continue

            results.append(make_advancement(
                title=f"{task_label}: {model_id}",
                summary=(
                    f"Model popular pe Hugging Face pentru task-ul '{task}'. "
                    f"Downloads: {downloads:,}. Likes: {likes}."
                ),
                source_type="huggingface",
                source_name=f"Hugging Face Hub — {task}",
                source_url=f"https://huggingface.co/{model_id}",
                published_date=created,
                affected_skills=skills,
                maturity=_maturity(downloads),
                impact=_impact(likes),
                evidence_strength="medium",
                adoption_readiness=_adoption(downloads),
                confidence="high",
            ))

        return results
