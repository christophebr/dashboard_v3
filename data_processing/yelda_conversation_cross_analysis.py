"""
Analyse croisée Yelda × HubSpot × Aircall, par conversation.

Fenêtre temporelle [T, T + 24h] après la date/heure de la conversation.

- Côté dashboard : n'entrent dans l'analyse que les **conversations évaluées** (comme
  ``filter_yelda_evaluated`` / Évaluation LLM). L'historique pour l'attribution des tickets
  aux sessions est lui aussi limité aux conversations évaluées.

- Attribution des tickets : pour un même contact, un ticket est rattaché à la **dernière**
  conversation **retenue dans cet historique** commencée **avant ou à** l'heure de création
  du ticket. Les IDs HubSpot « Associated Conversation » sont exposés à titre informatif
  (format numérique, distinct de l'ID conversation Yelda).

- Agrégats : synthèse période + segment par URL d'origine.

- Échantillon de cas limites : parcours sans creation_ticket_hubspot mais tickets dans la fenêtre.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd

from data_processing.yelda_processing import (
    COL_DATE,
    COL_ID_CONV,
    COL_PARCOURS,
    has_ticket_created,
    filter_yelda_stellair,
)

COL_HUBSPOT_ID_SLOT = "Persistant slot - hubspot_id_slot"
COL_YELDA_PHONE = "Numéro de téléphone"
COL_URL = "URL d'origine"
COL_EVAL_LLM = "Évaluation LLM"
COL_DUREE = "Durée en seconde"

# Export contacts HubSpot (FR)
CONTACT_COL_ID = "ID de fiche d'informations"
CONTACT_COL_PHONE_PRIMARY = "Numéro de téléphone"
CONTACT_COL_PHONE_2 = "Numéro de téléphone 2"
CONTACT_COL_PHONE_3 = "Numéro de téléphone 3"

# Tickets
TICKET_COL_CONTACT_IDS = "Associated Contact IDs"
TICKET_COL_CREATED = "Date de création"
TICKET_COL_SOURCE = "Source"
TICKET_COL_PIPELINE = "Pipeline"
TICKET_COL_ID = "Ticket ID"
TICKET_COL_CONV_IDS = "Associated Conversation IDs"

DEFAULT_WINDOW_HOURS = 24
PIPELINE_CHATBOT_YELDA = "Chatbot Yelda"
SOURCE_CHAT = "Chat"


def _normalize_hubspot_id(val: Any) -> Optional[str]:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return None
    s = str(val).strip()
    if not s or s.lower() == "nan":
        return None
    if s.endswith(".0") and s[:-2].isdigit():
        s = s[:-2]
    return s if s.isdigit() else None


def _parse_contact_ids_cell(val: Any) -> List[str]:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return []
    s = str(val).strip()
    if not s or s.lower() == "nan":
        return []
    parts = re.split(r"[;,]", s)
    out = []
    for p in parts:
        n = _normalize_hubspot_id(p.strip())
        if n:
            out.append(n)
    return out


def _parse_hubspot_conversation_ids_cell(val: Any) -> List[str]:
    """Normalise les IDs conversation HubSpot (numériques) pour affichage / futur rapprochement."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return []
    s = str(val).strip()
    if not s or s.lower() == "nan":
        return []
    parts = re.split(r"[;,]", s)
    out: List[str] = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        try:
            n = int(float(p.replace(",", "").replace(" ", "")))
            out.append(str(n))
        except (ValueError, TypeError):
            if p:
                out.append(p)
    return out


def phone_match_key(val: Any) -> Optional[str]:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return None
    digits = "".join(c for c in str(val) if c.isdigit())
    if len(digits) < 9:
        return None
    return digits[-9:]


def _collect_phone_keys_from_row(row: pd.Series, cols: List[str]) -> Set[str]:
    keys: Set[str] = set()
    for c in cols:
        if c in row.index:
            k = phone_match_key(row.get(c))
            if k:
                keys.add(k)
    return keys


def _contact_id_column(df: pd.DataFrame) -> Optional[str]:
    for c in (CONTACT_COL_ID, "Record ID", "Contact ID"):
        if c in df.columns:
            return c
    return None


