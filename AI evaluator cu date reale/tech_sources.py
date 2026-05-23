"""
tech_sources.py — Bază de cunoștințe despre avanstamente tehnologice.

NOTĂ METODOLOGICĂ:
  Versiunea actuală folosește o bază internă de categorii tehnologice curate manual
  (sourceType: "internal_categorized"), nu date extrase în timp real din surse externe.

  Arhitectura este pregătită pentru conectarea la API-uri reale:
    - arXiv API        → https://arxiv.org/help/api/
    - OpenAlex API     → https://docs.openalex.org/
    - Hugging Face Hub → https://huggingface.co/docs/hub/api
    - Papers with Code → https://paperswithcode.com/api/v1/

  Când API-urile vor fi conectate, câmpul sourceType va deveni "arxiv", "openalex" etc.
  Câmpul sourceUrl va conține link-ul direct la sursa primară.
"""

from __future__ import annotations


# ── Baza internă de avanstamente tehnologice ─────────────────────────────────
# Câmpuri standard pentru fiecare intrare:
#   title          — denumirea avanstamentului
#   category       — domeniul tehnologic principal
#   affectedSkills — skill-uri afectate (pentru matching și afișare)
#   maturity       — gradul de maturitate: "emerging" | "growing" | "high"
#   impact         — impactul estimat: "low" | "medium" | "high"
#   sourceType     — "internal_categorized" (curent) | "arxiv" | "openalex" | "huggingface"
#   sourceName     — organizația sau publicația sursă
#   sourceUrl      — link de referință (documentație publică, nu date live)
#   publishedDate  — perioada în care avanstamentul a devenit semnificativ

