"""
Lecture et synthèse du fichier « Besoin ETP Support » (évolution licences vs charge support).

Fichier attendu : `data/Besoin ETP Support 2025.xlsx`.

- **Sheet1** : série mensuelle agrégée (licences, charge Stellair/Affid en « jour », etc.).
  La colonne « Ration Licences / Stellair » n’est **pas** le ratio licences / appels téléphoniques.

- **Analyse** : contient le **Ratio Licences / Appels** (licences ÷ appels), indicateur d’intensité
  d’appels par rapport au parc : plus le ratio est **élevé**, plus il y a de **licences par appel**
  (donc moins d’appels par licence, toutes choses égales par ailleurs).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd

DEFAULT_XLSX = Path(__file__).resolve().parents[1] / "data" / "Besoin ETP Support 2025.xlsx"


def load_analyse_ratio_licences_appels(path: str | Path) -> pd.DataFrame:
    """
    Feuille « Analyse » : une ou deux lignes par mois ; on garde les lignes où
    « Ratio Licences / Appels » est renseigné (série officielle du classeur).
    """
    path = Path(path)
    df = pd.read_excel(path, sheet_name="Analyse", header=5)
    df = df.rename(columns=lambda x: str(x).strip())
    col_mois = "Mois"
    col_ratio = "Ratio Licences / Appels"
    need = [col_mois, col_ratio, "Appels", "Licences Stellair (Affid)"]
    missing = [c for c in need if c not in df.columns]
    if missing:
        raise ValueError(f"Colonnes manquantes dans Analyse : {missing}")

    sub = df[need].copy()
    sub[col_mois] = pd.to_datetime(sub[col_mois], errors="coerce")
    for c in need[1:]:
        sub[c] = pd.to_numeric(sub[c], errors="coerce")
    sub = sub[sub[col_mois].notna()]
    sub = sub[sub[col_ratio].notna()].sort_values(col_mois).reset_index(drop=True)
    sub["interpretation"] = (
        "Licences par unité d’appel (ratio du fichier) ; hausse = plus de licences par appel."
    )
    return sub


def load_besoin_etp_sheet1(path: str | Path) -> pd.DataFrame:
    """Charge la feuille Sheet1 : première ligne de données = en-têtes (colonnes 3+)."""
    path = Path(path)
    raw = pd.read_excel(path, sheet_name="Sheet1", header=None)
    cols = [
        str(x).strip() if pd.notna(x) else f"col_{i}"
        for i, x in enumerate(raw.iloc[0, 3:15].tolist())
    ]
    data = raw.iloc[1:, 3:15].copy()
    data.columns = cols
    data = data.dropna(how="all")
    data["Mois"] = pd.to_datetime(data["Mois"], errors="coerce")
    data = data[data["Mois"].notna()].sort_values("Mois").reset_index(drop=True)
    for c in data.columns:
        if c != "Mois":
            data[c] = pd.to_numeric(data[c], errors="coerce")
    return data


def compute_summary_stats(df: pd.DataFrame) -> Dict[str, Any]:
    """Corrélations et régression simple charge Stellair ~ licences."""
    out: Dict[str, Any] = {}
    pairs = [
        ("Licences Stellair Affid", "Stellair"),
        ("Licences Stellair Affid", "Affid"),
        ("Licences Stellair Affid", "Ration Licences / Stellair"),
    ]
    key_map = {
        ("Licences Stellair Affid", "Stellair"): "corr_licences_vs_charge_stellair_jour",
        ("Licences Stellair Affid", "Affid"): "corr_licences_vs_charge_affid_jour",
        ("Licences Stellair Affid", "Ration Licences / Stellair"): "corr_licences_vs_ratio_licences_sur_stellair",
    }
    for a, b in pairs:
        if a not in df.columns or b not in df.columns:
            continue
        s = df[[a, b]].dropna()
        if len(s) >= 4:
            out[key_map.get((a, b), f"corr_{a}_{b}")] = float(s[a].corr(s[b]))

    clean = df[["Licences Stellair Affid", "Stellair"]].dropna()
    if len(clean) >= 3:
        X = np.c_[np.ones(len(clean)), clean["Licences Stellair Affid"].values]
        y = clean["Stellair"].values
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        out["reg_stellair_intercept"] = float(beta[0])
        out["reg_stellair_slope_per_licence"] = float(beta[1])
        out["reg_n"] = int(len(clean))

    if len(df):
        out["periode_debut"] = str(df["Mois"].min().date())
        out["periode_fin"] = str(df["Mois"].max().date())
        out["nb_mois"] = int(len(df))
        lic = df["Licences Stellair Affid"].dropna()
        if len(lic) >= 2:
            out["evolution_licences_premier_dernier_pct"] = float(
                100 * (lic.iloc[-1] - lic.iloc[0]) / max(lic.iloc[0], 1e-9)
            )
    return out


def _stats_ratio_licences_appels(ratio_df: pd.DataFrame) -> Dict[str, Any]:
    """Premier / dernier ratio Analyse + évolution."""
    if ratio_df.empty or "Ratio Licences / Appels" not in ratio_df.columns:
        return {}
    r = ratio_df["Ratio Licences / Appels"].dropna()
    if r.empty:
        return {}
    out: Dict[str, Any] = {
        "ratio_licences_sur_appels_premier": float(r.iloc[0]),
        "ratio_licences_sur_appels_dernier": float(r.iloc[-1]),
        "mois_ratio_premier": str(ratio_df["Mois"].iloc[0].date()),
        "mois_ratio_dernier": str(ratio_df["Mois"].iloc[-1].date()),
        "nb_points_ratio": int(len(r)),
    }
    if r.iloc[0]:
        out["evolution_ratio_pct"] = float(100 * (r.iloc[-1] - r.iloc[0]) / r.iloc[0])
    return out


def run_export(
    xlsx_path: Optional[str | Path] = None,
    output_dir: Optional[str | Path] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Charge le classeur, écrit la série Sheet1, la série « Ratio licences / appels » (Analyse),
    et un CSV de synthèse (volumes Sheet1 + ratio Analyse).
    Retourne (df_sheet1, df_ratio_la, resume).
    """
    path = Path(xlsx_path) if xlsx_path else DEFAULT_XLSX
    if not path.is_file():
        raise FileNotFoundError(path)

    df = load_besoin_etp_sheet1(path)
    stats = compute_summary_stats(df)
    try:
        ratio_df = load_analyse_ratio_licences_appels(path)
        stats.update(_stats_ratio_licences_appels(ratio_df))
    except Exception as e:
        print(f"⚠️ Feuille Analyse (ratio licences/appels) : {e}")
        ratio_df = pd.DataFrame()
    resume = pd.DataFrame([stats])

    out_dir = Path(output_dir) if output_dir else path.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    stem = path.stem.replace(" ", "_")
    serie_path = out_dir / f"{stem}_serie_mensuelle.csv"
    ratio_path = out_dir / f"{stem}_ratio_licences_appels_analyse.csv"
    resume_path = out_dir / f"{stem}_resume_stats.csv"

    df.to_csv(serie_path, index=False, encoding="utf-8-sig")
    resume.to_csv(resume_path, index=False, encoding="utf-8-sig")
    print(f"Écrit : {serie_path}")
    print(f"Écrit : {resume_path}")
    if not ratio_df.empty:
        ratio_df.to_csv(ratio_path, index=False, encoding="utf-8-sig")
        print(f"Écrit : {ratio_path}")
    return df, ratio_df, resume


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    _, ratio_df, resume = run_export(
        DEFAULT_XLSX, output_dir=root / "data" / "Affid" / "analyse_appels_tickets"
    )
    if not ratio_df.empty and "Ratio Licences / Appels" in ratio_df.columns:
        r0 = ratio_df["Ratio Licences / Appels"].iloc[0]
        r1 = ratio_df["Ratio Licences / Appels"].iloc[-1]
        print(
            f"→ Ratio Licences/Appels (feuille Analyse) : {r0:.2f} → {r1:.2f} "
            f"(licences par appel, selon votre classeur)"
        )