def load_hubspot_contacts_excel(contacts_dir: str | Path) -> pd.DataFrame:
    contacts_dir = Path(contacts_dir)
    if not contacts_dir.is_dir():
        return pd.DataFrame()
    files = [
        contacts_dir / f
        for f in os.listdir(contacts_dir)
        if f.lower().endswith((".xlsx", ".xls"))
        and not f.startswith("~$")
        and not f.startswith(".")
    ]
    if not files:
        return pd.DataFrame()
    latest = max(files, key=lambda p: p.stat().st_mtime)
    return pd.read_excel(latest)


def build_contact_id_to_phone_keys(df_contacts: pd.DataFrame) -> Dict[str, Set[str]]:
    phone_cols = [
        c
        for c in (CONTACT_COL_PHONE_PRIMARY, CONTACT_COL_PHONE_2, CONTACT_COL_PHONE_3)
        if c in df_contacts.columns
    ]
    id_col = _contact_id_column(df_contacts)
    if not id_col:
        return {}
    out: Dict[str, Set[str]] = {}
    for _, row in df_contacts.iterrows():
        hid = _normalize_hubspot_id(row.get(id_col))
        if not hid:
            continue
        keys = _collect_phone_keys_from_row(row, phone_cols)
        if keys:
            out[hid] = keys
    return out


def _prepare_tickets_flat(df_tickets: pd.DataFrame) -> List[Dict[str, Any]]:
    """Liste plate de tickets avec contact(s), date, métadonnées."""
    need = [TICKET_COL_CONTACT_IDS, TICKET_COL_CREATED]
    if not all(c in df_tickets.columns for c in need):
        return []
    df = df_tickets.copy()
    df[TICKET_COL_CREATED] = pd.to_datetime(df[TICKET_COL_CREATED], errors="coerce")
    tid_col = TICKET_COL_ID if TICKET_COL_ID in df.columns else None
    src_col = TICKET_COL_SOURCE if TICKET_COL_SOURCE in df.columns else None
    pipe_col = TICKET_COL_PIPELINE if TICKET_COL_PIPELINE in df.columns else None
    conv_col = TICKET_COL_CONV_IDS if TICKET_COL_CONV_IDS in df.columns else None

    rows: List[Dict[str, Any]] = []
    for _, row in df.iterrows():
        cids = _parse_contact_ids_cell(row[TICKET_COL_CONTACT_IDS])
        if not cids:
            continue
        dt = row[TICKET_COL_CREATED]
        if pd.isna(dt):
            continue
        hs_conv = _parse_hubspot_conversation_ids_cell(row[conv_col]) if conv_col else []
        rec = {
            "date": pd.Timestamp(dt),
            "ticket_id": row[tid_col] if tid_col else None,
            "source": row[src_col] if src_col else None,
            "pipeline": row[pipe_col] if pipe_col else None,
            "hubspot_conversation_ids": hs_conv,
        }
        for cid in cids:
            r = rec.copy()
            r["contact_id"] = cid
            rows.append(r)
    # Dédupliquer (même ticket / même contact si doublon export)
    dedup: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for tk in rows:
        tid = tk.get("ticket_id")
        key = (tk["contact_id"], str(tid) if tid is not None else str(id(tk)))
        dedup[key] = tk
    return list(dedup.values())


def _build_conversations_by_contact(df_stellair: pd.DataFrame) -> Dict[str, List[Tuple[Any, pd.Timestamp]]]:
    """
    contact_id -> liste (conv_id, t0) triée par t0 croissant (toutes conversations fse.stellair).
    """
    df = df_stellair.copy()
    df[COL_DATE] = pd.to_datetime(df[COL_DATE], errors="coerce")
    df = df[df[COL_DATE].notna()]
    id_slot = COL_HUBSPOT_ID_SLOT if COL_HUBSPOT_ID_SLOT in df.columns else None
    conv_col = COL_ID_CONV if COL_ID_CONV in df.columns else None
    if not id_slot or not conv_col:
        return {}
    out: Dict[str, List[Tuple[Any, pd.Timestamp]]] = {}
    for _, row in df.iterrows():
        hid = _normalize_hubspot_id(row.get(id_slot))
        if not hid:
            continue
        t0 = pd.Timestamp(row[COL_DATE])
        cid = row[conv_col]
        out.setdefault(hid, []).append((cid, t0))
    for hid in out:
        out[hid].sort(key=lambda x: x[1])
    return out


