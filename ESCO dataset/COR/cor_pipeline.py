from __future__ import annotations

import importlib
import pickle
import sys
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import joblib
import pandas as pd

REQUIRED_FEATURES = [
    "total_skill",
    "essential",
    "optional",
    "knowledge",
    "skill_com",
    "automation_score_proxy",
]


COR_NAME_CANDIDATES = [
    "denumire_ocupatie",
    "occupation",
    "job",
    "occupationLabel_ro",
]


ESCO_JOB_CANDIDATES = [
    "job",
    "occupation",
    "occupationLabel_ro",
]


def classify(score: float) -> str:
    if score < 45:
        return "low"
    if score < 65:
        return "medium"
    return "high"


def ensure_columns(df: pd.DataFrame, required: list[str], df_name: str) -> None:
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"{df_name} nu conține coloanele necesare: {missing}")


def pick_first_existing(columns: list[str], candidates: list[str], name: str) -> str:
    for candidate in candidates:
        if candidate in columns:
            return candidate
    raise ValueError(f"Nu am găsit nicio coloană validă pentru {name}. Căutate: {candidates}")


def load_model(model_path: Path):
    try:
        return joblib.load(model_path)
    except Exception:
        with model_path.open("rb") as handle:
            return pickle.load(handle)


def normalize_text(series: pd.Series) -> pd.Series:
    def strip_accents(text: str) -> str:
        normalized = unicodedata.normalize("NFKD", text)
        return "".join(ch for ch in normalized if not unicodedata.combining(ch))

    return (
        series.astype(str)
        .map(strip_accents)
        .str.lower()
        .str.strip()
        .str.replace(r"\s+", " ", regex=True)
    )


def match_jobs(cor: pd.DataFrame, esco: pd.DataFrame) -> pd.DataFrame:
    esco_jobs = sorted(set(esco["job_clean"].dropna().astype(str).tolist()))
    if not esco_jobs:
        raise ValueError("Nu există ocupații ESCO valide pentru matching.")

    rf_process = None
    try:
        rf_process = importlib.import_module("rapidfuzz.process")
    except ModuleNotFoundError:
        rf_process = None

    def fallback_extract_one(job: str) -> tuple[str, float]:
        best_job = ""
        best_score = 0.0
        for candidate in esco_jobs:
            score = SequenceMatcher(None, job, candidate).ratio() * 100
            if score > best_score:
                best_score = score
                best_job = candidate
        return best_job, float(best_score)

    def match_one(job: str) -> tuple[str, float]:
        if rf_process is not None:
            result = rf_process.extractOne(job, esco_jobs)
            if result is None:
                return "", 0.0
            match, score, _ = result
            return str(match), float(score)
        return fallback_extract_one(job)

    matched = cor["denumire_clean"].apply(lambda x: pd.Series(match_one(x), index=["matched_job", "match_score"]))
    return pd.concat([cor, matched], axis=1)


