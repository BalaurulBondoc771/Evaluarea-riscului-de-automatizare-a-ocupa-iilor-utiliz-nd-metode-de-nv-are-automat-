import re

import pandas as pd
import plotly.express as px
import streamlit as st
from pathlib import Path
from streamlit.runtime.scriptrunner import get_script_run_ctx


def fail_and_stop(message: str) -> None:
    if get_script_run_ctx() is None:
        raise SystemExit(message)
    st.error(message)
    st.stop()


if __name__ == "__main__" and get_script_run_ctx() is None:
    raise SystemExit("Aceasta este o aplicatie Streamlit. Ruleaza: streamlit run site.py")


st.set_page_config(
    page_title="Risc de automatizare a ocupațiilor",
    page_icon="🤖",
    layout="wide",
)

# ── CSS global ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
:root {
    --low:         #2e7d32;
    --low-bg:      #0a1f0b;
    --low-border:  #1b5e20;
    --med:         #e65100;
    --med-bg:      #1a0e00;
    --med-border:  #8d3000;
    --high:        #c62828;
    --high-bg:     #1a0505;
    --high-border: #7f0000;
    --accent:      #c62828;
    --surface:     #1a1a1a;
    --surface2:    #232323;
    --border:      #2e2e2e;
    --text:        #eeeeee;
    --text-muted:  #999999;
    --r:           10px;
    --shadow:      0 2px 10px rgba(0,0,0,0.5);
}