_ADVANCEMENTS: list[dict] = [
    {
        "title": "Large Language Models (GPT-4o, Claude 3, Gemini 1.5)",
        "category": "Natural Language Processing",
        "affectedSkills": [
            "redactare text", "traducere", "comunicare scrisă", "documentare",
            "raportare", "suport clienți", "copywriting", "cercetare documentară",
            "introducere date", "procesare formulare", "asistență juridică",
        ],
        "maturity": "high",
        "impact": "high",
        "sourceType": "internal_categorized",
        "sourceName": "OpenAI / Anthropic / Google DeepMind",
        "sourceUrl": "https://openai.com/research/",
        "publishedDate": "2022-2024",
        "reason": (
            "Modelele LLM pot genera, analiza și edita text la nivel profesional. "
            "Ocupațiile bazate pe procesarea limbajului natural sunt puternic afectate."
        ),
    },
    {
        "title": "Computer Vision (YOLO v9, SAM 2, Vision Transformers)",
        "category": "Computer Vision",
        "affectedSkills": [
            "inspecție vizuală", "control calitate", "sortare", "monitorizare",
            "supraveghere", "analiză imagini", "radiologie", "patologie",
            "analiză satelitară", "scanare documente",
        ],
        "maturity": "high",
        "impact": "high",
        "sourceType": "internal_categorized",
        "sourceName": "Meta AI / Google DeepMind / Papers with Code",
        "sourceUrl": "https://paperswithcode.com/methods/category/object-detection",
        "publishedDate": "2020-2024",
        "reason": (
            "Sistemele de computer vision detectează și clasifică obiecte vizuale "
            "cu acuratețe supraomană în condiții controlate."
        ),
    },
    {
        "title": "Robotic Process Automation cu AI (UiPath, Automation Anywhere)",
        "category": "Process Automation",
        "affectedSkills": [
            "introducere date", "contabilitate primară", "facturare", "salarizare",
            "procesare formulare", "arhivare", "administrație", "birotică",
            "reconciliere bancară", "raportare financiară",
        ],
        "maturity": "high",
        "impact": "high",
        "sourceType": "internal_categorized",
        "sourceName": "UiPath / Automation Anywhere / Gartner",
        "sourceUrl": "https://www.uipath.com/rpa/robotic-process-automation",
        "publishedDate": "2018-2024",
        "reason": (
            "RPA cu AI automatizează task-uri repetitive bazate pe reguli. "
            "Integrarea cu modele AI extinde capabilitățile la date nestructurate."
        ),
    },
    {
        "title": "Generative AI pentru imagini (DALL-E 3, Midjourney v6, Stable Diffusion 3)",
        "category": "Generative AI — Image",
        "affectedSkills": [
            "design grafic", "ilustrație", "concept art", "marketing vizual",
            "editare foto", "conținut vizual", "design publicitar", "logo design",
            "prototipare vizuală",
        ],
        "maturity": "high",
        "impact": "medium",
        "sourceType": "internal_categorized",
        "sourceName": "OpenAI / Stability AI / Midjourney",
        "sourceUrl": "https://openai.com/dall-e-3",
        "publishedDate": "2022-2024",
        "reason": (
            "Generarea de imagini AI accelerează producția de conținut vizual. "
            "Creativitatea strategică și identitatea de brand rămân activități umane."
        ),
    },
    {
        "title": "AI pentru generare de cod (GitHub Copilot, Cursor, Devin)",
        "category": "Software Development AI",
        "affectedSkills": [
            "programare", "dezvoltare software", "scripting", "testare software",
            "debugging", "dezvoltare web", "automatizare", "baze de date",
        ],
        "maturity": "high",
        "impact": "medium",
        "sourceType": "internal_categorized",
        "sourceName": "GitHub / OpenAI / Cognition Labs",
        "sourceUrl": "https://github.com/features/copilot",
        "publishedDate": "2021-2024",
        "reason": (
            "AI-ul asistă și accelerează scrierea codului de rutină. "
            "Arhitectura complexă, debugging-ul avansat și deciziile de design rămân umane."
        ),
    },
    {
        "title": "ML pentru optimizare logistică și lanțuri de aprovizionare",
        "category": "Operations Research / ML",
        "affectedSkills": [
            "logistică", "lanț de aprovizionare", "gestionare stocuri", "planificare",
            "rutare", "prognoză cerere", "gestiune depozit", "transport",
            "dispecerat", "planificare producție",
        ],
        "maturity": "high",
        "impact": "high",
        "sourceType": "internal_categorized",
        "sourceName": "Amazon / Google / arXiv Operations Research",
        "sourceUrl": "https://arxiv.org/search/?query=supply+chain+optimization&searchtype=all",
        "publishedDate": "2019-2024",
        "reason": (
            "Algoritmii ML pot planifica și gestiona lanțurile logistice "
            "mai eficient decât procesele manuale, reducând costurile operaționale."
        ),
    },
    {
        "title": "Roboți industriali colaborativi cu AI (cobots)",
        "category": "Industrial Robotics",
        "affectedSkills": [
            "asamblare", "sudură", "vopsire", "ambalare", "manipulare materiale",
            "operare mașini", "producție industrială", "control calitate producție",
        ],
        "maturity": "growing",
        "impact": "high",
        "sourceType": "internal_categorized",
        "sourceName": "Universal Robots / Boston Dynamics / IFR",
        "sourceUrl": "https://ifr.org/free-downloads/",
        "publishedDate": "2017-2024",
        "reason": (
            "Cobots cu AI pot lucra alături de oameni și pot fi reprogramați rapid. "
            "Adoptarea este accelerată de scăderea costurilor și reglementările de siguranță."
        ),
    },
    {
        "title": "AI pentru analiză financiară și audit (BloombergGPT, FinGPT)",
        "category": "Financial AI",
        "affectedSkills": [
            "analiză financiară", "contabilitate", "audit", "evaluare risc",
            "investiții", "banking", "asigurări", "pregătire declarații fiscale",
            "conformitate", "raportare financiară",
        ],
        "maturity": "high",
        "impact": "medium",
        "sourceType": "internal_categorized",
        "sourceName": "Bloomberg / Palantir / arXiv Finance",
        "sourceUrl": "https://arxiv.org/abs/2303.17564",
        "publishedDate": "2020-2024",
        "reason": (
            "AI-ul poate analiza seturi mari de date financiare și detecta pattern-uri. "
            "Responsabilitatea legală și relațiile cu clienții rămân activități umane."
        ),
    },
    {
        "title": "NLP pentru documentare medicală (Nuance DAX, Med-PaLM 2)",
        "category": "Medical AI / Clinical NLP",
        "affectedSkills": [
            "documentare medicală", "note clinice", "codificare medicală",
            "transcriere consultații", "rapoarte de laborator", "asistență diagnostic",
        ],
        "maturity": "growing",
        "impact": "medium",
        "sourceType": "internal_categorized",
        "sourceName": "Nuance (Microsoft) / Google Health / arXiv Medical AI",
        "sourceUrl": "https://arxiv.org/abs/2305.09617",
        "publishedDate": "2021-2024",
        "reason": (
            "NLP medical poate transcrie și structura automat notele clinice. "
            "Diagnosticul final și responsabilitatea etică rămân medicale."
        ),
    },
    {
        "title": "AI pentru educație personalizată (Khan Academy Khanmigo, Duolingo AI)",
        "category": "Educational Technology AI",
        "affectedSkills": [
            "predare", "tutoriat", "formare profesională", "e-learning",
            "design curriculum", "evaluare", "corectare lucrări",
        ],
        "maturity": "growing",
        "impact": "low",
        "sourceType": "internal_categorized",
        "sourceName": "Khan Academy / Duolingo / arXiv EdTech",
        "sourceUrl": "https://www.khanacademy.org/khan-labs",
        "publishedDate": "2022-2024",
        "reason": (
            "AI-ul poate personaliza conținutul educațional și oferi feedback instant. "
            "Mentoratul, motivarea și relația educator-student rămân esențiale și umane."
        ),
    },
    {
        "title": "Speech-to-text și voice AI (OpenAI Whisper, ElevenLabs)",
        "category": "Speech Recognition / Voice AI",
        "affectedSkills": [
            "transcriere", "stenografie", "call center", "secretariat",
            "suport clienți vocal", "voice-over", "traducere simultană",
        ],
        "maturity": "high",
        "impact": "high",
        "sourceType": "internal_categorized",
        "sourceName": "OpenAI / ElevenLabs / Google",
        "sourceUrl": "https://openai.com/research/whisper",
        "publishedDate": "2022-2024",
        "reason": (
            "Transcrierea automată și sinteza vocală au atins calitate umană. "
            "Ocupațiile bazate pe transcriere și comunicare vocală standard sunt puternic afectate."
        ),
    },
    {
        "title": "AI pentru proiectare constructii și arhitectură (BIM + generative design)",
        "category": "Architecture / Construction AI",
        "affectedSkills": [
            "proiectare tehnică", "desen tehnic", "design structural",
            "planificare construcții", "deviz lucrări", "inspecție construcții",
        ],
        "maturity": "growing",
        "impact": "medium",
        "sourceType": "internal_categorized",
        "sourceName": "Autodesk / Trimble / arXiv Architecture",
        "sourceUrl": "https://www.autodesk.com/solutions/generative-design",
        "publishedDate": "2020-2024",
        "reason": (
            "AI-ul poate genera și optimiza planuri de construcție și modele structurale. "
            "Judecata contextuală, coordonarea în teren și aprobările legale rămân umane."
        ),
    },
]


