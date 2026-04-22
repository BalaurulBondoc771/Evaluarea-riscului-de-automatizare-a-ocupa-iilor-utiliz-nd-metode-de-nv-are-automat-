import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from pathlib import Path
from streamlit.runtime.scriptrunner import get_script_run_ctx


def fail_and_stop(message: str) -> None:
    # In bare Python mode there is no Streamlit session context, so exit cleanly.
    if get_script_run_ctx() is None:
        raise SystemExit(message)
    st.error(message)
    st.stop()


if __name__ == "__main__" and get_script_run_ctx() is None:
    raise SystemExit("Aceasta este o aplicatie Streamlit. Ruleaza: streamlit run c:/Economie AI/Site/site.py")

st.set_page_config(
    page_title="Risc de automatizare a ocupațiilor",
    page_icon="🤖",
    layout="wide",
)

BASE_DIR = Path(__file__).resolve().parent
COR_CANDIDATES = [
    BASE_DIR / "COR" / "cor_risk_scored.csv",
    BASE_DIR / "cor_risk_scored.csv",
    BASE_DIR.parent / "cor_risk_scored.csv",
]
ESCO_CANDIDATES = [
    BASE_DIR / "dataset_final.csv",
]


def load_first_existing(paths):
    for path in paths:
        if path.exists():
            return path
    return None