/* ─ Hero ─────────────────────────────────────────────────────────────── */
.hero {
    background: linear-gradient(135deg, #1a0000 0%, #2d0505 60%, #1a0a0a 100%);
    border-bottom: 3px solid #c62828;
    color: white;
    padding: 2.2rem 2.5rem;
    border-radius: 14px;
    margin-bottom: 1.4rem;
}
.hero h1 {
    margin: 0 0 0.4rem 0;
    font-size: 1.85rem;
    font-weight: 700;
    line-height: 1.2;
}
.hero p {
    margin: 0 0 1rem 0;
    opacity: 0.88;
    font-size: 0.97rem;
    line-height: 1.5;
}
.hero-tags  { display: flex; gap: 0.5rem; flex-wrap: wrap; }
.hero-tag {
    background: rgba(198,40,40,0.25);
    border: 1px solid rgba(198,40,40,0.5);
    border-radius: 20px;
    padding: 3px 12px;
    font-size: 0.78rem;
    font-weight: 500;
}

/* ─ KPI row ──────────────────────────────────────────────────────────── */
.kpi-row { display: flex; gap: 1rem; margin-bottom: 0.4rem; }
.kpi-card {
    flex: 1;
    background: var(--surface);
    border: 1px solid var(--border);
    border-top: 3px solid var(--accent);
    border-radius: var(--r);
    padding: 1rem;
    text-align: center;
    box-shadow: var(--shadow);
}
.kpi-val {
    font-size: 1.75rem;
    font-weight: 700;
    color: #ef5350;
    line-height: 1;
    margin-bottom: 5px;
}
.kpi-lbl {
    font-size: 0.75rem;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

/* ─ Disclaimer ───────────────────────────────────────────────────────── */
.disclaimer {
    background: #1a1500;
    border: 1px solid #5d4900;
    border-left: 5px solid #f9a825;
    border-radius: 8px;
    padding: 0.85rem 1.2rem;
    margin: 0.4rem 0 1.1rem 0;
    font-size: 0.88rem;
    color: #ffecb3;
    line-height: 1.6;
}

/* ─ Job header card ──────────────────────────────────────────────────── */
.job-card-header {
    display: flex;
    align-items: flex-start;
    gap: 1.2rem;
    padding: 1.4rem 1.6rem;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--r);
    margin: 0.6rem 0 0.8rem 0;
    box-shadow: var(--shadow);
}
.score-circle {
    min-width: 88px;
    height: 88px;
    border-radius: 50%;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    flex-shrink: 0;
    box-shadow: 0 0 18px rgba(0,0,0,0.4);
}
.score-num { font-size: 2rem; line-height: 1; }
.score-sub { font-size: 0.68rem; opacity: 0.85; margin-top: 2px; }
.job-info  { flex: 1; min-width: 0; }
.job-title {
    font-size: 1.2rem;
    font-weight: 700;
    color: var(--text);
    margin: 0 0 7px 0;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.risk-pill {
    display: inline-block;
    padding: 3px 13px;
    border-radius: 20px;
    color: white;
    font-weight: 600;
    font-size: 0.8rem;
    margin-bottom: 9px;
}
.job-meta { font-size: 0.8rem; color: var(--text-muted); }
.job-meta span { margin-right: 14px; }
.score-gauge {
    height: 6px;
    background: #333;
    border-radius: 3px;
    margin-top: 10px;
    overflow: hidden;
}
.score-gauge-fill {
    height: 6px;
    border-radius: 3px;
}

/* ─ Generic section box ──────────────────────────────────────────────── */
.sec-box {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--r);
    padding: 1rem 1.2rem;
    margin: 0.6rem 0;
}
.sec-title {
    font-size: 0.76rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    color: var(--text-muted);
    margin-bottom: 0.55rem;
}
.sec-body {
    font-size: 0.91rem;
    color: var(--text);
    line-height: 1.65;
}

/* ─ Task rows ────────────────────────────────────────────────────────── */
.task-row {
    display: flex;
    align-items: flex-start;
    gap: 9px;
    padding: 4px 0;
    font-size: 0.9rem;
    color: var(--text);
    line-height: 1.4;
}
.task-dot {
    min-width: 8px;
    height: 8px;
    border-radius: 50%;
    margin-top: 5px;
    flex-shrink: 0;
}

/* ─ Career advice box ────────────────────────────────────────────────── */
.career-box {
    border-radius: 8px;
    padding: 1rem 1.2rem;
    margin: 0.6rem 0;
    font-size: 0.9rem;
    line-height: 1.65;
}
.career-low  { background: var(--low-bg);  border: 1px solid var(--low-border);  border-left: 5px solid var(--low); }
.career-med  { background: var(--med-bg);  border: 1px solid var(--med-border);  border-left: 5px solid var(--med); }
.career-high { background: var(--high-bg); border: 1px solid var(--high-border); border-left: 5px solid var(--high); }
.career-low  .career-body { color: #a5d6a7; }
.career-med  .career-body { color: #ffcc80; }
.career-high .career-body { color: #ef9a9a; }

/* ─ Misc ─────────────────────────────────────────────────────────────── */
.hr-thin { border: none; border-top: 1px solid var(--border); margin: 0.6rem 0 1rem 0; }
.block-container { padding-top: 1.5rem !important; }
</style>
""", unsafe_allow_html=True)


BASE_DIR = Path(__file__).resolve().parent

COR_CANDIDATES = [
    BASE_DIR.parent / "cor_risk_scored.csv",
    BASE_DIR / "cor_risk_scored.csv",
]
ESCO_CANDIDATES = [
    BASE_DIR.parent.parent / "dataset_final.csv",
    BASE_DIR / "dataset_final.csv",
]
SHAP_SUMMARY = BASE_DIR.parent.parent / "shap_summary_plot.png"
SHAP_BAR     = BASE_DIR.parent.parent / "shap_feature_importance.png"
FIGURI_DIR   = BASE_DIR.parent.parent / "figuri"


def load_first_existing(paths):
    for p in paths:
        if p.exists():
            return p
    return None


@st.cache_data
def load_cor_results(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    if "predicted_score" in df.columns:
        df["predicted_score"] = pd.to_numeric(df["predicted_score"], errors="coerce")
    if "match_score" in df.columns:
        df["match_score"] = pd.to_numeric(df["match_score"], errors="coerce")
    return df


@st.cache_data
def load_esco_dataset(path: str) -> pd.DataFrame:
    return pd.read_csv(path)


def risk_color(risk: str) -> str:
    return {"low": "#2e7d32", "medium": "#e65100", "high": "#c62828"}.get(str(risk).lower(), "#555")


def risk_label_ro(risk: str) -> str:
    return {"low": "Scăzut", "medium": "Mediu", "high": "Ridicat"}.get(str(risk).lower(), str(risk))


def score_to_color(score: float) -> str:
    s = max(0.0, min(100.0, float(score)))
    stops = [
        (  0,  76, 187, 110),
        ( 25, 156, 204,  57),
        ( 45, 255, 193,   7),
        ( 62, 255, 111,   0),
        ( 78, 211,  47,  47),
        ( 90, 139,   0,   0),
        (100,  26,   0,   0),
    ]
    for i in range(len(stops) - 1):
        s0, r0, g0, b0 = stops[i]
        s1, r1, g1, b1 = stops[i + 1]
        if s <= s1 or i == len(stops) - 2:
            t = (s - s0) / (s1 - s0) if s1 > s0 else 1.0
            t = max(0.0, min(1.0, t))
            r = int(r0 + t * (r1 - r0))
            g = int(g0 + t * (g1 - g0))
            b = int(b0 + t * (b1 - b0))
            return f"#{r:02x}{g:02x}{b:02x}"
    return "#1a0000"


def score_text_color(score: float) -> str:
    hex_c = score_to_color(score)
    r = int(hex_c[1:3], 16)
    g = int(hex_c[3:5], 16)
    b = int(hex_c[5:7], 16)
    return "#0a0a0a" if (0.299 * r + 0.587 * g + 0.114 * b) / 255 > 0.45 else "#ffffff"


def md_bold(text: str) -> str:
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)


# ── Date pentru explicații per nivel de risc ─────────────────────────────────

_AUTOMATABLE_TASKS = {
    "high": [
        "introducerea și procesarea datelor în sisteme informatice",
        "generarea automată a rapoartelor standard și a situațiilor financiare",
        "verificarea conformității documentelor pe baza unor reguli fixe",
        "calcule repetitive, reconcilieri numerice și balanțe de verificare",
        "sortarea, clasificarea și etichetarea materialelor după criterii predefinite",
        "monitorizarea parametrilor în procese industriale standardizate",
        "trimiterea automată a notificărilor și corespondenței de rutină",
    ],
    "medium": [
        "programarea și gestionarea agendei de activități",
        "procesarea cererilor și documentelor standard",
        "generarea de rapoarte periodice pe baza unor șabloane",
        "înregistrarea și arhivarea documentelor",
        "redactarea corespondenței administrative de rutină",
        "urmărirea indicatorilor de performanță pe baza datelor existente",
    ],
    "low": [
        "programarea activităților de rutină și gestionarea calendarului",
        "completarea formularelor administrative standard",
        "gestiunea corespondenței simple și a notificărilor repetitive",
    ],
}

_HUMAN_TASKS = {
    "high": [
        "gestionarea situațiilor excepționale și a cazurilor atipice",
        "luarea deciziilor cu responsabilitate legală, morală sau financiară",
        "interacțiunea cu persoane aflate în situații de criză sau vulnerabilitate",
        "reprezentarea organizației în relații externe sau cu autorități",
    ],
    "medium": [
        "coordonarea și motivarea echipei în contexte variabile",
        "consultanță personalizată pentru cazuri complexe sau sensibile",
        "negocierea, medierea conflictelor și construirea consensului",
        "evaluarea situațiilor ambigue și luarea deciziilor discreționare",
        "creativitate, adaptare la cerințe nestandard și inovare incrementală",
    ],
    "low": [
        "empatie, suport emoțional și consiliere individualizată",
        "gândire critică, creativitate și inovare strategică",
        "coordonarea echipelor și proiectelor complexe cu incertitudini ridicate",
        "judecată etică și responsabilitate în contexte cu implicații sociale mari",
        "adaptare rapidă la medii imprevizibile și situații fără precedent",
        "construirea relațiilor de lungă durată bazate pe încredere și empatie",
    ],
}

_CAREER_ADVICE = {
    "high": (
        "Ocupația include un procent semnificativ de sarcini rutiniere care pot fi preluate "
        "progresiv de sisteme automate sau AI. **Aceasta nu înseamnă că jobul va dispărea imediat**, "
        "ci că rolul se va transforma: sarcinile de execuție vor scădea, iar cele de supervizare, "
        "gestionare a excepțiilor și relații interumane vor câștiga importanță.\n\n"
        "**Recomandări:** Dezvoltă competențe digitale avansate (utilizarea instrumentelor AI, "
        "analiza datelor), orientează-te spre consultanță și coordonare, și investește în "
        "competențe relaționale și de comunicare — greu de înlocuit de mașini."
    ),
    "medium": (
        "Ocupația combină activități rutiniere cu activități complexe. O parte a sarcinilor poate "
        "fi optimizată sau automatizată în orizontul următorilor ani, dar componenta umană rămâne "
        "esențială pentru calitate și relevanță.\n\n"
        "**Recomandări:** Diversifică-ți competențele spre activități cu valoare adăugată mai mare — "
        "management, specializare tehnică avansată, comunicare sau creativitate. Adaptabilitatea "
        "și formarea continuă sunt cheia pentru a rămâne relevant pe piața muncii."
    ),
    "low": (
        "Ocupația implică preponderent activități complexe, creative sau relaționale, care sunt "
        "dificil de automatizat în orizontul previzibil. Componentele de empatie, judecată "
        "contextuală și interacțiune umană autentică reprezintă un avantaj competitiv durabil.\n\n"
        "**Recomandări:** Valorifică aceste competențe distinctive și familiarizează-te cu "
        "instrumentele AI ca auxiliare productive — nu ca înlocuitori. Integrarea AI în fluxul "
        "de lucru îți poate amplifica semnificativ productivitatea, menținând avantajul "
        "competitiv al competențelor umane unice."
    ),
}


def get_score_explanation(row: pd.Series) -> str:
    score = float(row["predicted_score"])

    if score >= 65:
        intro = (
            f"Scorul estimat de **{score:.0f}/100** reflectă un **grad ridicat de expunere la "
            "automatizare**. Ocupația include preponderent activități repetitive, standardizate "
            "sau de procesare a datelor — tipuri de sarcini pe care sistemele AI și roboții le "
            "pot prelua eficient în orizontul apropiat."
        )
    elif score >= 45:
        intro = (
            f"Scorul estimat de **{score:.0f}/100** reflectă un **grad mediu de expunere la "
            "automatizare**. Ocupația combină activități rutiniere (parțial automatizabile) cu "
            "activități nerutiniere care presupun judecată, adaptare sau interacțiune umană directă."
        )
    else:
        intro = (
            f"Scorul estimat de **{score:.0f}/100** reflectă un **grad scăzut de expunere la "
            "automatizare**. Ocupația implică preponderent activități complexe, creative sau "
            "relaționale, dificil de automatizat în orizontul previzibil."
        )

    feature_notes = []
    total = float(row["total_skill"]) if "total_skill" in row.index else 0.0
    if total > 0:
        if "essential" in row.index:
            ess_pct = float(row["essential"]) / total * 100
            if ess_pct > 60:
                feature_notes.append(
                    f"Profilul ocupației este dominat de competențe **esențiale** "
                    f"({ess_pct:.0f}% din total), indicând un set de sarcini bine definit "
                    "și standardizabil."
                )
            elif ess_pct < 35:
                feature_notes.append(
                    f"Ponderea redusă a competențelor esențiale ({ess_pct:.0f}%) sugerează "
                    "un profil de competențe flexibil și mai rezistent la rutinizare."
                )
        if "automation_score_proxy" in row.index:
            proxy = float(row["automation_score_proxy"])
            if proxy > 60:
                feature_notes.append(
                    "Indicatorul structural al ocupației confirmă o proporție ridicată de "
                    "competențe rutinizabile (cunoștințe formale + competențe opționale extinse)."
                )
            elif proxy < 30:
                feature_notes.append(
                    "Indicatorul structural al ocupației sugerează un profil cu competențe "
                    "predominant nerutinizabile."
                )

    if feature_notes:
        return intro + "\n\n" + "\n\n".join(feature_notes)
    return intro


# ── Helpers HTML ─────────────────────────────────────────────────────────────

def _tasks_html(tasks: list, dot_color: str) -> str:
    return "".join(
        f'<div class="task-row">'
        f'<div class="task-dot" style="background:{dot_color};"></div>'
        f'<span>{t}</span></div>'
        for t in tasks
    )


def render_job_header(row: pd.Series, name_col: str) -> str:
    score    = float(row["predicted_score"])
    risk     = str(row.get("risk_level", "")).lower()
    circ_col = score_to_color(score)
    txt_col  = score_text_color(score)
    risk_col = risk_color(risk)
    risk_ro  = risk_label_ro(risk)
    job_name = str(row.get(name_col, "—"))

    meta_parts = []
    if "cod_cor" in row.index and str(row["cod_cor"]) not in ("nan", ""):
        meta_parts.append(f'<span>COR: {row["cod_cor"]}</span>')
    if "matched_job" in row.index:
        esco = str(row["matched_job"])[:48]
        meta_parts.append(f'<span>ESCO: {esco}</span>')
    if "match_score" in row.index:
        meta_parts.append(f'<span>Potrivire: {float(row["match_score"]):.0f}%</span>')

    return f"""
<div class="job-card-header">
  <div class="score-circle" style="background:{circ_col};color:{txt_col};">
    <div class="score-num">{score:.0f}</div>
    <div class="score-sub">/ 100</div>
  </div>
  <div class="job-info">
    <div class="job-title">{job_name}</div>
    <div><span class="risk-pill" style="background:{risk_col};">Risc {risk_ro}</span></div>
    <div class="job-meta">{"".join(meta_parts)}</div>
    <div class="score-gauge">
      <div class="score-gauge-fill" style="width:{score:.0f}%;background:{circ_col};"></div>
    </div>
  </div>
</div>"""


def render_explanation_box(row: pd.Series) -> str:
    text = md_bold(get_score_explanation(row).replace("\n\n", "<br><br>"))
    return f"""
<div class="sec-box">
  <div class="sec-title">💡 De ce are acest scor?</div>
  <div class="sec-body">{text}</div>
</div>"""


def render_tasks_box(tasks: list, title: str, dot_color: str, border_color: str) -> str:
    rows = _tasks_html(tasks, dot_color)
    return f"""
<div class="sec-box" style="border-left:4px solid {border_color};">
  <div class="sec-title">{title}</div>
  {rows}
</div>"""


def render_career_box(risk: str) -> str:
    text = _CAREER_ADVICE.get(risk, _CAREER_ADVICE["medium"])
    body = md_bold(text.replace("\n\n", "<br><br>"))
    css_cls = {"low": "career-low", "medium": "career-med", "high": "career-high"}.get(risk, "career-low")
    return f"""
<div class="career-box {css_cls}">
  <div class="sec-title" style="opacity:0.7;">🎯 Ce înseamnă pentru carieră?</div>
  <div class="career-body">{body}</div>
</div>"""


# ── Încărcare date ────────────────────────────────────────────────────────────
cor_path  = load_first_existing(COR_CANDIDATES)
esco_path = load_first_existing(ESCO_CANDIDATES)

if cor_path is None:
    fail_and_stop("Nu am găsit fișierul cor_risk_scored.csv. Rulează mai întâi cor_pipeline.py.")

cor_df  = load_cor_results(str(cor_path))
esco_df = load_esco_dataset(str(esco_path)) if esco_path else None

name_col = next(
    (c for c in ["denumire_ocupatie", "job", "occupation", "matched_job"] if c in cor_df.columns),
    None,
)
if name_col is None:
    fail_and_stop("Nu am găsit o coloană cu denumirea ocupației în fișierul COR.")

missing = [c for c in ["predicted_score", "risk_level"] if c not in cor_df.columns]
if missing:
    fail_and_stop(f"Lipsesc coloanele necesare: {missing}")

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Filtre")
    selected_risk = st.multiselect(
        "Nivel de risc",
        options=["low", "medium", "high"],
        default=["low", "medium", "high"],
        format_func=risk_label_ro,
    )
    min_match = 0
    if "match_score" in cor_df.columns:
        min_match = st.slider(
            "Scor minim de potrivire COR–ESCO",
            min_value=0, max_value=100, value=80,
            help="Valori sub 80 pot conține potriviri eronate. Recomandat: ≥ 80.",
        )
    unmatched_path = BASE_DIR.parent / "cor_unmatched.csv"
    if unmatched_path.exists():
        n_unmatched = len(pd.read_csv(unmatched_path))
        n_total = len(cor_df) + n_unmatched
        st.markdown("---")
        st.markdown("**Acoperire COR–ESCO**")
        st.progress(len(cor_df) / n_total if n_total else 0)
        st.caption(
            f"{len(cor_df):,} mapate / {n_total:,} total "
            f"({len(cor_df)/n_total*100:.0f}%) — prag ≥ {min_match}%".replace(",", ".")
        )
    st.markdown("---")
    st.caption(
        "Rezultatele sunt estimative și au rol exploratoriu. "
        "Nu trebuie interpretate ca verdict definitiv pentru o ocupație."
    )

filtered = cor_df[cor_df["risk_level"].isin(selected_risk)].copy()
if "match_score" in filtered.columns:
    filtered = filtered[filtered["match_score"] >= min_match]

# ── Hero header ───────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <h1>🤖 Risc de automatizare a ocupațiilor</h1>
  <p>Instrument de analiză bazat pe date ESCO și algoritmi LightGBM — aplicat pe clasificarea
  ocupațiilor românești (COR). Scorurile reprezintă <strong>estimări orientative</strong>,
  nu predicții certe despre viitorul pieței muncii.</p>
  <div class="hero-tags">
    <span class="hero-tag">România — COR 2024</span>
    <span class="hero-tag">ESCO v1.2</span>
    <span class="hero-tag">LightGBM + SHAP</span>
    <span class="hero-tag">Analiză exploratorie</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ── KPI row ───────────────────────────────────────────────────────────────────
n_fmt  = f"{len(filtered):,}".replace(",", ".")
avg_sc = f"{filtered['predicted_score'].mean():.1f}" if not filtered.empty else "—"
dom    = risk_label_ro(filtered["risk_level"].mode().iloc[0]) if not filtered.empty else "—"
max_sc = f"{filtered['predicted_score'].max():.1f}" if not filtered.empty else "—"

st.markdown(f"""
<div class="kpi-row">
  <div class="kpi-card">
    <div class="kpi-val">{n_fmt}</div>
    <div class="kpi-lbl">Ocupații afișate</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-val">{avg_sc}</div>
    <div class="kpi-lbl">Scor mediu</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-val">{dom}</div>
    <div class="kpi-lbl">Nivel dominant</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-val">{max_sc}</div>
    <div class="kpi-lbl">Scor maxim</div>
  </div>
</div>
<hr class="hr-thin">
""", unsafe_allow_html=True)

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_search, tab_charts, tab_top, tab_shap, tab_method = st.tabs([
    "🔍 Caută ocupație",
    "📊 Distribuții",
    "🏆 Top ocupații",
    "🧠 Explicabilitate SHAP",
    "📖 Metodologie",
])

# ── Tab 1: Căutare ────────────────────────────────────────────────────────────
with tab_search:
    st.markdown("""
    <div class="disclaimer">
      <strong>⚠️ Notă metodologică:</strong> Procentele afișate sunt
      <strong>estimări orientative</strong>, nu predicții certe. Ele indică gradul în care
      sarcinile asociate unei ocupații pot fi automatizate sau asistate de AI. Scorul este
      calculat în funcție de repetitivitatea sarcinilor, nivelul de creativitate, interacțiunea
      umană, responsabilitatea decizională și dependența de activități digitale.
    </div>
    """, unsafe_allow_html=True)

    query = st.text_input(
        "Scrie denumirea ocupației",
        placeholder="Ex.: contabil, programator, operator CNC",
    )
    search_df = filtered.copy()
    if query:
        search_df = search_df[
            search_df[name_col].astype(str).str.contains(query, case=False, na=False)
        ]

    if query and not search_df.empty:
        selected_job = st.selectbox(
            "Selectează ocupația",
            search_df[name_col].astype(str).tolist(),
        )
        row = search_df[search_df[name_col].astype(str) == selected_job].iloc[0]
        risk = str(row["risk_level"]).lower()

        # ── Job header card ──────────────────────────────────────────────────
        st.markdown(render_job_header(row, name_col), unsafe_allow_html=True)

        # ── De ce are acest scor? ────────────────────────────────────────────
        st.markdown(render_explanation_box(row), unsafe_allow_html=True)

        # ── Sarcini (2 coloane) ──────────────────────────────────────────────
        col_auto, col_human = st.columns(2)
        with col_auto:
            st.markdown(
                render_tasks_box(
                    _AUTOMATABLE_TASKS.get(risk, _AUTOMATABLE_TASKS["medium"]),
                    "⚙️ Sarcini care pot fi automatizate",
                    "#ef5350", "#c62828",
                ),
                unsafe_allow_html=True,
            )
        with col_human:
            st.markdown(
                render_tasks_box(
                    _HUMAN_TASKS.get(risk, _HUMAN_TASKS["medium"]),
                    "🧠 Sarcini greu de automatizat",
                    "#66bb6a", "#2e7d32",
                ),
                unsafe_allow_html=True,
            )

        # ── Sfaturi carieră ──────────────────────────────────────────────────
        st.markdown(render_career_box(risk), unsafe_allow_html=True)

        # ── Detalii tehnice (colapsate) ──────────────────────────────────────
        with st.expander("🔧 Detalii tehnice"):
            extra = {
                c: row[c]
                for c in ["cod_cor", "matched_job", "match_score"]
                if c in row.index
            }
            if extra:
                st.json({k: (float(v) if hasattr(v, "item") else v) for k, v in extra.items()})
            feat_cols = [
                c for c in
                ["total_skill", "essential", "optional", "knowledge", "skill_com", "automation_score_proxy"]
                if c in row.index
            ]
            if feat_cols:
                st.markdown("**Caracteristici folosite de model**")
                feat_df = pd.DataFrame({
                    "Caracteristică": feat_cols,
                    "Valoare": [round(float(row[c]), 2) for c in feat_cols],
                })
                st.dataframe(feat_df, use_container_width=True, hide_index=True)

    elif query:
        st.warning("Nu am găsit nicio ocupație care să corespundă filtrului introdus.")

# ── Tab 2: Distribuții ────────────────────────────────────────────────────────
with tab_charts:
    col_l, col_r = st.columns(2)

    with col_l:
        st.subheader("Distribuția nivelurilor de risc")
        risk_counts = (
            filtered["risk_level"]
            .value_counts()
            .reindex(["low", "medium", "high"], fill_value=0)
            .reset_index()
        )
        risk_counts.columns = ["risk_level", "count"]
        risk_counts["label"] = risk_counts["risk_level"].map(risk_label_ro)
        fig_bar = px.bar(
            risk_counts,
            x="label", y="count",
            color="risk_level",
            color_discrete_map={"low": "#2e7d32", "medium": "#e65100", "high": "#c62828"},
            labels={"label": "Nivel risc", "count": "Număr ocupații"},
            text="count",
        )
        fig_bar.update_layout(
            showlegend=False, margin=dict(t=20),
            plot_bgcolor="#1a1a1a", paper_bgcolor="#0f0f0f",
            font=dict(color="#eeeeee"),
        )
        fig_bar.update_traces(textposition="outside")
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_r:
        st.subheader("Distribuția scorului de automatizare")
        fig_hist = px.histogram(
            filtered.dropna(subset=["predicted_score"]),
            x="predicted_score",
            nbins=25,
            labels={"predicted_score": "Scor automatizare", "count": "Ocupații"},
            color_discrete_sequence=["#ef5350"],
        )
        fig_hist.add_vline(x=45, line_dash="dash", line_color="#66bb6a",
                           annotation_text="Prag low/medium (45)",
                           annotation_font_color="#66bb6a")
        fig_hist.add_vline(x=65, line_dash="dash", line_color="#ef5350",
                           annotation_text="Prag medium/high (65)",
                           annotation_font_color="#ef5350")
        fig_hist.update_layout(
            margin=dict(t=20),
            plot_bgcolor="#1a1a1a", paper_bgcolor="#0f0f0f",
            font=dict(color="#eeeeee"),
        )
        st.plotly_chart(fig_hist, use_container_width=True)

    if "total_skill" in filtered.columns:
        st.subheader("Scor de automatizare vs. număr total de competențe")
        fig_scatter = px.scatter(
            filtered.dropna(subset=["predicted_score", "total_skill"]),
            x="total_skill",
            y="predicted_score",
            color="risk_level",
            color_discrete_map={"low": "#2e7d32", "medium": "#e65100", "high": "#c62828"},
            hover_name=name_col,
            labels={
                "total_skill": "Număr total competențe",
                "predicted_score": "Scor automatizare",
            },
            opacity=0.6,
        )
        fig_scatter.update_layout(
            margin=dict(t=20),
            plot_bgcolor="#1a1a1a", paper_bgcolor="#0f0f0f",
            font=dict(color="#eeeeee"),
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

# ── Tab 3: Top ocupații ───────────────────────────────────────────────────────
with tab_top:
    col_h, col_l = st.columns(2)
    _disp_cols = (
        [name_col, "predicted_score", "match_score"]
        if "match_score" in filtered.columns
        else [name_col, "predicted_score"]
    )
    with col_h:
        st.subheader("🔴 Top 15 risc ridicat")
        top_high = (
            filtered[filtered["risk_level"] == "high"]
            .sort_values("predicted_score", ascending=False)[_disp_cols]
            .head(15)
            .rename(columns={
                name_col: "Ocupație",
                "predicted_score": "Scor",
                "match_score": "Potrivire %",
            })
        )
        st.dataframe(top_high, use_container_width=True, hide_index=True)

    with col_l:
        st.subheader("🟢 Top 15 risc scăzut")
        top_low = (
            filtered[filtered["risk_level"] == "low"]
            .sort_values("predicted_score", ascending=True)[_disp_cols]
            .head(15)
            .rename(columns={
                name_col: "Ocupație",
                "predicted_score": "Scor",
                "match_score": "Potrivire %",
            })
        )
        st.dataframe(top_low, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("Descarcă rezultatele filtrate")
    export_cols = [name_col, "predicted_score", "risk_level"] + (
        ["match_score", "matched_job"] if "match_score" in filtered.columns else []
    )
    export_df = filtered[export_cols].rename(columns={
        name_col: "Ocupatie",
        "predicted_score": "Scor_automatizare",
        "risk_level": "Nivel_risc",
        "match_score": "Potrivire_pct",
        "matched_job": "Ocupatie_ESCO_mapata",
    })
    st.download_button(
        label=f"⬇ Descarcă {len(export_df):,} ocupații (CSV)".replace(",", "."),
        data=export_df.to_csv(index=False, encoding="utf-8-sig"),
        file_name="risc_automatizare_cor.csv",
        mime="text/csv",
    )

# ── Tab 4: SHAP ───────────────────────────────────────────────────────────────
with tab_shap:
    st.subheader("Importanța variabilelor — analiză SHAP")
    st.write(
        "SHAP (SHapley Additive exPlanations) măsoară contribuția medie a fiecărui predictor "
        "la ieșirea modelului, bazată pe teoria jocurilor cooperative (Lundberg & Lee, 2017). "
        "Valorile SHAP permit interpretarea locală și globală a deciziilor modelului."
    )

    if SHAP_BAR.exists():
        st.markdown("**Importanța globală a variabilelor (SHAP bar plot)**")
        st.image(str(SHAP_BAR), use_container_width=True)
    elif (FIGURI_DIR / "shap_feature_importance.png").exists():
        st.image(str(FIGURI_DIR / "shap_feature_importance.png"), use_container_width=True)
    else:
        st.info("Graficul SHAP bar nu a fost găsit. Rulează dataset.py pentru a-l genera.")

    if SHAP_SUMMARY.exists():
        st.markdown("**Distribuția valorilor SHAP per variabilă (beeswarm plot)**")
        st.image(str(SHAP_SUMMARY), use_container_width=True)
    elif (FIGURI_DIR / "shap_summary_plot.png").exists():
        st.image(str(FIGURI_DIR / "shap_summary_plot.png"), use_container_width=True)
    else:
        st.info("Graficul SHAP summary nu a fost găsit. Rulează dataset.py pentru a-l genera.")

    st.markdown("---")
    st.caption(
        "Referință: Lundberg, S. M., & Lee, S.-I. (2017). "
        "A unified approach to interpreting model predictions. *NeurIPS 2017*."
    )

# ── Tab 5: Metodologie ────────────────────────────────────────────────────────
with tab_method:
    st.subheader("Cum funcționează modelul?")

    with st.expander("1. Sursa datelor", expanded=True):
        st.write(
            "Datele provin din baza **ESCO** (European Skills, Competences, Qualifications and "
            "Occupations), versiunea în limba română. Au fost extrase relațiile dintre ocupații "
            "și competențele asociate (esențiale și opționale), rezultând un dataset cu ~3.000 "
            "de ocupații și 6 predictori structurali."
        )
        st.write(
            "Ocupațiile românești (**COR — Clasificarea Ocupațiilor din România**) au fost "
            "mapate pe ESCO prin fuzzy string matching (RapidFuzz), reținând doar potrivirile "
            "cu scor ≥ 80%."
        )

    with st.expander("2. Variabila țintă — scorul de automatizare"):
        st.write(
            "Scorul de automatizare este o euristică bazată pe **task-based approach** "
            "(Frey & Osborne, 2017; Autor, 2015): competențele asociate fiecărei ocupații sunt "
            "clasificate ca rutiniere (cresc riscul) sau nerutiniere/sociale/creative (scad riscul), "
            "pe baza unui lexicon de termeni în română."
        )
        st.markdown(
            "| Tip task | Exemple | Efect |\n"
            "|---|---|---|\n"
            "| Rutiniere manuale | operează, asamblează, sortează, sudează | ↑ risc |\n"
            "| Rutiniere cognitive | introduce date, arhivează, codifică | ↑ risc |\n"
            "| Nerutiniere sociale | negociază, consiliază, predă, coordonează | ↓ risc |\n"
            "| Nerutiniere analitice/creative | cercetează, proiectează, evaluează, inovează | ↓ risc |"
        )

    with st.expander("3. Predictori (features)"):
        st.write(
            "Modelul folosește 6 variabile structurale derivate din ESCO:\n"
            "- **total_skill** — numărul total de competențe asociate ocupației\n"
            "- **essential** — numărul de competențe esențiale\n"
            "- **optional** — numărul de competențe opționale\n"
            "- **knowledge** — numărul de competențe de tip cunoștințe\n"
            "- **skill_com** — numărul de competențe/abilități propriu-zise\n"
            "- **automation_score_proxy** — indicator structural: "
            "`(optional/total·0.5 + knowledge/total·0.5)·100`; "
            "capturează proporția de competențe cu potențial de rutinizare"
        )

    with st.expander("4. Modelul ML"):
        st.write(
            "Algoritmul utilizat este **LightGBM** (Light Gradient Boosting Machine), "
            "atât în variantă de regresie (predicție scor continuu), cât și de clasificare "
            "(LOW / MEDIUM / HIGH). Validarea a inclus split train/test stratificat și "
            "cross-validare 5-fold."
        )
        st.warning(
            "**Limitare importantă:** Deși R²_test = 0.196 (pozitiv) și acuratețea "
            "clasificatorului (55.3%) depășește marginal baseline-ul trivial (53.95%), "
            "cross-validarea relevă instabilitate semnificativă (R²_CV = −14.21 ± 6.16). "
            "Rezultatele trebuie interpretate ca estimări exploratorii, nu ca predicții robuste."
        )

    with st.expander("5. Limitări"):
        st.write("- Maparea COR–ESCO nu este perfectă; ocupațiile fără echivalent ESCO sunt excluse.")
        st.write("- Scorul de automatizare este o euristică, nu un indicator validat extern față de Frey & Osborne (2013).")
        st.write("- Modelul nu capturează contextul economic, organizațional sau geografic al ocupațiilor.")
        st.write("- Dezechilibrul claselor (53.9% LOW, 35.1% MEDIUM, 11.0% HIGH) limitează performanța pe clasa HIGH — cea mai relevantă din perspectivă economică.")

    with st.expander("Bibliografie"):
        st.markdown(
            "- Frey, C. B., & Osborne, M. A. (2017). The future of employment. "
            "*Technological Forecasting and Social Change*, 114, 254–280.\n"
            "- Autor, D. H. (2015). Why are there still so many jobs? "
            "*Journal of Economic Perspectives*, 29(3), 3–30.\n"
            "- Arntz, M., Gregory, T., & Zierahn, U. (2016). *The Risk of Automation for Jobs "
            "in OECD Countries*. OECD Social, Employment and Migration Working Papers No. 189.\n"
            "- Lundberg, S. M., & Lee, S.-I. (2017). A unified approach to interpreting model "
            "predictions. *NeurIPS 2017*.\n"
            "- ESCO v1.2 — European Commission, https://esco.ec.europa.eu"
        )

    if esco_df is not None:
        with st.expander("Date de intrare (ESCO dataset — primele 10 rânduri)"):
            st.dataframe(esco_df.head(10), use_container_width=True)
