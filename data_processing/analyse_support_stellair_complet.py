#!/usr/bin/env python3
"""
Analyse support Stellair (HubSpot) : **un seul fichier Excel** agrégé.

Contenu du classeur :
  - Méthodologie (texte COMEX, cohorte, macro-catégories)
  - Par_anciennete_mois — moyenne tickets / client par mois depuis souscription
  - Par_anciennete_macro — idem ventilé par 2 familles (lecteurs vs infos/logiciel)
  - Totaux_macro — volumes et parts sur la cohorte
  - Moyen_par_mois — série mensuelle calendaire
  - Contacts_eligibles_12m — cohorte « au moins 12 mois »
  - Contacts_ADV_tous — tous les contacts avec date souscription ADV
  - Resume_fenetres — synthèse fenêtres mois 1–3 vs 4–12, etc.

Les calculs sont ceux de ``hubspot_subscription_support_analysis``.

Usage :
  python3 data_processing/analyse_support_stellair_complet.py
  python3 data_processing/analyse_support_stellair_complet.py chemin/vers/export_tickets.xlsx
  python3 data_processing/analyse_support_stellair_complet.py export.xlsx -o rapport.xlsx
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

# Racine du projet (parent de data_processing/)
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from data_processing.hubspot_subscription_support_analysis import (  # noqa: E402
    MIN_SUBSCRIPTION_AGE_MONTHS,
    export_support_stellair_workbook,
)


def _default_ticket_xlsx() -> Path:
    d = _ROOT / "data/Affid/Hubspot/ticket"
    cands = sorted(d.glob("*.xlsx"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not cands:
        raise SystemExit(f"Aucun .xlsx dans {d}")
    return cands[0]


def main() -> None:
    p = argparse.ArgumentParser(
        description="Export agrégé Excel (méthodologie + tables) — analyse support Stellair."
    )
    p.add_argument(
        "ticket_xlsx",
        nargs="?",
        type=Path,
        help="Export HubSpot tickets (.xlsx). Par défaut : dernier fichier du dossier ticket.",
    )
    p.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Fichier .xlsx de sortie. Défaut : même dossier que l'export, nom *_analyse_support_stellair_complet.xlsx",
    )
    p.add_argument(
        "--min-mois-recul",
        type=int,
        default=MIN_SUBSCRIPTION_AGE_MONTHS,
        help=f"Cohorte : souscription au moins N mois avant la fin des données (défaut {MIN_SUBSCRIPTION_AGE_MONTHS}).",
    )
    args = p.parse_args()

    src = args.ticket_xlsx or _default_ticket_xlsx()
    if not src.is_file():
        raise SystemExit(f"Fichier introuvable : {src}")

    stem = src.stem
    out = args.output
    if out is None:
        out = src.parent / f"{stem}_analyse_support_stellair_complet.xlsx"

    df = pd.read_excel(src)
    export_support_stellair_workbook(
        df,
        out_xlsx=out,
        fichier_export_name=src.name,
        min_subscription_age_months=args.min_mois_recul,
    )
    print(f"Écrit : {out.resolve()}")


if __name__ == "__main__":
    main()