def _attribute_ticket_to_conversation(
    conv_sorted: List[Tuple[Any, pd.Timestamp]], ticket_time: pd.Timestamp
) -> Any:
    """Dernière conversation avec t0 <= heure du ticket (même contact)."""
    chosen = None
    for conv_id, t in conv_sorted:
        if t <= ticket_time:
            chosen = conv_id
        else:
            break
    return chosen


def _calls_in_window_for_keys(
    df_aircall: pd.DataFrame,
    phone_keys: Set[str],
    t0: pd.Timestamp,
    t1: pd.Timestamp,
) -> int:
    if df_aircall is None or df_aircall.empty or not phone_keys:
        return 0
    if "StartTime" not in df_aircall.columns:
        return 0
    st = pd.to_datetime(df_aircall["StartTime"], errors="coerce")
    mask_time = (st >= t0) & (st <= t1)
    dfw = df_aircall.loc[mask_time]
    if dfw.empty:
        return 0
    n = 0
    for _, row in dfw.iterrows():
        keys_row: Set[str] = set()
        for col in ("FromNumber", "ToNumber"):
            if col in row.index:
                k = phone_match_key(row.get(col))
                if k:
                    keys_row.add(k)
        if keys_row & phone_keys:
            n += 1
    return n


def build_yelda_conversation_cross_analysis(
    df_yelda_periode: pd.DataFrame,
    df_tickets: pd.DataFrame,
    df_aircall: pd.DataFrame,
    df_contacts: Optional[pd.DataFrame] = None,
    window_hours: float = DEFAULT_WINDOW_HOURS,
    df_yelda_stellair_full: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """
    Une ligne par conversation dans ``df_yelda_periode`` (fse.stellair, dates valides).

    ``df_yelda_stellair_full`` : toutes les conversations Stellair (hors filtre période) pour
    l'attribution des tickets ; si None, on utilise ``df_yelda_periode`` (moins précis).
    """
    if df_yelda_periode is None or df_yelda_periode.empty:
        return pd.DataFrame()

    df_out = filter_yelda_stellair(df_yelda_periode).copy()
    if df_out.empty:
        return pd.DataFrame()

    df_out[COL_DATE] = pd.to_datetime(df_out[COL_DATE], errors="coerce")
    df_out = df_out[df_out[COL_DATE].notna()].copy()

    df_full = filter_yelda_stellair(df_yelda_stellair_full) if df_yelda_stellair_full is not None else df_out
    conv_by_contact = _build_conversations_by_contact(df_full)

    contact_phone_map: Dict[str, Set[str]] = {}
    if df_contacts is not None and not df_contacts.empty:
        contact_phone_map = build_contact_id_to_phone_keys(df_contacts)

    tickets_flat = _prepare_tickets_flat(df_tickets)
    # Index tickets par contact pour fenêtre + attribution
    tickets_by_contact: Dict[str, List[Dict[str, Any]]] = {}
    for tk in tickets_flat:
        tickets_by_contact.setdefault(tk["contact_id"], []).append(tk)
    for cid in tickets_by_contact:
        tickets_by_contact[cid].sort(key=lambda x: x["date"])

    parcours_col = COL_PARCOURS if COL_PARCOURS in df_out.columns else None
    id_slot_col = COL_HUBSPOT_ID_SLOT if COL_HUBSPOT_ID_SLOT in df_out.columns else None
    conv_col = COL_ID_CONV if COL_ID_CONV in df_out.columns else None

    delta = pd.Timedelta(hours=window_hours)
    rows: List[Dict[str, Any]] = []

    for idx, row in df_out.iterrows():
        t0 = pd.Timestamp(row[COL_DATE])
        t1 = t0 + delta
        hid = _normalize_hubspot_id(row.get(id_slot_col)) if id_slot_col else None
        ticket_parcours = bool(parcours_col and has_ticket_created(row.get(parcours_col)))

        conv_id_row = row[conv_col] if conv_col else idx

        phone_keys: Set[str] = set()
        if COL_YELDA_PHONE in row.index:
            phone_keys |= _collect_phone_keys_from_row(row, [COL_YELDA_PHONE])
        if hid and hid in contact_phone_map:
            phone_keys |= contact_phone_map[hid]

        nb_tickets = 0
        nb_hors_chat = 0
        nb_pipe_yelda = 0
        ticket_ids_all: List[Any] = []
        ids_attribues: List[Any] = []
        hs_conv_attrib: List[str] = []

        if hid and hid in tickets_by_contact:
            conv_sorted = conv_by_contact.get(hid, [])
            for tk in tickets_by_contact[hid]:
                d = tk["date"]
                if not (t0 <= d <= t1):
                    continue
                nb_tickets += 1
                ticket_ids_all.append(tk.get("ticket_id"))
                src = tk.get("source")
                if src is None or (isinstance(src, float) and np.isnan(src)):
                    nb_hors_chat += 1
                else:
                    s = str(src).strip()
                    if s != SOURCE_CHAT:
                        nb_hors_chat += 1
                pipe = tk.get("pipeline")
                if pipe is not None and str(pipe).strip() == PIPELINE_CHATBOT_YELDA:
                    nb_pipe_yelda += 1

                att = _attribute_ticket_to_conversation(conv_sorted, d) if conv_sorted else None
                if att is not None and att == conv_id_row:
                    tid = tk.get("ticket_id")
                    if tid is not None:
                        ids_attribues.append(tid)
                    for x in tk.get("hubspot_conversation_ids") or []:
                        if x not in hs_conv_attrib:
                            hs_conv_attrib.append(x)

        nb_tickets_attribues = len(ids_attribues)
        nb_tickets_fenetre_autres_sessions = max(0, nb_tickets - nb_tickets_attribues)

        nb_calls = _calls_in_window_for_keys(df_aircall, phone_keys, t0, t1)

        url_val = row[COL_URL] if COL_URL in row.index else np.nan
        eval_llm = row[COL_EVAL_LLM] if COL_EVAL_LLM in row.index else np.nan
        duree = row[COL_DUREE] if COL_DUREE in row.index else np.nan

        rows.append(
            {
                COL_ID_CONV: conv_id_row,
                COL_DATE: t0,
                "window_end": t1,
                "window_hours": window_hours,
                COL_URL: url_val,
                COL_EVAL_LLM: eval_llm,
                COL_DUREE: duree,
                "hubspot_contact_id": hid if hid else np.nan,
                "has_hubspot_id": bool(hid),
                "ticket_creation_parcours_yelda": ticket_parcours,
                "nb_tickets_fenetre": nb_tickets,
                "nb_tickets_fenetre_attribues_cette_session": nb_tickets_attribues,
                "nb_tickets_fenetre_autres_sessions": nb_tickets_fenetre_autres_sessions,
                "nb_tickets_fenetre_hors_source_chat": nb_hors_chat,
                "nb_tickets_fenetre_pipeline_chatbot_yelda": nb_pipe_yelda,
                "ticket_ids_fenetre": ";".join(str(x) for x in ticket_ids_all if x is not None and str(x) != "nan"),
                "ticket_ids_attribues_cette_session": ";".join(str(x) for x in ids_attribues if x is not None),
                "hubspot_conversation_ids_tickets_attribues": ";".join(hs_conv_attrib),
                "nb_appels_aircall_fenetre": nb_calls,
                "nb_cles_telephone_utilisees": len(phone_keys),
            }
        )

    return pd.DataFrame(rows)


def aggregate_yelda_cross_metrics(df_cross: pd.DataFrame) -> Dict[str, Any]:
    """Synthèse sur la période (tableau croisé par conversation)."""
    if df_cross is None or df_cross.empty:
        return {
            "nb_conversations": 0,
            "nb_avec_hubspot_id": 0,
            "part_avec_hubspot_id_pct": 0.0,
            "nb_parcours_false_avec_tickets_fenetre": 0,
            "part_parcours_false_avec_tickets_fenetre_pct": 0.0,
            "moyenne_nb_tickets_fenetre": 0.0,
            "moyenne_nb_tickets_attribues_session": 0.0,
            "nb_cas_limites_parcours_vs_tickets": 0,
        }
    n = len(df_cross)
    avec_id = int(df_cross["has_hubspot_id"].sum()) if "has_hubspot_id" in df_cross.columns else 0
    m = (
        (~df_cross["ticket_creation_parcours_yelda"])
        & (df_cross["nb_tickets_fenetre"] > 0)
    )
    nb_lim = int(m.sum())
    return {
        "nb_conversations": n,
        "nb_avec_hubspot_id": avec_id,
        "part_avec_hubspot_id_pct": round(100 * avec_id / n, 1) if n else 0.0,
        "nb_parcours_false_avec_tickets_fenetre": nb_lim,
        "part_parcours_false_avec_tickets_fenetre_pct": round(100 * nb_lim / n, 1) if n else 0.0,
        "moyenne_nb_tickets_fenetre": round(float(df_cross["nb_tickets_fenetre"].mean()), 3),
        "moyenne_nb_tickets_attribues_session": round(
            float(df_cross["nb_tickets_fenetre_attribues_cette_session"].mean()), 3
        ),
        "nb_cas_limites_parcours_vs_tickets": nb_lim,
    }


def segment_yelda_cross_by_url(df_cross: pd.DataFrame) -> pd.DataFrame:
    """Agrégation par URL d'origine."""
    if df_cross is None or df_cross.empty or COL_URL not in df_cross.columns:
        return pd.DataFrame()
    rows = []
    for url, sub in df_cross.groupby(df_cross[COL_URL].fillna("(non renseigné)")):
        m = (~sub["ticket_creation_parcours_yelda"]) & (sub["nb_tickets_fenetre"] > 0)
        rows.append(
            {
                "url": url,
                "nb_conversations": len(sub),
                "nb_avec_hubspot_id": int(sub["has_hubspot_id"].sum()),
                "moy_nb_tickets_fenetre": round(float(sub["nb_tickets_fenetre"].mean()), 3),
                "moy_nb_tickets_attribues": round(
                    float(sub["nb_tickets_fenetre_attribues_cette_session"].mean()), 3
                ),
                "nb_cas_parcours_false_avec_tickets_fenetre": int(m.sum()),
            }
        )
    return pd.DataFrame(rows)


def sample_yelda_cross_edge_cases(
    df_cross: pd.DataFrame, n: int = 20
) -> pd.DataFrame:
    """Cas limites : pas de creation_ticket_hubspot dans le parcours mais tickets dans la fenêtre."""
    if df_cross is None or df_cross.empty:
        return pd.DataFrame()
    m = (~df_cross["ticket_creation_parcours_yelda"]) & (df_cross["nb_tickets_fenetre"] > 0)
    out = df_cross.loc[m].copy()
    if out.empty:
        return out
    out = out.sort_values("nb_tickets_fenetre", ascending=False).head(n)
    cols = [
        c
        for c in [
            COL_ID_CONV,
            COL_DATE,
            "hubspot_contact_id",
            COL_URL,
            "ticket_creation_parcours_yelda",
            "nb_tickets_fenetre",
            "nb_tickets_fenetre_attribues_cette_session",
            "nb_tickets_fenetre_autres_sessions",
            COL_EVAL_LLM,
        ]
        if c in out.columns
    ]
    return out[cols]


def default_paths(project_root: Path | None = None) -> Tuple[Path, Path, Path]:
    root = project_root or Path(__file__).resolve().parents[1]
    contacts = root / "data/Affid/Hubspot/contacts"
    return contacts, root / "data/Affid/Hubspot/ticket", root / "data/Affid/yelda/yelda.xlsx"
