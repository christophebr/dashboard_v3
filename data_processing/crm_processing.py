"""Chargement et calcul de KPI à partir de l'export CRM "Tous les incidents".

Le CRM exporte un fichier Excel contenant l'ensemble des incidents (tickets)
créés dans tous les environnements (PMAJ alias TMAJ, PXV3/Vehis,
HELIO/DIAPASON, STELLAIR, HELIO-DMP). Les fonctions ci-dessous proposent un
pipeline standard, équivalent à ce que fait `hubspot_processing` pour les
tickets HubSpot :

    df_raw       = load_crm_data(CRM_DATA_PATH)
    df_clean     = process_crm_data(df_raw)
    df_tmaj_12m  = filter_crm_par_environnement(df_clean, "TMAJ")
    df_tmaj_12m  = filter_crm_periode(df_tmaj_12m, periode="12_mois")
    kpis         = compute_crm_kpis(df_tmaj_12m)

Le périmètre par défaut exclut le propriétaire « Admin Olaqin CRM365 CRM365 »
qui correspond à des tickets administratifs auto-créés.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Iterable

import pandas as pd

DEFAULT_EXCLUDED_OWNERS: tuple[str, ...] = ("Admin Olaqin CRM365 CRM365",)

ENVIRONMENT_TO_TYPE_CONTRAT: dict[str, str] = {
    "TMAJ": "PMAJ",
    "PMAJ": "PMAJ",
    "PXV3": "PXV3/Vehis",
    "VEHIS": "PXV3/Vehis",
    "HELIO": "HELIO/DIAPASON",
    "DIAPASON": "HELIO/DIAPASON",
    "STELLAIR": "STELLAIR",
    "HELIO-DMP": "HELIO-DMP",
    "DMP": "HELIO-DMP",
}

# Mapping abréviations CRM → nom lisible de l'intervenant.
# Les abréviations peuvent contenir des points, des espaces ou de la casse
# variable (ex. "K.EL" ↔ "KEL"). La normalisation est faite par
# `normalize_intervenant_name` ci-dessous.
INTERVENANT_NAME_MAP: dict[str, str] = {
    "KEL": "Karim",
    "K.EL": "Karim",
    "KYF": "Synalcom",
    "MM": "Synalcom",
    "DML": "Synalcom",
    "ET": "Emmanuelle",
    "YL": "Yohann",
    "POUR SABRINA": "Sabrina",
    "SABRINA": "Sabrina",
    "SABRINA M": "Sabrina",
}

EXPECTED_COLUMNS: tuple[str, ...] = (
    "(Ne pas modifier) Incident",
    "(Ne pas modifier) Modifié le",
    "Propriétaire",
    "Intervenant",
    "N° client",
    "Client",
    "Sujet",
    "Type contrat",
    "Statut",
    "Echéance",
    "Date fin",
    "Avancement",
    "Suivi requis",
    "Créé le",
    "N° incident",
)


# Noms d'onglets candidats où trouver la table des incidents.
# Le CRM exporte parfois un classeur multi-onglets (Détails1, Détails2…) ;
# la table principale est `Tous les incidents` (avec ou sans préfixe "5 - ").
_CRM_SHEET_NAME_HINTS: tuple[str, ...] = (
    "tous les incidents",
    "incidents",
)

# Colonnes attendues pour valider qu'un onglet est bien la table cible.
_CRM_REQUIRED_COLUMNS: tuple[str, ...] = (
    "Propriétaire",
    "Type contrat",
    "Statut",
    "Créé le",
)


def load_crm_data(crm_path: str) -> pd.DataFrame:
    """Lit le ou les exports Excel CRM présents dans `crm_path`.

    Si plusieurs fichiers `.xlsx` / `.xls` sont présents, ils sont concaténés.
    Les fichiers de verrouillage Office (`~$...`) et fichiers cachés sont
    ignorés. Le bon onglet est détecté automatiquement parmi ceux du
    classeur : on cible en priorité un onglet dont le nom contient
    « Tous les incidents » / « Incidents », puis on retombe sur le
    premier onglet contenant les colonnes attendues.
    """
    if not os.path.isdir(crm_path):
        raise FileNotFoundError(
            f"Le dossier des exports CRM n'existe pas : '{crm_path}'.\n"
            f"Créez ce dossier et déposez-y l'export Excel CRM (« Tous les incidents »)."
        )

    excel_files = [
        os.path.join(crm_path, f)
        for f in sorted(os.listdir(crm_path))
        if f.lower().endswith((".xls", ".xlsx"))
        and not f.startswith(".")
        and not f.startswith("~$")
        and os.path.isfile(os.path.join(crm_path, f))
    ]
    if not excel_files:
        raise FileNotFoundError(
            f"Aucun fichier Excel trouvé dans '{crm_path}'.\n"
            f"Déposez l'export CRM (« Tous les incidents.xlsx ») dans ce dossier."
        )

    frames: list[pd.DataFrame] = []
    for path in excel_files:
        try:
            frames.append(_read_crm_sheet(path))
        except Exception as exc:
            raise RuntimeError(
                f"Erreur lors de la lecture du fichier CRM '{path}' : {exc}"
            ) from exc
    return pd.concat(frames, ignore_index=True)


def _read_crm_sheet(path: str) -> pd.DataFrame:
    """Lit l'onglet « Tous les incidents » d'un classeur CRM.

    Détecte le bon onglet :
    1. Par mot-clé dans le nom (« Tous les incidents », « Incidents »…).
    2. À défaut, on essaie chaque onglet et on retient le premier qui
       contient les colonnes attendues.
    """
    excel = pd.ExcelFile(path)
    candidate_sheets: list[str] = []
    for sheet in excel.sheet_names:
        lower = sheet.lower()
        if any(hint in lower for hint in _CRM_SHEET_NAME_HINTS):
            candidate_sheets.append(sheet)
    # On ajoute ensuite les autres onglets en fallback.
    candidate_sheets.extend(
        s for s in excel.sheet_names if s not in candidate_sheets
    )

    last_error: Exception | None = None
    for sheet in candidate_sheets:
        try:
            df = pd.read_excel(path, sheet_name=sheet)
        except Exception as exc:  # onglet protégé / autre
            last_error = exc
            continue
        cleaned_cols = {c.strip() for c in df.columns if isinstance(c, str)}
        if _CRM_REQUIRED_COLUMNS[0] in cleaned_cols and "Type contrat" in cleaned_cols:
            return df

    raise RuntimeError(
        f"Impossible de localiser l'onglet « Tous les incidents » dans "
        f"« {os.path.basename(path)} ». Onglets trouvés : {excel.sheet_names}."
        + (f" Dernière erreur : {last_error}" if last_error else "")
    )


def process_crm_data(
    df: pd.DataFrame,
    exclude_owners: Iterable[str] | None = DEFAULT_EXCLUDED_OWNERS,
) -> pd.DataFrame:
    """Normalise un export CRM brut.

    - Retire les espaces parasites des noms de colonnes (la colonne `Statut `
      est exportée avec un espace de fin par le CRM).
    - Convertit les colonnes de date en `datetime` (`Créé le`, `Date fin`,
      `Echéance`, `(Ne pas modifier) Modifié le`).
    - Supprime les tickets dont le propriétaire est dans `exclude_owners`.
    - Ajoute deux colonnes dérivées :
        * `delai_resolution_jours` : délai en jours entre `Créé le` et
          `Date fin` (NaN si le ticket est encore ouvert).
        * `categorie_sujet`        : préfixe du `Sujet` jusqu'au premier
          " - " (ex. `Courrier reçu - Résiliation` → `Courrier reçu`).
    """
    df = df.copy()
    df.columns = [c.strip() for c in df.columns]

    for col in (
        "Créé le",
        "Date fin",
        "Echéance",
        "(Ne pas modifier) Modifié le",
    ):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    if exclude_owners and "Propriétaire" in df.columns:
        owners = set(exclude_owners)
        df = df[~df["Propriétaire"].isin(owners)].copy()

    if "Date fin" in df.columns and "Créé le" in df.columns:
        delta = df["Date fin"] - df["Créé le"]
        df["delai_resolution_jours"] = delta.dt.total_seconds() / 86400.0

    if "Sujet" in df.columns:
        df["categorie_sujet"] = df["Sujet"].apply(_categorize_sujet)

    if "Intervenant" in df.columns:
        df["intervenant_nom"] = df["Intervenant"].apply(normalize_intervenant_name)

    return df.reset_index(drop=True)


def normalize_intervenant_name(value: object) -> str:
    """Convertit une abréviation CRM en nom lisible.

    - Insensible à la casse, aux espaces de fin et aux points : `K.EL`,
      `KEL`, `kel ` sont tous mappés sur `Karim`.
    - Renvoie `"(non assigné)"` pour les valeurs vides / NaN.
    - Renvoie la valeur d'origine (titre-cased) si elle n'est pas mappée,
      pour ne pas perdre d'information.
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "(non assigné)"
    raw = str(value).strip()
    if not raw:
        return "(non assigné)"
    key = raw.upper()
    if key in INTERVENANT_NAME_MAP:
        return INTERVENANT_NAME_MAP[key]
    # Variante sans points (ex. "K.EL" → "KEL")
    key_no_dots = key.replace(".", "").replace(" ", "")
    for variant, name in INTERVENANT_NAME_MAP.items():
        if variant.replace(".", "").replace(" ", "") == key_no_dots:
            return name
    return raw