@st.cache_data
def load_cor_results(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    # Normalize likely columns
    if "predicted_score" in df.columns:
        df["predicted_score"] = pd.to_numeric(df["predicted_score"], errors="coerce")
    if "match_score" in df.columns:
        df["match_score"] = pd.to_numeric(df["match_score"], errors="coerce")
    return df


@st.cache_data
def load_esco_dataset(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    return df


def classify_color(risk: str) -> str:
    if str(risk).lower() == "low":
        return "#2e7d32"
    if str(risk).lower() == "medium":
        return "#ef6c00"
    return "#c62828"


def risk_label_ro(risk: str) -> str:
    mapping = {
        "low": "Scăzut",
        "medium": "Mediu",
        "high": "Ridicat",
    }
    return mapping.get(str(risk).lower(), str(risk))


def score_explanation(score: float) -> str:
    if score < 45:
        return (
            "Ocupația este estimată cu risc scăzut de automatizare. "
            "Asta sugerează că include mai multe activități care cer judecată umană, "
            "adaptare sau interacțiune complexă."
        )
    if score < 65:
        return (
            "Ocupația este estimată cu risc mediu de automatizare. "
            "Asta înseamnă că unele activități pot fi automatizate, dar nu întreaga ocupație."
        )
    return (
        "Ocupația este estimată cu risc ridicat de automatizare. "
        "Asta sugerează o pondere mai mare de activități repetitive sau standardizabile."
    )


cor_path = load_first_existing(COR_CANDIDATES)
esco_path = load_first_existing(ESCO_CANDIDATES)

st.title("🤖 Risc de automatizare a ocupațiilor")
st.caption("Aplicație demonstrativă bazată pe modelul antrenat pe ESCO și aplicat pe COR")

if cor_path is None:
    fail_and_stop("Nu am găsit fișierul cor_risk_scored.csv. Pune-l în folderul aplicației sau în subfolderul COR.")

cor_df = load_cor_results(str(cor_path))
esco_df = load_esco_dataset(str(esco_path)) if esco_path else None

name_col_candidates = ["denumire_ocupatie", "job", "occupation", "matched_job"]
name_col = next((c for c in name_col_candidates if c in cor_df.columns), None)
if name_col is None:
    fail_and_stop("Nu am găsit o coloană cu denumirea ocupației în fișierul COR.")

required_cols = ["predicted_score", "risk_level"]
missing = [c for c in required_cols if c not in cor_df.columns]
if missing:
    fail_and_stop(f"Lipsesc coloanele necesare: {missing}")

# Sidebar
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
        min_match = st.slider("Scor minim de potrivire COR–ESCO", 0, 100, 70)

    st.markdown("---")
    st.subheader("Despre aplicație")
    st.write(
        "Rezultatele sunt estimative și au rol exploratoriu. "
        "Ele nu trebuie interpretate ca verdict final pentru o ocupație."
    )

filtered = cor_df.copy()
filtered = filtered[filtered["risk_level"].isin(selected_risk)]
if "match_score" in filtered.columns:
    filtered = filtered[filtered["match_score"] >= min_match]

# Metrics
col1, col2, col3, col4 = st.columns(4)
col1.metric("Ocupații afișate", f"{len(filtered):,}".replace(",", "."))
col2.metric("Scor mediu", f"{filtered['predicted_score'].mean():.1f}")
col3.metric("Risc mediu", f"{risk_label_ro(filtered['risk_level'].mode().iloc[0]) if not filtered.empty else '-'}")
col4.metric("Scor maxim", f"{filtered['predicted_score'].max():.1f}" if not filtered.empty else "-")

st.markdown("---")

# Search section
st.subheader("Caută o ocupație")
query = st.text_input("Scrie denumirea ocupației", placeholder="Ex.: contabil, programator, operator CNC")

search_df = filtered.copy()
if query:
    search_df = search_df[search_df[name_col].astype(str).str.contains(query, case=False, na=False)]

if query and not search_df.empty:
    options = search_df[name_col].astype(str).tolist()
    selected_job = st.selectbox("Selectează ocupația", options)
    row = search_df[search_df[name_col].astype(str) == selected_job].iloc[0]

    st.markdown("### Rezultat")
    c1, c2 = st.columns([1, 2])

    with c1:
        risk = str(row["risk_level"]).lower()
        color = classify_color(risk)
        st.markdown(
            f"""
            <div style='padding:16px;border-radius:14px;background:{color};color:white;text-align:center;'>
                <div style='font-size:16px;'>Nivel de risc</div>
                <div style='font-size:30px;font-weight:700;'>{risk_label_ro(risk)}</div>
                <div style='font-size:14px;'>Scor: {row['predicted_score']:.1f}/100</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c2:
        st.write(score_explanation(float(row["predicted_score"])))
        extra_cols = [c for c in ["cod_cor", "matched_job", "match_score"] if c in row.index]
        if extra_cols:
            details = {c: row[c] for c in extra_cols}
            st.json(details)

        feat_cols = [c for c in ["total_skill", "essential", "optional", "knowledge", "skill_com"] if c in row.index]
        if feat_cols:
            st.markdown("**Caracteristici folosite de model**")
            feat_df = pd.DataFrame({"Caracteristică": feat_cols, "Valoare": [row[c] for c in feat_cols]})
            st.dataframe(feat_df, use_container_width=True, hide_index=True)

elif query:
    st.warning("Nu am găsit nicio ocupație care să corespundă filtrului introdus.")

st.markdown("---")

# Charts
left, right = st.columns(2)

with left:
    st.subheader("Distribuția nivelurilor de risc")
    risk_counts = filtered["risk_level"].value_counts().reindex(["low", "medium", "high"], fill_value=0)
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar([risk_label_ro(x) for x in risk_counts.index], risk_counts.values)
    ax.set_ylabel("Număr ocupații")
    ax.set_xlabel("Nivel risc")
    st.pyplot(fig)

with right:
    st.subheader("Distribuția scorului de automatizare")
    fig2, ax2 = plt.subplots(figsize=(6, 4))
    ax2.hist(filtered["predicted_score"].dropna(), bins=20)
    ax2.set_xlabel("Scor automatizare")
    ax2.set_ylabel("Număr ocupații")
    st.pyplot(fig2)

st.markdown("---")

# Top occupations
c1, c2 = st.columns(2)
with c1:
    st.subheader("Top ocupații cu risc ridicat")
    top_high = filtered.sort_values("predicted_score", ascending=False)[[name_col, "predicted_score", "risk_level"]].head(10)
    top_high = top_high.rename(columns={name_col: "Ocupație", "predicted_score": "Scor", "risk_level": "Risc"})
    top_high["Risc"] = top_high["Risc"].map(risk_label_ro)
    st.dataframe(top_high, use_container_width=True, hide_index=True)

with c2:
    st.subheader("Top ocupații cu risc scăzut")
    top_low = filtered.sort_values("predicted_score", ascending=True)[[name_col, "predicted_score", "risk_level"]].head(10)
    top_low = top_low.rename(columns={name_col: "Ocupație", "predicted_score": "Scor", "risk_level": "Risc"})
    top_low["Risc"] = top_low["Risc"].map(risk_label_ro)
    st.dataframe(top_low, use_container_width=True, hide_index=True)

st.markdown("---")

# Methodology section
with st.expander("Cum funcționează modelul?"):
    st.write(
        "Modelul a fost antrenat pe date ESCO, folosind caracteristici care descriu competențele asociate ocupațiilor. "
        "Apoi a fost aplicat pe ocupațiile din România printr-un proces de mapare între COR și ESCO."
    )
    st.write(
        "Scorul returnat este o estimare a riscului de automatizare, nu o certitudine. "
        "El trebuie interpretat ca instrument exploratoriu."
    )

with st.expander("Limitări"):
    st.write("• maparea COR–ESCO nu este perfectă;")
    st.write("• modelul are limitări de generalizare;")
    st.write("• scorurile nu surprind complet contextul economic și organizațional al fiecărei ocupații.")

# Optional ESCO section
if esco_df is not None:
    with st.expander("Date de intrare disponibile"):
        st.write(f"Dataset ESCO încărcat: {len(esco_df):,} rânduri".replace(",", "."))
        st.dataframe(esco_df.head(10), use_container_width=True)
