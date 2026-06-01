"""
Analyse : volume moyen de tickets support par client après souscription Stellair.

Date de souscription (proxy) : date de fermeture du ticket pipeline ADV dont le sujet est
« Suivi de ma commande » (traitement de commande). Si plusieurs tickets pour un même contact,
on retient la plus ancienne fermeture (première commande traitée).

Tickets support : pipelines SSI, SSIA, SPSA (aligné sur kpi_generation).

Filtre : par défaut, seuls les clients dont la souscription remonte à au moins 12 mois
avant la dernière date de ticket support sont retenus (cohorte exploitable sur mois 1, 2, 3…
et comparaison avec les mois suivants).

Analyse complémentaire (run_formation_cohort_analysis) : clients avec ticket pipeline
« Formation Stellair », souscription ADV à partir du 1er juin 2025, moyennes de tickets
support sur les 6 premiers mois d'utilisation (même règle de moyenne, zéros inclus).

Analyse comparative (run_formation_buyers_vs_rest_cohort_analysis) : sur la cohorte 12 mois,
clients ayant une transaction formation « Fermé gagné » (export transactions) vs les autres ;
même métriques d'ancienneté et moyenne totale de tickets support par client après souscription.

Analyse (run_support_demands_after_formation_eligible_6mois) : clients dont la première formation
gagnée date d'au moins 6 mois avant la fin des tickets ; comptage des tickets support créés
après la date de formation jusqu'à la fin des données.

Tableau (run_tenure_table_cohorte12m_formation_recue_6mois_plus) : même format que l'analyse
principale (mois_depuis_souscription, mois_utilisation, nb_contacts_eligibles, nb_tickets,
moyenne_tickets_par_contact) pour le sous-ensemble « cohorte 12 mois » ∩ « formation gagnée
il y a au moins 6 mois ».

Méthodologie cohorte (fichier *_methodologie_cohorte_anciennete_support.txt + doc ci-dessous) :
Les N clients (ex. 1294) ne sont **pas** une cohorte ayant tous souscrit le même mois. Ce sont
tous les contacts dont le **proxy de souscription** (1er ticket ADV « Suivi de ma commande » fermé)
remonte à **au moins 12 mois** avant la **dernière date de création** d'un ticket support dans
l'export. Chaque client a donc une **date de souscription différente** ; l'axe « mois depuis
souscription » (0 à 12) aligne **chaque** parcours sur son propre calendrier (mois calendaires).
Pour un mois d'ancienneté m, le dénominateur = clients pour lesquels au moins m mois se sont
écoulés entre le mois de souscription et la fin des données (fenêtre observable). La moyenne =
moyenne des volumes de tickets **ce mois-là** par client (zéros inclus).

Export agrégé (un seul .xlsx, méthodologie + tables) : script
``data_processing/analyse_support_stellair_complet.py`` ou fonction
``export_support_stellair_workbook``.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import pandas as pd

from data_processing.hubspot_ticket_category_macros import (
    MACRO_INFOS_LOGICIELS,
    MACRO_LECTEURS,
    macro_groupe_comex,
)

# Identifiants HubSpot des tickets « commande » (ADV)
COL_PIPELINE = "Pipeline"
COL_SUBJECT = "Sujet de la demande"
ADV_PIPELINE = "ADV"
ADV_ORDER_SUBJECT = "Suivi de ma commande"
COL_CLOSE = "Date de fermeture"
COL_CREATE = "Date de création"
COL_CONTACT_IDS = "Associated Contact IDs"
COL_CATEGORIE = "Catégorie"

# Pipelines considérés comme demandes support (hors ADV / hors commande)
SUPPORT_PIPELINES = ("SSI", "SSIA", "SPSA")

# Ticket « souscription formation » (repère client formé)
FORMATION_PIPELINE = "Formation Stellair"

# Cohorte : souscription ADV à partir de cette date (inclus)
SUBSCRIPTION_FROM_DATE = pd.Timestamp("2025-06-01")

# Ne garder que les clients dont la souscription date d'au moins N mois avant la fin des données
# (pour comparer mois 1…12… sans biais de cohorte trop récente)
MIN_SUBSCRIPTION_AGE_MONTHS = 12

# Analyse formation : nombre de premiers mois d'utilisation (mois calendaires)
FORMATION_FIRST_USAGE_MONTHS = 6

# Export HubSpot « transactions » formations (fichier le plus récent du dossier si non précisé)
FORMATION_TRANSACTIONS_DIR = "data/Affid/Hubspot/formation"
COL_FORMATION_PHASE = "Phase de la transaction"
COL_FORMATION_ASSOC_CONTACT_IDS = "Associated Contact IDs"
COL_FORMATION_CLOSE = "Date de fermeture"

# Formation reçue il y a au moins N mois (avant la date de référence = fin des tickets support)
MIN_MONTHS_SINCE_FORMATION_FOR_ANALYSIS = 6


def _normalize_contact_id(val) -> Optional[str]:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    s = str(val).strip()
    if not s or s.lower() == "nan":
        return None
    if s.endswith(".0") and s[:-2].isdigit():
        s = s[:-2]
    return s if s.isdigit() else None


def parse_contact_ids_cell(val) -> List[str]:
    """Extrait les IDs numériques depuis une cellule (séparateurs ; , espace)."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return []
    s = str(val).strip()
    if not s or s.lower() == "nan":
        return []
    out: List[str] = []
    for part in s.replace(",", ";").split(";"):
        hid = _normalize_contact_id(part.strip())
        if hid:
            out.append(hid)
    return out


def explode_contacts(df: pd.DataFrame) -> pd.DataFrame:
    """Une ligne par (ticket, contact_id)."""
    if df.empty or COL_CONTACT_IDS not in df.columns:
        return pd.DataFrame()

    s = df[COL_CONTACT_IDS].astype(str).replace({"nan": ""})
    split = s.str.split(r"[;,]", regex=True)
    tmp = df.assign(_ids=split).explode("_ids")
    tmp["_contact_id"] = tmp["_ids"].map(
        lambda x: _normalize_contact_id(str(x).strip() if x is not None else "")
    )
    tmp = tmp[tmp["_contact_id"].notna()].drop(columns=["_ids"])
    return tmp


def subscription_date_per_contact(df: pd.DataFrame) -> pd.DataFrame:
    """
    Pour chaque contact : min(Date de fermeture) sur les tickets ADV « Suivi de ma commande ».
    """
    if COL_CLOSE not in df.columns:
        raise ValueError(f"Colonne manquante : {COL_CLOSE}")

    adv = df[
        (df[COL_PIPELINE] == ADV_PIPELINE)
        & (df[COL_SUBJECT].astype(str).str.strip() == ADV_ORDER_SUBJECT)
    ].copy()
    adv[COL_CLOSE] = pd.to_datetime(adv[COL_CLOSE], errors="coerce")
    adv = adv[adv[COL_CLOSE].notna()]
    if adv.empty:
        return pd.DataFrame(columns=["contact_id", "date_souscription"])

    ex = explode_contacts(adv)
    if ex.empty:
        return pd.DataFrame(columns=["contact_id", "date_souscription"])

    sub = (
        ex.groupby("_contact_id", as_index=False)[COL_CLOSE]
        .min()
        .rename(columns={"_contact_id": "contact_id", COL_CLOSE: "date_souscription"})
    )
    return sub


def support_tickets_df(df: pd.DataFrame) -> pd.DataFrame:
    """Tickets dans les pipelines support, avec date de création parsée."""
    d = df[df[COL_PIPELINE].isin(SUPPORT_PIPELINES)].copy()
    d[COL_CREATE] = pd.to_datetime(d[COL_CREATE], errors="coerce")
    return d[d[COL_CREATE].notna()]