def _categorize_sujet(value: object) -> str:
    """Extrait la catégorie d'un `Sujet` CRM.

    Beaucoup de sujets suivent la convention `Famille - Détail`
    (ex. `Courrier reçu - Résiliation`, `Email reçu - Avis de cession`).
    On garde la famille pour pouvoir agréger.
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "(inconnu)"
    text = str(value).strip()
    if not text:
        return "(inconnu)"
    if " - " in text:
        return text.split(" - ", 1)[0].strip()
    if " " in text:
        return text.split(" ", 1)[0].strip()
    return text


def filter_crm_par_environnement(
    df: pd.DataFrame,
    environnement: str,
) -> pd.DataFrame:
    """Filtre sur la colonne `Type contrat` à partir d'un alias d'environnement.

    `environnement="TMAJ"` est traduit en `Type contrat == "PMAJ"`.
    Si l'alias n'est pas connu, on prend la valeur telle quelle pour
    permettre un appel direct du type `filter_crm_par_environnement(df, "PMAJ")`.
    """
    target = ENVIRONMENT_TO_TYPE_CONTRAT.get(environnement.upper(), environnement)
    return df[df["Type contrat"] == target].copy()


def filter_crm_periode(
    df: pd.DataFrame,
    periode: str | tuple | list | None = None,
    debut: pd.Timestamp | datetime | None = None,
    fin: pd.Timestamp | datetime | None = None,
    colonne: str = "Créé le",
) -> pd.DataFrame:
    """Filtre temporel cohérent avec les autres modules du dashboard.

    `periode` accepte :
    - les libellés utilisés ailleurs dans l'app : `"1 an"`,
      `"6 derniers mois"`, `"3 derniers mois"`, `"Dernier mois"` ;
    - les raccourcis techniques : `"30_jours"`, `"3_mois"`, `"6_mois"`,
      `"12_mois"`, `"depuis_2024"`, `"depuis_2025"` ;
    - un tuple `(date_debut, date_fin)` pour une période personnalisée.

    Sinon on utilise `debut` / `fin` explicites.
    """
    if colonne not in df.columns:
        raise KeyError(f"Colonne '{colonne}' absente du DataFrame CRM.")

    today = pd.Timestamp(datetime.now().date())

    # Période personnalisée : tuple (date_debut, date_fin)
    if isinstance(periode, (tuple, list)) and len(periode) == 2:
        debut = pd.Timestamp(periode[0])
        fin = pd.Timestamp(periode[1])
    elif isinstance(periode, str):
        mapping = {
            # Libellés du dashboard (page Support)
            "1 an":              today - pd.DateOffset(years=1),
            "6 derniers mois":   today - pd.DateOffset(months=6),
            "3 derniers mois":   today - pd.DateOffset(months=3),
            "Dernier mois":      today - pd.DateOffset(months=1),
            # Raccourcis techniques
            "30_jours":   today - pd.Timedelta(days=30),
            "3_mois":     today - pd.DateOffset(months=3),
            "6_mois":     today - pd.DateOffset(months=6),
            "12_mois":    today - pd.DateOffset(months=12),
            "depuis_2024": pd.Timestamp("2024-01-01"),
            "depuis_2025": pd.Timestamp("2025-01-01"),
        }
        if periode not in mapping:
            raise ValueError(
                f"Période inconnue : '{periode}'. Valeurs supportées : {sorted(mapping)}"
            )
        debut = mapping[periode]
        fin = today

    out = df.copy()
    if debut is not None:
        out = out[out[colonne] >= pd.Timestamp(debut)]
    if fin is not None:
        out = out[out[colonne] <= pd.Timestamp(fin)]
    return out.reset_index(drop=True)


def compute_crm_kpis(df: pd.DataFrame) -> dict[str, float | int]:
    """KPIs synthétiques sur un DataFrame CRM déjà filtré."""
    total = len(df)
    statut = df["Statut"] if "Statut" in df.columns else pd.Series(dtype=object)
    resolus = int((statut == "Résolu").sum())
    actifs = int((statut == "Actif").sum())
    annules = int((statut == "Annulé(e)").sum())

    kpis: dict[str, float | int] = {
        "total_tickets": int(total),
        "tickets_resolus": resolus,
        "tickets_actifs": actifs,
        "tickets_annules": annules,
        "taux_resolution_pct": round(resolus / total * 100, 1) if total else 0.0,
        "clients_distincts": int(df["N° client"].nunique()) if "N° client" in df.columns else 0,
        "tickets_suivi_requis": int((df.get("Suivi requis") == "Oui").sum()),
    }

    if "delai_resolution_jours" in df.columns:
        delais = df["delai_resolution_jours"].dropna()
        if len(delais):
            kpis.update(
                delai_median_jours=round(float(delais.median()), 2),
                delai_moyen_jours=round(float(delais.mean()), 2),
                delai_p75_jours=round(float(delais.quantile(0.75)), 2),
                delai_p95_jours=round(float(delais.quantile(0.95)), 2),
                pct_resolus_24h=round(float((delais <= 1).mean() * 100), 1),
                pct_resolus_7j=round(float((delais <= 7).mean() * 100), 1),
            )

    if "Echéance" in df.columns and "Statut" in df.columns:
        en_retard = (
            (df["Echéance"].notna())
            & (df["Echéance"] < pd.Timestamp(datetime.now()))
            & (df["Statut"] != "Résolu")
        )
        kpis["tickets_en_retard"] = int(en_retard.sum())

    return kpis


def compute_crm_evolution_mensuelle(df: pd.DataFrame) -> pd.Series:
    """Nombre de tickets par mois (`Créé le`)."""
    if "Créé le" not in df.columns:
        return pd.Series(dtype=int)
    mois = df["Créé le"].dt.to_period("M").astype(str)
    return mois.value_counts().sort_index()


def compute_crm_par_proprietaire(df: pd.DataFrame) -> pd.Series:
    return _value_counts(df, "Propriétaire")


def compute_crm_par_intervenant(df: pd.DataFrame, top: int | None = None) -> pd.Series:
    s = _value_counts(df, "Intervenant", dropna=True)
    return s.head(top) if top else s


def compute_crm_par_intervenant_normalise(
    df: pd.DataFrame,
    inclure_non_assigne: bool = False,
    top: int | None = None,
) -> pd.Series:
    """Agrège les tickets par intervenant en utilisant les noms lisibles.

    Les abréviations CRM (`KEL`, `ET`, `YL`, `KYF`, `MM`, `DML`, ...) sont
    remplacées par les noms réels (Karim, Emmanuelle, Yohann, Synalcom...).

    Par défaut on exclut les tickets sans intervenant assigné. Passe
    `inclure_non_assigne=True` pour visualiser aussi le volume non
    attribué.
    """
    if "intervenant_nom" not in df.columns:
        # Si le DataFrame n'a pas été passé par `process_crm_data`, on
        # calcule à la volée.
        col = df.get("Intervenant", pd.Series(dtype=object)).apply(normalize_intervenant_name)
    else:
        col = df["intervenant_nom"]

    if not inclure_non_assigne:
        col = col[col != "(non assigné)"]

    serie = col.value_counts()
    return serie.head(top) if top else serie


def compute_crm_par_type_contrat(df: pd.DataFrame) -> pd.Series:
    return _value_counts(df, "Type contrat")


def compute_crm_top_clients(df: pd.DataFrame, n: int = 10) -> pd.Series:
    return _value_counts(df, "Client").head(n)


def compute_crm_categories_sujets(df: pd.DataFrame, top: int = 15) -> pd.Series:
    return _value_counts(df, "categorie_sujet").head(top)


def _value_counts(
    df: pd.DataFrame, column: str, dropna: bool = False
) -> pd.Series:
    if column not in df.columns:
        return pd.Series(dtype=int)
    return df[column].value_counts(dropna=dropna)