def main() -> None:
    # === PATH-URI FIXE (modifică dacă e nevoie) ===
    # Paths sunt relative la locul scriptului, indiferent de unde îl rulezi
    here = Path(__file__).parent
    cor_path = here / "cor_curat.csv"
    esco_path = here / "../dataset_final.csv"
    model_path = here / "../ai_automation_model.pkl"
    threshold = 80.0
    out_path = here / "cor_risk_scored.csv"
    unmatched_out = here / "cor_unmatched.csv"
    top_n = 20

    if not cor_path.exists():
        raise FileNotFoundError(f"Fișier COR inexistent: {cor_path}")
    if not esco_path.exists():
        raise FileNotFoundError(f"Fișier ESCO inexistent: {esco_path}")
    if not model_path.exists():
        raise FileNotFoundError(f"Fișier model inexistent: {model_path}")

    cor = pd.read_csv(cor_path)
    esco = pd.read_csv(esco_path)

    cor_name_col = pick_first_existing(cor.columns.tolist(), COR_NAME_CANDIDATES, "nume ocupație COR")
    esco_job_col = pick_first_existing(esco.columns.tolist(), ESCO_JOB_CANDIDATES, "nume ocupație ESCO")

    ensure_columns(esco, [*REQUIRED_FEATURES], "ESCO")

    cor["denumire_clean"] = normalize_text(cor[cor_name_col])
    esco["job_clean"] = normalize_text(esco[esco_job_col])

    cor_all = match_jobs(cor, esco)
    cor_unmatched = cor_all[cor_all["match_score"] < threshold].copy()
    cor = cor_all[cor_all["match_score"] >= threshold].copy()

    unmatched_path = unmatched_out
    cor_unmatched.to_csv(unmatched_path, index=False, encoding="utf-8-sig")

    if cor.empty:
        raise ValueError(
            "Nicio ocupație COR nu a trecut pragul de matching. "
            f"Prag curent: {threshold}. Modifică variabila threshold din main()."
        )

    # Aduce features din ESCO în funcție de ocupația mapată.
    feature_map = esco.drop_duplicates(subset=["job_clean"]).set_index("job_clean")[REQUIRED_FEATURES]
    cor = cor.join(feature_map, on="matched_job")

    ensure_columns(cor, REQUIRED_FEATURES, "COR după matching")
    cor[REQUIRED_FEATURES] = cor[REQUIRED_FEATURES].apply(pd.to_numeric, errors="coerce")
    cor = cor.dropna(subset=REQUIRED_FEATURES)

    model = load_model(model_path)
    cor["predicted_score"] = model.predict(cor[REQUIRED_FEATURES])
    cor["predicted_score"] = pd.to_numeric(cor["predicted_score"], errors="coerce")
    cor = cor.dropna(subset=["predicted_score"])
    cor["predicted_score"] = cor["predicted_score"].clip(0, 100)
    cor["risk_level"] = cor["predicted_score"].apply(classify)
    cor = cor.sort_values(["predicted_score", "match_score"], ascending=[False, False]).reset_index(drop=True)

    top_n = max(1, int(top_n))
    high_path = here / "cor_top_high.csv"
    medium_path = here / "cor_top_medium.csv"
    low_path = here / "cor_top_low.csv"

    cor[cor["risk_level"] == "high"].head(top_n).to_csv(high_path, index=False, encoding="utf-8-sig")
    cor[cor["risk_level"] == "medium"].head(top_n).to_csv(medium_path, index=False, encoding="utf-8-sig")
    cor.sort_values("predicted_score", ascending=True).head(top_n).to_csv(low_path, index=False, encoding="utf-8-sig")

    cor.to_csv(out_path, index=False, encoding="utf-8-sig")

    # Avertizare pentru match-uri cu scor redus (între prag și 90) — posibil eronate
    borderline = cor[(cor["match_score"] >= threshold) & (cor["match_score"] < 90)]
    if not borderline.empty:
        print(f"\nATENTIE: {len(borderline)} ocupatii COR au scor de potrivire intre "
              f"{threshold:.0f} si 90 - verificati manual cor_unmatched_borderline.csv")
        borderline_path = here / "cor_unmatched_borderline.csv"
        borderline[[cor_name_col, "matched_job", "match_score", "predicted_score", "risk_level"]].to_csv(
            borderline_path, index=False, encoding="utf-8-sig"
        )

    print(f"Rezultate salvate: {out_path.resolve()}")
    print(f"Nemapate salvate: {unmatched_path.resolve()} (randuri: {len(cor_unmatched)})")
    print(f"Top high: {high_path.resolve()}")
    print(f"Top medium: {medium_path.resolve()}")
    print(f"Top low: {low_path.resolve()}")
    print(f"Randuri finale: {len(cor)}")
    print(f"Coloana COR folosita pentru nume: {cor_name_col}")
    print(f"Coloana ESCO folosita pentru nume: {esco_job_col}")
    if len(cor) > 0:
        preview_cols = ["matched_job", "match_score", "predicted_score", "risk_level"]
        if "cod_cor" in cor.columns:
            preview_cols.insert(0, "cod_cor")
        if cor_name_col in cor.columns:
            preview_cols.insert(1 if "cod_cor" in cor.columns else 0, cor_name_col)
        print(cor[preview_cols].head(10))


if __name__ == "__main__":
    main()