def find_latest_formation_transactions_xlsx(
    directory: str | Path | None = None,
) -> Optional[Path]:
    """Retourne le fichier .xlsx le plus récent du dossier formations, ou None."""
    root = Path(__file__).resolve().parents[1]
    d = Path(directory) if directory else root / FORMATION_TRANSACTIONS_DIR
    if not d.is_dir():
        return None
    cands = sorted(
        d.glob("*.xlsx"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return cands[0] if cands else None


def load_formation_contact_first_win_close_date(
    transactions_xlsx: str | Path,
    phase_filtre_gagne: bool = True,
) -> pd.DataFrame:
    """
    Pour chaque contact : date de la première transaction formation « gagnée »
    (min Date de fermeture parmi les lignes Fermé gagné associées au contact).
    Colonnes : contact_id, date_formation.
    """
    path = Path(transactions_xlsx)
    if not path.is_file():
        raise FileNotFoundError(path)
    df = pd.read_excel(path)
    if COL_FORMATION_ASSOC_CONTACT_IDS not in df.columns:
        raise ValueError(f"Colonne manquante : {COL_FORMATION_ASSOC_CONTACT_IDS}")
    if COL_FORMATION_CLOSE not in df.columns:
        raise ValueError(f"Colonne manquante : {COL_FORMATION_CLOSE}")
    work = df
    if phase_filtre_gagne and COL_FORMATION_PHASE in df.columns:
        work = work[
            work[COL_FORMATION_PHASE].astype(str).str.lower().str.contains("gagn", na=False)
        ]
    rows: List[Dict[str, Any]] = []
    for _, r in work.iterrows():
        d = pd.to_datetime(r.get(COL_FORMATION_CLOSE), errors="coerce")
        if pd.isna(d):
            continue
        for cid in parse_contact_ids_cell(r.get(COL_FORMATION_ASSOC_CONTACT_IDS)):
            rows.append({"contact_id": cid, "date_formation": d})
    if not rows:
        return pd.DataFrame(columns=["contact_id", "date_formation"])
    out = pd.DataFrame(rows)
    out = out.groupby("contact_id", as_index=False)["date_formation"].min()
    return out


def load_formation_transaction_contact_ids(
    transactions_xlsx: str | Path,
    phase_filtre_gagne: bool = True,
) -> Set[str]:
    """
    Contacts ayant au moins une transaction formation dans l'export HubSpot.
    Par défaut : phases contenant « gagn » (ex. Fermé gagné).
    IDs issus de « Associated Contact IDs » uniquement.
    """
    path = Path(transactions_xlsx)
    if not path.is_file():
        raise FileNotFoundError(path)
    df = pd.read_excel(path)
    if COL_FORMATION_ASSOC_CONTACT_IDS not in df.columns:
        raise ValueError(f"Colonne manquante : {COL_FORMATION_ASSOC_CONTACT_IDS}")
    work = df
    if phase_filtre_gagne and COL_FORMATION_PHASE in df.columns:
        work = work[
            work[COL_FORMATION_PHASE].astype(str).str.lower().str.contains("gagn", na=False)
        ]
    out: Set[str] = set()
    for val in work[COL_FORMATION_ASSOC_CONTACT_IDS]:
        out.update(parse_contact_ids_cell(val))
    return out


def mean_tickets_support_par_client_apres_sub(
    df: pd.DataFrame, sub: pd.DataFrame
) -> float:
    """
    Moyenne (sur les contacts de sub) du nombre total de tickets support après date_souscription.
    """
    if sub.empty:
        return float("nan")
    sup = support_tickets_df(df)
    sup_ex = explode_contacts(sup).rename(columns={"_contact_id": "contact_id"})
    sup_ex[COL_CREATE] = pd.to_datetime(sup_ex[COL_CREATE], errors="coerce")
    merged = sup_ex.merge(sub, on="contact_id", how="inner")
    merged = merged[merged[COL_CREATE] > merged["date_souscription"]]
    elig = sub["contact_id"].unique()
    per_contact = merged.groupby("contact_id").size().reindex(elig, fill_value=0)
    return float(per_contact.mean())


def contact_ids_with_formation_pipeline(df: pd.DataFrame) -> pd.Series:
    """IDs contact ayant au moins un ticket dans le pipeline Formation Stellair."""
    if COL_PIPELINE not in df.columns:
        return pd.Series(dtype=object)
    form = df[df[COL_PIPELINE].astype(str).str.strip() == FORMATION_PIPELINE]
    if form.empty:
        return pd.Series(dtype=object)
    ex = explode_contacts(form)
    if ex.empty:
        return pd.Series(dtype=object)
    return ex["_contact_id"].drop_duplicates().reset_index(drop=True)


def compute_tenure_formation_cohort_first_months(
    df: pd.DataFrame,
    subscription_from: pd.Timestamp = SUBSCRIPTION_FROM_DATE,
    first_months: int = FORMATION_FIRST_USAGE_MONTHS,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Cohorte : souscription ADV à partir de subscription_from, contact avec au moins un ticket
    « Formation Stellair ». Moyenne de tickets support par client et par mois d'utilisation
    sur les first_months premiers mois calendaires (0 = mois de la souscription), zéros inclus.

    Retourne (tenure, contacts_cohorte).
    """
    empty_cols = [
        "mois_depuis_souscription",
        "mois_utilisation",
        "nb_contacts_eligibles",
        "nb_tickets",
        "moyenne_tickets_par_contact",
    ]
    sub = subscription_date_per_contact(df)
    if sub.empty:
        return pd.DataFrame(columns=empty_cols), pd.DataFrame(
            columns=["contact_id", "date_souscription"]
        )

    form_ids = set(contact_ids_with_formation_pipeline(df).astype(str))
    if not form_ids:
        return pd.DataFrame(columns=empty_cols), pd.DataFrame(
            columns=["contact_id", "date_souscription"]
        )

    sub = sub[sub["date_souscription"] >= pd.Timestamp(subscription_from)].copy()
    sub = sub[sub["contact_id"].isin(form_ids)]
    if sub.empty:
        return pd.DataFrame(columns=empty_cols), pd.DataFrame(
            columns=["contact_id", "date_souscription"]
        )

    sup = support_tickets_df(df)
    sup_ex = explode_contacts(sup).rename(columns={"_contact_id": "contact_id"})
    sup_ex[COL_CREATE] = pd.to_datetime(sup_ex[COL_CREATE], errors="coerce")
    merged = sup_ex.merge(sub, on="contact_id", how="inner")
    merged = merged[merged[COL_CREATE] > merged["date_souscription"]]

    sup_all = support_tickets_df(df)
    if not sup_all.empty:
        max_date = sup_all[COL_CREATE].max()
    elif not merged.empty:
        max_date = merged[COL_CREATE].max()
    else:
        max_date = pd.Timestamp.now(tz=None)

    sub = sub.copy()
    sub["max_m_observable"] = (
        (max_date.year - sub["date_souscription"].dt.year) * 12
        + (max_date.month - sub["date_souscription"].dt.month)
    )

    if not merged.empty:
        merged["mois_depuis_souscription"] = _month_offset_calendar(
            merged[COL_CREATE], merged["date_souscription"]
        )
        merged = merged[merged["mois_depuis_souscription"].between(0, first_months - 1)]
    else:
        merged = pd.DataFrame()

    max_idx = first_months - 1
    rows = []
    for m in range(0, max_idx + 1):
        elig = sub[sub["max_m_observable"] >= m]["contact_id"].unique()
        nb_elig = len(elig)
        if merged.empty:
            sub_m = pd.DataFrame()
        else:
            sub_m = merged[merged["mois_depuis_souscription"] == m]
        nb_tickets = len(sub_m)
        if nb_elig == 0:
            mean_v = 0.0
        else:
            per_contact = sub_m.groupby("contact_id").size().reindex(elig, fill_value=0)
            mean_v = float(per_contact.mean())
        rows.append(
            {
                "mois_depuis_souscription": m,
                "mois_utilisation": m + 1,
                "nb_contacts_eligibles": int(nb_elig),
                "nb_tickets": int(nb_tickets),
                "moyenne_tickets_par_contact": round(mean_v, 4),
            }
        )

    return pd.DataFrame(rows), sub[["contact_id", "date_souscription"]].drop_duplicates()


def compute_monthly_mean_support_after_subscription(
    df: pd.DataFrame,
    min_subscription_age_months: int = MIN_SUBSCRIPTION_AGE_MONTHS,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Retourne :
    - monthly : par mois calendaire (période), moyenne des tickets support par contact
      (uniquement tickets créés ce mois-là, strictement après date_souscription).
    - contacts : table contact_id, date_souscription (filtrée si ancienneté minimale > 0).

    Si min_subscription_age_months > 0 : seuls les contacts dont la souscription remonte à au
    moins ce délai avant la dernière date de ticket support sont retenus.
    """
    empty_m = pd.DataFrame(
        columns=[
            "periode_mois",
            "nb_contacts_eligibles",
            "nb_tickets_support",
            "moyenne_tickets_par_contact",
        ]
    )
    sub = subscription_date_per_contact(df)
    if sub.empty:
        return empty_m, sub

    sup = support_tickets_df(df)
    sup_ex = explode_contacts(sup)
    if sup_ex.empty:
        return empty_m, sub

    sup_ex[COL_CREATE] = pd.to_datetime(sup_ex[COL_CREATE], errors="coerce")
    sup_ex = sup_ex.rename(columns={"_contact_id": "contact_id"})
    merged = sup_ex.merge(sub, on="contact_id", how="inner")
    merged = merged[merged[COL_CREATE] > merged["date_souscription"]]

    if merged.empty:
        return empty_m, sub

    max_date = merged[COL_CREATE].max()
    sub = _filter_contacts_subscription_age(sub, max_date, min_subscription_age_months)
    merged = merged[merged["contact_id"].isin(sub["contact_id"])]

    merged["periode_mois"] = merged[COL_CREATE].dt.to_period("M")

    periods = sorted(merged["periode_mois"].dropna().unique())
    rows = []
    for p in periods:
        in_month = merged[merged["periode_mois"] == p]
        month_end = p.to_timestamp(how="end")
        elig = sub[sub["date_souscription"] <= month_end]["contact_id"].unique()
        nb_elig = len(elig)
        nb_tickets = len(in_month)
        mean_tc = nb_tickets / nb_elig if nb_elig else 0.0
        rows.append(
            {
                "periode_mois": str(p),
                "nb_contacts_eligibles": nb_elig,
                "nb_tickets_support": nb_tickets,
                "moyenne_tickets_par_contact": round(mean_tc, 4),
            }
        )

    monthly = pd.DataFrame(rows)
    return monthly, sub


def _month_offset_calendar(create: pd.Series, sub: pd.Series) -> pd.Series:
    """Écart en mois calendaires entre deux dates (année/mois)."""
    return (create.dt.year - sub.dt.year) * 12 + (create.dt.month - sub.dt.month)


def _filter_contacts_subscription_age(
    sub: pd.DataFrame, ref_date: pd.Timestamp, min_months: int
) -> pd.DataFrame:
    """Contacts dont date_souscription <= ref_date - min_months (ancienneté minimale)."""
    if sub.empty or min_months <= 0:
        return sub.copy()
    cutoff = pd.Timestamp(ref_date) - pd.DateOffset(months=min_months)
    return sub[sub["date_souscription"] <= cutoff].copy()


def _prepare_support_tenure_sub_merged(
    df: pd.DataFrame,
    max_months: int,
    min_subscription_age_months: int,
    contact_ids_filter: Optional[Set[str]],
) -> Optional[Tuple[pd.DataFrame, pd.DataFrame, pd.Timestamp]]:
    """
    Prépare (sub, merged, max_date) pour les analyses par mois d'ancienneté.
    merged : une ligne par ticket support avec mois_depuis_souscription.
    """
    sub = subscription_date_per_contact(df)
    if sub.empty:
        return None

    sup = support_tickets_df(df)
    sup_ex = explode_contacts(sup).rename(columns={"_contact_id": "contact_id"})
    sup_ex[COL_CREATE] = pd.to_datetime(sup_ex[COL_CREATE], errors="coerce")
    merged = sup_ex.merge(sub, on="contact_id", how="inner")
    merged = merged[merged[COL_CREATE] > merged["date_souscription"]]

    if merged.empty:
        return None

    max_date = merged[COL_CREATE].max()
    sub = _filter_contacts_subscription_age(sub, max_date, min_subscription_age_months)
    if sub.empty:
        return None

    merged = merged[merged["contact_id"].isin(sub["contact_id"])]

    if contact_ids_filter is not None:
        fid = {str(x) for x in contact_ids_filter}
        sub = sub[sub["contact_id"].isin(fid)]
        if sub.empty:
            return None
        merged = merged[merged["contact_id"].isin(sub["contact_id"])]

    sub = sub.copy()
    sub["max_m_observable"] = (
        (max_date.year - sub["date_souscription"].dt.year) * 12
        + (max_date.month - sub["date_souscription"].dt.month)
    )

    merged["mois_depuis_souscription"] = _month_offset_calendar(
        merged[COL_CREATE], merged["date_souscription"]
    )
    merged = merged[merged["mois_depuis_souscription"].between(0, max_months)]
    return sub, merged, max_date


def compute_tenure_buckets_mean_support(
    df: pd.DataFrame,
    max_months: int = 24,
    min_subscription_age_months: int = MIN_SUBSCRIPTION_AGE_MONTHS,
    contact_ids_filter: Optional[Set[str]] = None,
) -> pd.DataFrame:
    """
    Par mois d'ancienneté depuis la souscription (0 = même mois calendaire que la souscription),
    moyenne du tickets support par client (0 si aucun ce mois-là).

    mois_utilisation : 1 = premier mois (mois de la souscription), 2 = mois suivant, etc.

    Si min_subscription_age_months > 0 : uniquement les clients dont la souscription remonte
    à au moins ce nombre de mois avant la dernière date observée sur les tickets support.

    Si contact_ids_filter est fourni : restreint l'analyse à ces contact_id (intersection avec
    la cohorte déjà filtrée par ancienneté).
    """
    empty_cols = [
        "mois_depuis_souscription",
        "mois_utilisation",
        "nb_contacts_eligibles",
        "nb_tickets",
        "moyenne_tickets_par_contact",
    ]
    prep = _prepare_support_tenure_sub_merged(
        df, max_months, min_subscription_age_months, contact_ids_filter
    )
    if prep is None:
        return pd.DataFrame(columns=empty_cols)

    sub, merged, _max_date = prep

    rows = []
    for m in range(0, max_months + 1):
        elig = sub[sub["max_m_observable"] >= m]["contact_id"].unique()
        nb_elig = len(elig)
        sub_m = merged[merged["mois_depuis_souscription"] == m]
        nb_tickets = len(sub_m)
        if nb_elig == 0:
            mean_v = 0.0
        else:
            per_contact = sub_m.groupby("contact_id").size().reindex(elig, fill_value=0)
            mean_v = float(per_contact.mean())
        rows.append(
            {
                "mois_depuis_souscription": m,
                "mois_utilisation": m + 1,
                "nb_contacts_eligibles": int(nb_elig),
                "nb_tickets": int(nb_tickets),
                "moyenne_tickets_par_contact": round(mean_v, 4),
            }
        )

    return pd.DataFrame(rows)


def compute_tenure_buckets_mean_support_by_macro_category(
    df: pd.DataFrame,
    max_months: int = 24,
    min_subscription_age_months: int = MIN_SUBSCRIPTION_AGE_MONTHS,
    contact_ids_filter: Optional[Set[str]] = None,
) -> pd.DataFrame:
    """
    Même logique que ``compute_tenure_buckets_mean_support``, avec une ligne par
    (mois d'ancienneté × groupe macro). Les groupes reprennent le mapping HubSpot → sujet
    « Lecteur » vs le reste (voir ``hubspot_ticket_category_macros``).
    """
    empty_cols = [
        "mois_depuis_souscription",
        "mois_utilisation",
        "groupe_macro",
        "nb_contacts_eligibles",
        "nb_tickets",
        "moyenne_tickets_par_contact",
    ]
    prep = _prepare_support_tenure_sub_merged(
        df, max_months, min_subscription_age_months, contact_ids_filter
    )
    if prep is None:
        return pd.DataFrame(columns=empty_cols)

    sub, merged, _max_date = prep
    merged = merged.copy()
    if COL_CATEGORIE in merged.columns:
        merged["groupe_macro"] = merged[COL_CATEGORIE].map(macro_groupe_comex)
    else:
        merged["groupe_macro"] = MACRO_INFOS_LOGICIELS

    groupes = [MACRO_INFOS_LOGICIELS, MACRO_LECTEURS]
    rows: List[Dict[str, Any]] = []
    for m in range(0, max_months + 1):
        elig = sub[sub["max_m_observable"] >= m]["contact_id"].unique()
        nb_elig = len(elig)
        for g in groupes:
            sub_m = merged[
                (merged["mois_depuis_souscription"] == m)
                & (merged["groupe_macro"] == g)
            ]
            nb_tickets = len(sub_m)
            if nb_elig == 0:
                mean_v = 0.0
            else:
                per_contact = (
                    sub_m.groupby("contact_id").size().reindex(elig, fill_value=0)
                )
                mean_v = float(per_contact.mean())
            rows.append(
                {
                    "mois_depuis_souscription": m,
                    "mois_utilisation": m + 1,
                    "groupe_macro": g,
                    "nb_contacts_eligibles": int(nb_elig),
                    "nb_tickets": int(nb_tickets),
                    "moyenne_tickets_par_contact": round(mean_v, 4),
                }
            )

    return pd.DataFrame(rows)


def compute_totaux_support_par_macro_categorie_cohorte(
    df: pd.DataFrame,
    min_subscription_age_months: int = MIN_SUBSCRIPTION_AGE_MONTHS,
    contact_ids_filter: Optional[Set[str]] = None,
) -> pd.DataFrame:
    """
    Volume total de tickets support (toute la fenêtre après souscription) par groupe macro,
    sur la même cohorte que l'analyse par ancienneté (sans plafond de mois sur les tickets).
    """
    sub = subscription_date_per_contact(df)
    if sub.empty:
        return pd.DataFrame(
            columns=["groupe_macro", "nb_tickets", "part_pct"]
        )

    sup = support_tickets_df(df)
    sup_ex = explode_contacts(sup).rename(columns={"_contact_id": "contact_id"})
    sup_ex[COL_CREATE] = pd.to_datetime(sup_ex[COL_CREATE], errors="coerce")
    merged = sup_ex.merge(sub, on="contact_id", how="inner")
    merged = merged[merged[COL_CREATE] > merged["date_souscription"]]
    if merged.empty:
        return pd.DataFrame(columns=["groupe_macro", "nb_tickets", "part_pct"])

    max_date = merged[COL_CREATE].max()
    sub = _filter_contacts_subscription_age(sub, max_date, min_subscription_age_months)
    if sub.empty:
        return pd.DataFrame(columns=["groupe_macro", "nb_tickets", "part_pct"])

    merged = merged[merged["contact_id"].isin(sub["contact_id"])]
    if contact_ids_filter is not None:
        fid = {str(x) for x in contact_ids_filter}
        sub = sub[sub["contact_id"].isin(fid)]
        if sub.empty:
            return pd.DataFrame(columns=["groupe_macro", "nb_tickets", "part_pct"])
        merged = merged[merged["contact_id"].isin(sub["contact_id"])]

    if COL_CATEGORIE in merged.columns:
        merged = merged.copy()
        merged["groupe_macro"] = merged[COL_CATEGORIE].map(macro_groupe_comex)
    else:
        merged = merged.copy()
        merged["groupe_macro"] = MACRO_INFOS_LOGICIELS

    counts = merged.groupby("groupe_macro").size().reset_index(name="nb_tickets")
    total = int(counts["nb_tickets"].sum())
    if total > 0:
        counts["part_pct"] = (100.0 * counts["nb_tickets"] / total).round(2)
    else:
        counts["part_pct"] = 0.0
    return counts


def methodologie_cohorte_anciennete_support_text(
    ref_date: pd.Timestamp,
    nb_clients_cohorte: int,
    min_subscription_age_months: int,
    fichier_export: str,
) -> str:
    """Texte méthodologie COMEX (même contenu que l'ancien fichier .txt)."""
    from data_processing.hubspot_ticket_category_macros import (
        categories_hubspot_classees_lecteur,
    )

    lect_list = ", ".join(categories_hubspot_classees_lecteur())
    lines = [
        "Méthodologie — Volume moyen de tickets support par mois depuis la souscription Stellair",
        "=" * 72,
        "",
        "1. Définition de la souscription (proxy)",
        "   Date = date de fermeture du ticket pipeline ADV dont le sujet est exactement",
        "   « Suivi de ma commande ». Si plusieurs tickets, on retient la fermeture la plus ancienne",
        "   (première commande traitée) par contact HubSpot.",
        "",
        "2. Tickets support analysés",
        "   Pipelines SSI, SSIA, SPSA — uniquement les tickets créés STRICTEMENT APRÈS la date de",
        "   souscription ci-dessus.",
        "",
        "3. Date de fin d'observation (référence temporelle)",
        f"   Dernière date de CRÉATION d'un ticket support dans l'export : {ref_date.date()}.",
        "",
        "4. Cohorte « au moins N mois de recul » (par défaut N = 12)",
        f"   On ne garde que les contacts dont la date de souscription est antérieure d'AU MOINS",
        f"   {min_subscription_age_months} mois à cette date de fin d'observation.",
        f"   Effectif de cette cohorte dans l'export : {nb_clients_cohorte} contacts.",
        "",
        "5. Ce que ce n'est PAS",
        "   L'effectif N ci-dessus ne correspond pas à « tous les clients ayant souscrit le même mois ».",
        "   Les dates de souscription sont réparties sur l'historique disponible dans HubSpot. Le filtre « 12 mois »",
        "   garantit seulement que chaque client a au moins 12 mois d'ancienneté au moment de la fin",
        "   des données, pour pouvoir comparer les mois 1 à 12 sans biais de clients trop récents.",
        "",
        "6. Axe « mois depuis souscription » (alignement individuel)",
        "   Pour chaque client, chaque ticket est rangé dans un mois d'ancienneté 0, 1, 2… en comptant",
        "   les mois CALENDAIRES entre le mois de souscription et le mois de création du ticket.",
        "   Le mois 0 = même mois calendaire que la souscription ; le mois 1 = mois suivant, etc.",
        "",
        "7. Dénominateur par ligne (nb_contacts_eligibles)",
        "   Pour un mois d'ancienneté m, on compte les clients pour lesquels au moins m mois se sont",
        "   écoulés entre le mois de souscription et la fin des données (ils ont pu « atteindre » ce",
        "   rang d'ancienneté avant la date de fin d'observation). Ce nombre peut être constant",
        "   sur une plage de mois si tous les clients de la cohorte ont une observation assez longue.",
        "",
        "8. Moyenne (moyenne_tickets_par_contact)",
        "   Pour chaque mois m : moyenne, sur les contacts éligibles, du nombre de tickets support",
        "   créés dans CE mois d'ancienneté-là (les clients sans ticket ce mois-là comptent pour 0).",
        "",
        "9. Regroupement « Catégorie » HubSpot (2 familles pour le COMEX)",
        "   — Incidents / problèmes lecteurs : catégories HubSpot mappées vers le sujet agrégé",
        "     « Lecteur » (même logique que le dashboard), ex. :",
        f"     {lect_list}",
        "   — Demandes d'information, Stellair, logiciel, facturation, autres : toutes les autres",
        "     catégories reconnues du référentiel, plus catégories absentes ou non mappées (rangées ici).",
        "",
        f"Fichier source : {fichier_export}",
        "",
    ]
    return "\n".join(lines)


def write_methodologie_cohorte_anciennete_txt(
    path: str | Path,
    ref_date: pd.Timestamp,
    nb_clients_cohorte: int,
    min_subscription_age_months: int,
    fichier_export: str,
) -> None:
    """Écrit le fichier texte (alias de ``methodologie_cohorte_anciennete_support_text``)."""
    txt = methodologie_cohorte_anciennete_support_text(
        ref_date,
        nb_clients_cohorte,
        min_subscription_age_months,
        fichier_export,
    )
    Path(path).write_text(txt, encoding="utf-8")


def export_support_stellair_workbook(
    df: pd.DataFrame,
    out_xlsx: str | Path,
    fichier_export_name: str,
    min_subscription_age_months: int = MIN_SUBSCRIPTION_AGE_MONTHS,
) -> Dict[str, pd.DataFrame]:
    """
    Produit **un seul fichier Excel** (.xlsx) avec une feuille par tableau + la méthodologie.

    Feuilles : Méthodologie, Par_anciennete_mois, Par_anciennete_macro, Totaux_macro,
    Moyen_par_mois, Contacts_eligibles_12m, Contacts_ADV_tous, Resume_fenetres.

    Retourne un dict des DataFrames calculés (pour tests ou usage programmatique).
    """
    out_xlsx = Path(out_xlsx)
    out_xlsx.parent.mkdir(parents=True, exist_ok=True)

    monthly, contacts_sub = compute_monthly_mean_support_after_subscription(
        df, min_subscription_age_months=min_subscription_age_months
    )
    tenure = compute_tenure_buckets_mean_support(
        df, min_subscription_age_months=min_subscription_age_months
    )
    tenure_macro = compute_tenure_buckets_mean_support_by_macro_category(
        df, min_subscription_age_months=min_subscription_age_months
    )
    totaux_macro = compute_totaux_support_par_macro_categorie_cohorte(
        df, min_subscription_age_months=min_subscription_age_months
    )
    resume = compute_tenure_window_summary(tenure)
    contacts_all = subscription_date_per_contact(df)

    sup_ref = support_tickets_df(df)
    ref_date = pd.Timestamp(
        pd.to_datetime(sup_ref[COL_CREATE], errors="coerce").max()
    )
    nb_cohorte = len(contacts_sub)

    if not pd.isna(ref_date):
        meth_txt = methodologie_cohorte_anciennete_support_text(
            ref_date,
            nb_cohorte,
            min_subscription_age_months,
            fichier_export_name,
        )
    else:
        meth_txt = "Date de référence support indisponible — méthodologie non générée."

    df_meth = pd.DataFrame({"ligne": meth_txt.splitlines()})

    with pd.ExcelWriter(out_xlsx, engine="openpyxl") as writer:
        df_meth.to_excel(writer, sheet_name="Méthodologie", index=False)
        tenure.to_excel(writer, sheet_name="Par_anciennete_mois", index=False)
        tenure_macro.to_excel(writer, sheet_name="Par_anciennete_macro", index=False)
        totaux_macro.to_excel(writer, sheet_name="Totaux_macro", index=False)
        monthly.to_excel(writer, sheet_name="Moyen_par_mois", index=False)
        contacts_sub.to_excel(writer, sheet_name="Contacts_eligibles_12m", index=False)
        contacts_all.to_excel(writer, sheet_name="Contacts_ADV_tous", index=False)
        resume.to_excel(writer, sheet_name="Resume_fenetres", index=False)

    return {
        "monthly": monthly,
        "tenure": tenure,
        "tenure_macro": tenure_macro,
        "totaux_macro": totaux_macro,
        "resume": resume,
        "contacts_sub": contacts_sub,
        "contacts_all": contacts_all,
    }


def compute_tenure_window_summary(tenure: pd.DataFrame) -> pd.DataFrame:
    """
    Compare les moyennes par fenêtre : mois 1–3 vs 4–12 vs 13–24 (indices 0–2, 3–11, 12–23).
    mois_utilisation 1 = premier mois Stellair (même mois calendaire que la souscription).
    """
    if tenure.empty:
        return pd.DataFrame(
            columns=[
                "nb_clients_anciennete_min_12m",
                "nb_lignes_tenure",
                "moyenne_tickets_mois_utilisation_1",
                "moyenne_tickets_mois_utilisation_2",
                "moyenne_tickets_mois_utilisation_3",
                "moyenne_des_moyennes_mois_1_a_3",
                "moyenne_des_moyennes_mois_4_a_12",
                "moyenne_des_moyennes_mois_13_a_24",
                "ratio_moyenne_mois_1_a_3_sur_mois_4_a_12",
            ]
        )

    def _mean_range(lo: int, hi: int) -> float:
        part = tenure[tenure["mois_depuis_souscription"].between(lo, hi)]
        if part.empty:
            return float("nan")
        return float(part["moyenne_tickets_par_contact"].mean())

    m1 = tenure.loc[tenure["mois_depuis_souscription"] == 0, "moyenne_tickets_par_contact"]
    m2 = tenure.loc[tenure["mois_depuis_souscription"] == 1, "moyenne_tickets_par_contact"]
    m3 = tenure.loc[tenure["mois_depuis_souscription"] == 2, "moyenne_tickets_par_contact"]

    avg_1_3 = _mean_range(0, 2)
    avg_4_12 = _mean_range(3, 11)
    avg_13_24 = _mean_range(12, 23)
    ratio = float("nan")
    if not math.isnan(avg_4_12) and avg_4_12 != 0 and not math.isnan(avg_1_3):
        ratio = avg_1_3 / avg_4_12

    nb_clients = int(tenure.iloc[0]["nb_contacts_eligibles"]) if len(tenure) else 0

    row: Dict[str, Any] = {
        "nb_clients_anciennete_min_12m": nb_clients,
        "nb_lignes_tenure": len(tenure),
        "moyenne_tickets_mois_utilisation_1": float(m1.iloc[0]) if len(m1) else float("nan"),
        "moyenne_tickets_mois_utilisation_2": float(m2.iloc[0]) if len(m2) else float("nan"),
        "moyenne_tickets_mois_utilisation_3": float(m3.iloc[0]) if len(m3) else float("nan"),
        "moyenne_des_moyennes_mois_1_a_3": round(avg_1_3, 4) if not math.isnan(avg_1_3) else float("nan"),
        "moyenne_des_moyennes_mois_4_a_12": round(avg_4_12, 4) if not math.isnan(avg_4_12) else float("nan"),
        "moyenne_des_moyennes_mois_13_a_24": round(avg_13_24, 4) if not math.isnan(avg_13_24) else float("nan"),
        "ratio_moyenne_mois_1_a_3_sur_mois_4_a_12": round(ratio, 4) if not math.isnan(ratio) else float("nan"),
    }
    return pd.DataFrame([row])


def run_analysis(
    ticket_excel_path: str | Path,
    output_dir: str | Path | None = None,
    min_subscription_age_months: int = MIN_SUBSCRIPTION_AGE_MONTHS,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Lit l'export HubSpot, écrit les CSV et retourne
    (monthly, tenure, contacts_filtres, contacts_tous, resume_fenetres).

    Fichiers supplémentaires produits (même répertoire, même préfixe que l'export) :
    - *_support_par_anciennete_mois_par_macro_categorie.csv — même logique que l'analyse par
      ancienneté, ventilée par 2 macro-familles (lecteurs vs infos/logiciel, voir module
      hubspot_ticket_category_macros) ;
    - *_support_totaux_par_macro_categorie_cohorte.csv — volumes totaux sur la cohorte ;
    - *_methodologie_cohorte_anciennete_support.txt — texte de méthodologie pour présentation.
    """
    path = Path(ticket_excel_path)
    if not path.is_file():
        raise FileNotFoundError(path)

    df = pd.read_excel(path)
    contacts_all = subscription_date_per_contact(df)
    monthly, contacts_sub = compute_monthly_mean_support_after_subscription(
        df, min_subscription_age_months=min_subscription_age_months
    )
    tenure = compute_tenure_buckets_mean_support(
        df, min_subscription_age_months=min_subscription_age_months
    )
    tenure_macro = compute_tenure_buckets_mean_support_by_macro_category(
        df, min_subscription_age_months=min_subscription_age_months
    )
    totaux_macro = compute_totaux_support_par_macro_categorie_cohorte(
        df, min_subscription_age_months=min_subscription_age_months
    )
    resume = compute_tenure_window_summary(tenure)

    sup_ref = support_tickets_df(df)
    ref_date = pd.Timestamp(
        pd.to_datetime(sup_ref[COL_CREATE], errors="coerce").max()
    )
    nb_cohorte = len(contacts_sub)

    out_dir = Path(output_dir) if output_dir else path.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    stem = path.stem
    monthly_path = out_dir / f"{stem}_support_moyen_par_mois.csv"
    tenure_path = out_dir / f"{stem}_support_par_anciennete_mois.csv"
    tenure_macro_path = out_dir / f"{stem}_support_par_anciennete_mois_par_macro_categorie.csv"
    totaux_macro_path = out_dir / f"{stem}_support_totaux_par_macro_categorie_cohorte.csv"
    methodo_path = out_dir / f"{stem}_methodologie_cohorte_anciennete_support.txt"
    sub_path = out_dir / f"{stem}_contacts_eligibles_12m_adv.csv"
    all_path = out_dir / f"{stem}_contacts_date_souscription_adv_tous.csv"
    resume_path = out_dir / f"{stem}_resume_comparaison_mois.csv"

    monthly.to_csv(monthly_path, index=False, encoding="utf-8-sig")
    tenure.to_csv(tenure_path, index=False, encoding="utf-8-sig")
    tenure_macro.to_csv(tenure_macro_path, index=False, encoding="utf-8-sig")
    totaux_macro.to_csv(totaux_macro_path, index=False, encoding="utf-8-sig")
    contacts_sub.to_csv(sub_path, index=False, encoding="utf-8-sig")
    contacts_all.to_csv(all_path, index=False, encoding="utf-8-sig")
    resume.to_csv(resume_path, index=False, encoding="utf-8-sig")
    if not pd.isna(ref_date):
        write_methodologie_cohorte_anciennete_txt(
            methodo_path,
            ref_date=ref_date,
            nb_clients_cohorte=nb_cohorte,
            min_subscription_age_months=min_subscription_age_months,
            fichier_export=path.name,
        )

    print(f"Écrit : {monthly_path}")
    print(f"Écrit : {tenure_path}")
    print(f"Écrit : {tenure_macro_path}")
    print(f"Écrit : {totaux_macro_path}")
    if not pd.isna(ref_date):
        print(f"Écrit : {methodo_path}")
    print(f"Écrit : {sub_path}")
    print(f"Écrit : {all_path}")
    print(f"Écrit : {resume_path}")
    if not resume.empty and not math.isnan(resume["moyenne_tickets_mois_utilisation_1"].iloc[0]):
        m1 = resume["moyenne_tickets_mois_utilisation_1"].iloc[0]
        print(
            f"→ Moyenne tickets au 1er mois d'utilisation (mois calendaire de la souscription) : {m1:.4f} ticket(s) / client"
        )
    return monthly, tenure, contacts_sub, contacts_all, resume


def run_formation_cohort_analysis(
    ticket_excel_path: str | Path,
    output_dir: str | Path | None = None,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Cohorte : souscription à partir de juin 2025 + au moins un ticket « Formation Stellair ».
    Exporte la moyenne de tickets support par client pour les 6 premiers mois d'utilisation.
    """
    path = Path(ticket_excel_path)
    if not path.is_file():
        raise FileNotFoundError(path)

    df = pd.read_excel(path)
    tenure, contacts = compute_tenure_formation_cohort_first_months(df)

    out_dir = Path(output_dir) if output_dir else path.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    stem = path.stem
    tenure_path = out_dir / f"{stem}_formation_juin2025_6premiers_mois_support.csv"
    contacts_path = out_dir / f"{stem}_formation_juin2025_contacts.csv"
    resume_path = out_dir / f"{stem}_formation_juin2025_resume.csv"

    tenure.to_csv(tenure_path, index=False, encoding="utf-8-sig")
    contacts.to_csv(contacts_path, index=False, encoding="utf-8-sig")

    avg_1_6 = (
        float(tenure["moyenne_tickets_par_contact"].mean())
        if len(tenure)
        else float("nan")
    )
    resume = pd.DataFrame(
        [
            {
                "filtre_souscription_depuis": str(SUBSCRIPTION_FROM_DATE.date()),
                "pipeline_formation": FORMATION_PIPELINE,
                "nb_clients_cohorte": len(contacts),
                "moyenne_des_moyennes_tickets_support_mois_1_a_6": round(avg_1_6, 4)
                if avg_1_6 == avg_1_6
                else float("nan"),
            }
        ]
    )
    resume.to_csv(resume_path, index=False, encoding="utf-8-sig")

    print(f"Écrit : {tenure_path}")
    print(f"Écrit : {contacts_path}")
    print(f"Écrit : {resume_path}")
    if len(contacts):
        print(
            f"→ Cohorte formation (souscription ≥ juin 2025 + ticket {FORMATION_PIPELINE}) : "
            f"{len(contacts)} client(s), moyenne arithmétique des moyennes mensuelles (mois 1–6) : "
            f"{resume['moyenne_des_moyennes_tickets_support_mois_1_a_6'].iloc[0]}"
        )
    return tenure, contacts, resume


def run_formation_buyers_vs_rest_cohort_analysis(
    ticket_excel_path: str | Path,
    formation_transactions_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    min_subscription_age_months: int = MIN_SUBSCRIPTION_AGE_MONTHS,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Compare la demande support (cohorte 12 mois) entre :
    - clients avec au moins une transaction formation « Fermé gagné » (Associated Contact IDs) ;
    - les autres clients de la même cohorte.

    Exporte les tables d'ancienneté par groupe, un CSV de synthèse et la liste des contacts
    avec indicateur booléen d'achat formation.
    """
    path = Path(ticket_excel_path)
    if not path.is_file():
        raise FileNotFoundError(path)

    df = pd.read_excel(path)
    _, contacts_sub = compute_monthly_mean_support_after_subscription(
        df, min_subscription_age_months=min_subscription_age_months
    )
    if contacts_sub.empty:
        raise ValueError("Cohorte vide (aucun contact éligible 12 mois).")

    cohort_ids = set(contacts_sub["contact_id"].astype(str))

    if formation_transactions_path is None:
        fx = find_latest_formation_transactions_xlsx()
        if fx is None:
            raise FileNotFoundError(
                f"Aucun export .xlsx trouvé dans {FORMATION_TRANSACTIONS_DIR}."
            )
    else:
        fx = Path(formation_transactions_path)
        if not fx.is_file():
            raise FileNotFoundError(fx)

    buyer_ids = load_formation_transaction_contact_ids(fx)
    avec_ids = cohort_ids & buyer_ids
    sans_ids = cohort_ids - buyer_ids

    tenure_avec = compute_tenure_buckets_mean_support(
        df,
        min_subscription_age_months=min_subscription_age_months,
        contact_ids_filter=avec_ids,
    )
    tenure_sans = compute_tenure_buckets_mean_support(
        df,
        min_subscription_age_months=min_subscription_age_months,
        contact_ids_filter=sans_ids,
    )

    resume_avec = compute_tenure_window_summary(tenure_avec)
    resume_sans = compute_tenure_window_summary(tenure_sans)

    sub_avec = contacts_sub[contacts_sub["contact_id"].isin(avec_ids)].copy()
    sub_sans = contacts_sub[contacts_sub["contact_id"].isin(sans_ids)].copy()

    moy_avec = mean_tickets_support_par_client_apres_sub(df, sub_avec)
    moy_sans = mean_tickets_support_par_client_apres_sub(df, sub_sans)
    diff = (
        (moy_sans - moy_avec)
        if not math.isnan(moy_avec) and not math.isnan(moy_sans)
        else float("nan")
    )

    comp = pd.DataFrame(
        [
            {
                "fichier_transactions_formation": fx.name,
                "nb_clients_cohorte_12m": len(cohort_ids),
                "nb_avec_formation_filtre_gagne": len(avec_ids),
                "nb_sans_formation": len(sans_ids),
                "moyenne_tickets_support_par_client_apres_sub_avec_formation": round(moy_avec, 4)
                if moy_avec == moy_avec
                else float("nan"),
                "moyenne_tickets_support_par_client_apres_sub_sans_formation": round(moy_sans, 4)
                if moy_sans == moy_sans
                else float("nan"),
                "ecart_moyenne_sans_moins_avec": round(diff, 4) if diff == diff else float("nan"),
                "note": "Si ecart > 0, la moyenne est plus élevée chez les sans formation (plus demandeurs).",
            }
        ]
    )

    out_dir = Path(output_dir) if output_dir else path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = path.stem

    path_avec = out_dir / f"{stem}_cohorte12m_tenure_avec_formation_transactions.csv"
    path_sans = out_dir / f"{stem}_cohorte12m_tenure_sans_formation.csv"
    path_comp = out_dir / f"{stem}_cohorte12m_comparaison_formation_acheteurs.csv"
    path_flag = out_dir / f"{stem}_cohorte12m_contacts_flag_formation.csv"
    path_resume_avec = out_dir / f"{stem}_cohorte12m_resume_fenetres_avec_formation.csv"
    path_resume_sans = out_dir / f"{stem}_cohorte12m_resume_fenetres_sans_formation.csv"

    tenure_avec.to_csv(path_avec, index=False, encoding="utf-8-sig")
    tenure_sans.to_csv(path_sans, index=False, encoding="utf-8-sig")
    comp.to_csv(path_comp, index=False, encoding="utf-8-sig")
    resume_avec.to_csv(path_resume_avec, index=False, encoding="utf-8-sig")
    resume_sans.to_csv(path_resume_sans, index=False, encoding="utf-8-sig")

    flag = contacts_sub.copy()
    flag["formation_achete_transaction_gagne"] = (
        flag["contact_id"].astype(str).isin(buyer_ids)
    )
    flag.to_csv(path_flag, index=False, encoding="utf-8-sig")

    print(f"Écrit : {path_avec}")
    print(f"Écrit : {path_sans}")
    print(f"Écrit : {path_comp}")
    print(f"Écrit : {path_flag}")
    print(f"Écrit : {path_resume_avec}")
    print(f"Écrit : {path_resume_sans}")
    print(
        f"→ Cohorte 12m : {len(cohort_ids)} clients | "
        f"avec formation (transactions gagnées) : {len(avec_ids)} | "
        f"sans : {len(sans_ids)}"
    )
    if moy_avec == moy_avec and moy_sans == moy_sans:
        print(
            f"→ Moyenne tickets support / client après souscription : "
            f"avec formation {moy_avec:.4f} | sans formation {moy_sans:.4f} | "
            f"écart (sans−avec) {diff:.4f}"
        )

    return tenure_avec, tenure_sans, comp, flag


def run_support_demands_after_formation_eligible_6mois(
    ticket_excel_path: str | Path,
    formation_transactions_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    min_months_since_formation: int = MIN_MONTHS_SINCE_FORMATION_FOR_ANALYSIS,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Clients ayant une formation « Fermé gagné » dont la **première** date de fermeture est
    antérieure d'**au moins** ``min_months_since_formation`` mois à la dernière date de
    ticket support (fin de fenêtre d'observation).

    Pour chaque contact éligible : compte les tickets support (SSI, SSIA, SPSA) avec
    date de création **strictement après** la date de formation et **jusqu'à** la fin des données.

    Exporte un détail par contact et une ligne de synthèse.
    """
    path = Path(ticket_excel_path)
    if not path.is_file():
        raise FileNotFoundError(path)

    df = pd.read_excel(path)
    sup = support_tickets_df(df)
    if sup.empty:
        raise ValueError("Aucun ticket support dans l'export tickets.")
    ref_date = pd.Timestamp(sup[COL_CREATE].max())
    if pd.isna(ref_date):
        raise ValueError("Date de création support invalide.")

    if formation_transactions_path is None:
        fx = find_latest_formation_transactions_xlsx()
        if fx is None:
            raise FileNotFoundError(
                f"Aucun export .xlsx trouvé dans {FORMATION_TRANSACTIONS_DIR}."
            )
    else:
        fx = Path(formation_transactions_path)
        if not fx.is_file():
            raise FileNotFoundError(fx)

    form_dates = load_formation_contact_first_win_close_date(fx)
    if form_dates.empty:
        raise ValueError("Aucune formation gagnée exploitable (dates manquantes).")

    cutoff = ref_date - pd.DateOffset(months=min_months_since_formation)
    eligible = form_dates[form_dates["date_formation"] <= cutoff].copy()

    if eligible.empty:
        detail = pd.DataFrame(
            columns=[
                "contact_id",
                "date_formation",
                "nb_tickets_support_apres_formation",
                "nb_mois_observation",
                "tickets_support_par_mois_calendaire",
            ]
        )
        summary = pd.DataFrame(
            [
                {
                    "date_fin_donnees_tickets": str(ref_date),
                    "date_limite_formation_au_plus_tard": str(cutoff.date()),
                    "min_mois_depuis_formation": min_months_since_formation,
                    "fichier_transactions": fx.name,
                    "nb_clients_eligibles": 0,
                    "nb_tickets_support_total_apres_formation": 0,
                    "moyenne_tickets_par_client": float("nan"),
                    "mediane_tickets_par_client": float("nan"),
                    "moyenne_tickets_par_mois_calendaire": float("nan"),
                }
            ]
        )
    else:
        sup_ex = explode_contacts(sup).rename(columns={"_contact_id": "contact_id"})
        sup_ex[COL_CREATE] = pd.to_datetime(sup_ex[COL_CREATE], errors="coerce")
        merged = sup_ex.merge(eligible, on="contact_id", how="inner")
        merged = merged[
            (merged[COL_CREATE] > merged["date_formation"])
            & (merged[COL_CREATE] <= ref_date)
        ]
        counts = merged.groupby("contact_id").size().rename(
            "nb_tickets_support_apres_formation"
        )
        detail = eligible.merge(
            counts.reset_index(), on="contact_id", how="left"
        )
        detail["nb_tickets_support_apres_formation"] = (
            detail["nb_tickets_support_apres_formation"].fillna(0).astype(int)
        )
        detail["nb_mois_observation"] = (
            (ref_date.year - detail["date_formation"].dt.year) * 12
            + (ref_date.month - detail["date_formation"].dt.month)
        )
        detail["nb_mois_observation"] = detail["nb_mois_observation"].clip(lower=1)
        detail["tickets_support_par_mois_calendaire"] = (
            detail["nb_tickets_support_apres_formation"] / detail["nb_mois_observation"]
        ).round(4)

        summary = pd.DataFrame(
            [
                {
                    "date_fin_donnees_tickets": str(ref_date),
                    "date_limite_formation_au_plus_tard": str(cutoff.date()),
                    "min_mois_depuis_formation": min_months_since_formation,
                    "fichier_transactions": fx.name,
                    "nb_clients_eligibles": len(detail),
                    "nb_tickets_support_total_apres_formation": int(
                        detail["nb_tickets_support_apres_formation"].sum()
                    ),
                    "moyenne_tickets_par_client": round(
                        float(detail["nb_tickets_support_apres_formation"].mean()), 4
                    ),
                    "mediane_tickets_par_client": float(
                        detail["nb_tickets_support_apres_formation"].median()
                    ),
                    "moyenne_tickets_par_mois_calendaire": round(
                        float(detail["tickets_support_par_mois_calendaire"].mean()), 4
                    ),
                }
            ]
        )

    out_dir = Path(output_dir) if output_dir else path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = path.stem
    path_detail = (
        out_dir
        / f"{stem}_support_apres_formation_6mois_plus_detail_contacts.csv"
    )
    path_summary = (
        out_dir
        / f"{stem}_support_apres_formation_6mois_plus_resume.csv"
    )
    detail.to_csv(path_detail, index=False, encoding="utf-8-sig")
    summary.to_csv(path_summary, index=False, encoding="utf-8-sig")
    print(f"Écrit : {path_detail}")
    print(f"Écrit : {path_summary}")
    print(
        f"→ Formation ≥ {min_months_since_formation} mois avant {ref_date.date()} : "
        f"{len(detail)} client(s) éligibles | "
        f"{int(summary['nb_tickets_support_total_apres_formation'].iloc[0])} ticket(s) support après formation (total)"
    )
    return detail, summary


def run_tenure_table_cohorte12m_formation_recue_6mois_plus(
    ticket_excel_path: str | Path,
    formation_transactions_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    min_months_since_formation: int = MIN_MONTHS_SINCE_FORMATION_FOR_ANALYSIS,
    max_months: int = 12,
    min_subscription_age_months: int = MIN_SUBSCRIPTION_AGE_MONTHS,
) -> pd.DataFrame:
    """
    Tableau par ancienneté (même colonnes que ``support_par_anciennete_mois``) pour le sous-ensemble :
    cohorte 12 mois (souscription ADV assez ancienne) ∩ contact avec formation « gagnée » dont la
    première fermeture est au plus tard ``ref_date - min_months_since_formation`` (formation reçue
    il y a au moins N mois). Les mois d'ancienneté restent relatifs à la souscription Stellair.
    """
    path = Path(ticket_excel_path)
    if not path.is_file():
        raise FileNotFoundError(path)

    df = pd.read_excel(path)
    sup = support_tickets_df(df)
    if sup.empty:
        raise ValueError("Aucun ticket support dans l'export tickets.")
    ref_date = pd.Timestamp(pd.to_datetime(sup[COL_CREATE], errors="coerce").max())
    if pd.isna(ref_date):
        raise ValueError("Date de création support invalide.")

    if formation_transactions_path is None:
        fx = find_latest_formation_transactions_xlsx()
        if fx is None:
            raise FileNotFoundError(
                f"Aucun export .xlsx trouvé dans {FORMATION_TRANSACTIONS_DIR}."
            )
    else:
        fx = Path(formation_transactions_path)
        if not fx.is_file():
            raise FileNotFoundError(fx)

    form_dates = load_formation_contact_first_win_close_date(fx)
    if form_dates.empty:
        raise ValueError("Aucune formation gagnée exploitable (dates manquantes).")

    cutoff = ref_date - pd.DateOffset(months=min_months_since_formation)
    eligible_formation = set(
        form_dates[form_dates["date_formation"] <= cutoff]["contact_id"].astype(str)
    )

    _, contacts_sub = compute_monthly_mean_support_after_subscription(
        df, min_subscription_age_months=min_subscription_age_months
    )
    if contacts_sub.empty:
        raise ValueError("Cohorte vide (aucun contact éligible 12 mois).")

    cohort_ids = set(contacts_sub["contact_id"].astype(str))
    intersection_ids = cohort_ids & eligible_formation

    tenure = compute_tenure_buckets_mean_support(
        df,
        max_months=max_months,
        min_subscription_age_months=min_subscription_age_months,
        contact_ids_filter=intersection_ids,
    )

    out_dir = Path(output_dir) if output_dir else path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = path.stem
    out_path = (
        out_dir
        / f"{stem}_support_par_anciennete_mois_cohorte12m_et_formation_6mois_plus.csv"
    )
    tenure.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"Écrit : {out_path}")
    n_inter = len(intersection_ids)
    print(
        f"→ Tableau ancienneté (cohorte 12m ∩ formation ≥ {min_months_since_formation} mois) : "
        f"{n_inter} contact(s) | fichier formation : {fx.name}"
    )
    return tenure


if __name__ == "__main__":
    import sys

    root = Path(__file__).resolve().parents[1]
    default_xlsx = root / "data/Affid/Hubspot/ticket"
    if len(sys.argv) > 1:
        xlsx = Path(sys.argv[1])
    else:
        cands = sorted(
            default_xlsx.glob("*.xlsx"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not cands:
            raise SystemExit(f"Aucun .xlsx dans {default_xlsx}")
        xlsx = cands[0]
        print(f"Fichier utilisé : {xlsx}")

    out = root / "data/Affid/analyse_appels_tickets"
    run_analysis(xlsx, output_dir=out)
    print()
    run_formation_cohort_analysis(xlsx, output_dir=out)
    print()
    try:
        run_formation_buyers_vs_rest_cohort_analysis(xlsx, output_dir=out)
    except FileNotFoundError as e:
        print(f"⚠️ Analyse formation acheteurs vs reste : {e}")
    print()
    try:
        run_support_demands_after_formation_eligible_6mois(xlsx, output_dir=out)
    except (FileNotFoundError, ValueError) as e:
        print(f"⚠️ Analyse support après formation (6 mois+) : {e}")
    print()
    try:
        run_tenure_table_cohorte12m_formation_recue_6mois_plus(xlsx, output_dir=out)
    except (FileNotFoundError, ValueError) as e:
        print(f"⚠️ Tableau ancienneté cohorte12m ∩ formation 6 mois+ : {e}")