def get_relevant_advancements(skills: list[str], max_results: int = 5) -> list[dict]:
    """
    Returnează avanstamentele tehnologice relevante pentru un set de skill-uri.

    Folosește matching pe cuvinte cheie față de baza internă de categorii.
    Toate rezultatele sunt marcate cu sourceType="internal_categorized".

    NOTĂ: Această funcție nu apelează API-uri externe în versiunea curentă.
    TODO: Înlocuiește cu apeluri la search_arxiv() / search_openalex() / search_huggingface_models()

    Args:
        skills:      Lista de skill-uri ale ocupației (text liber)
        max_results: Numărul maxim de rezultate returnate

    Returns:
        Lista de avanstamente relevante, sortate după relevanță.
        Fiecare element include câmpul sourceType="internal_categorized".
    """
    if not skills:
        return []

    skills_lower = [s.lower() for s in skills]
    scored: list[tuple[int, dict]] = []

    for adv in _ADVANCEMENTS:
        affected_lower = [s.lower() for s in adv["affectedSkills"]]
        match_score = 0
        for skill in skills_lower:
            for affected in affected_lower:
                if affected in skill or any(w in skill for w in affected.split()):
                    match_score += 1
                    break
        if match_score > 0:
            scored.append((match_score, adv))

    scored.sort(key=lambda x: -x[0])
    return [adv for _, adv in scored[:max_results]]


# ── Stubs pentru API-uri reale ────────────────────────────────────────────────
# De implementat în versiunile ulterioare.
# Fiecare funcție trebuie să returneze o listă de dict-uri
# cu aceeași structură ca _ADVANCEMENTS (inclusiv sourceType corect).

def search_arxiv(query: str, max_results: int = 3) -> list[dict]:
    """
    TODO: Caută lucrări recente pe arXiv.

    Endpoint: https://export.arxiv.org/api/query?search_query={query}&max_results={n}
    Librărie: pip install arxiv
    sourceType în rezultate: "arxiv"
    """
    return []


def search_openalex(query: str, from_year: int = 2022) -> list[dict]:
    """
    TODO: Caută lucrări academice open-access pe OpenAlex (fără API key).

    Endpoint: https://api.openalex.org/works?search={query}&filter=from_publication_date:{year}-01-01
    sourceType în rezultate: "openalex"
    """
    return []


def search_huggingface_models(task: str) -> list[dict]:
    """
    TODO: Caută modele AI pe Hugging Face Hub.

    Endpoint: https://huggingface.co/api/models?filter={task}&sort=downloads
    sourceType în rezultate: "huggingface"
    """
    return []


def search_papers_with_code(query: str) -> list[dict]:
    """
    TODO: Caută benchmark-uri și implementări pe Papers with Code.

    Endpoint: https://paperswithcode.com/api/v1/papers/?q={query}
    sourceType în rezultate: "papers_with_code"
    """
    return []
