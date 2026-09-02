#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Échantillonnage mensuel stratifié pour l'analyse/catégorisation appels & tickets.

Approche "roulant mensuel" : pour un mois donné, tire un échantillon aléatoire
STRATIFIÉ (proportionnel au volume de chaque strate) et REPRODUCTIBLE (seed fixe) :
  - Tickets support (SSI/SSIA/SPSA) stratifiés par pipeline.
  - Appels entrants répondus stratifiés par univers (Stellair/Affid/XMED/TMAJ).
  - + un fichier CIBLÉ (tickets escaladés N2) séparé, pour la couverture des cas
    importants mais rares (à NE PAS mélanger avec l'échantillon aléatoire pour les %).

Sorties : des CSV listant les éléments à analyser (Call ID interne pour les appels,
Ticket ID pour les tickets).

Exemples :
    python scripts/echantillon_analyse.py                      # mois précédent, 150+150
    python scripts/echantillon_analyse.py --mois 2026-07
    python scripts/echantillon_analyse.py --n-tickets 200 --n-appels 200 --seed 7
"""
import argparse
import glob
import os
import sys
from datetime import date

import pandas as pd

AIRCALL_DIR = "data/Affid/Aircall"
TICKETS_DIR = "data/Affid/Hubspot/ticket"
PIPELINES_SUPPORT = ("SSI", "SSIA", "SPSA")


def mois_precedent():
    t = date.today()
    premier = t.replace(day=1)
    fin_mois_prec = premier - pd.Timedelta(days=1)
    return f"{fin_mois_prec.year}-{fin_mois_prec.month:02d}"


def echantillon_stratifie(df, col_strate, n, seed):
    """Tirage aléatoire stratifié, allocation proportionnelle au volume."""
    if df.empty or n <= 0:
        return df.head(0)
    counts = df[col_strate].value_counts()
    total = len(df)
    alloc = {k: min(int(v), int(round(n * v / total))) for k, v in counts.items()}
    diff = n - sum(alloc.values())
    for k in counts.index:                       # ajuste pour atteindre n
        if diff == 0:
            break
        if diff > 0:
            marge = int(counts[k]) - alloc[k]
            add = min(marge, diff); alloc[k] += add; diff -= add
        else:
            red = min(alloc[k], -diff); alloc[k] -= red; diff += red
    parts = [df[df[col_strate] == k].sample(n=na, random_state=seed)
             for k, na in alloc.items() if na > 0]
    return pd.concat(parts) if parts else df.head(0)


def charger_appels():
    frames = []
    for d in ("data_v1", "data_v2", "data_v3"):
        for f in sorted(glob.glob(os.path.join(AIRCALL_DIR, d, "*.xls")) +
                        glob.glob(os.path.join(AIRCALL_DIR, d, "*.xlsx"))):
            try:
                frames.append(pd.read_excel(f))
            except Exception:
                frames.append(pd.read_excel(f, engine="xlrd"))
    if not frames:
        sys.exit(f"Aucun fichier Aircall dans {AIRCALL_DIR}.")
    a = pd.concat(frames, ignore_index=True)
    a = a.rename(columns={"from": "FromNumber", "answered": "answered_raw", "user": "UserName",
                          "datetime (tz offset incl.)": "StartTime", "tags": "Tags",
                          "ivr branch": "IVR Branch", "call id (internal)": "call_id"})
    a = a.loc[:, ~a.columns.duplicated()]  # évite les colonnes en double après concat/rename
    a["StartTime"] = pd.to_datetime(a["StartTime"], errors="coerce")
    a = a[a["StartTime"].notna()]
    for col in ("IVR Branch", "Tags"):
        if col not in a.columns:
            a[col] = ""
    a["line_norm"] = a["line"].astype(str).str.replace(" ", "", regex=False).str.lower()

    # Dérivation vectorisée de 'Logiciel' (priorité : IVR Branch > line armatistechnique > préfixe Tags)
    ivr = a["IVR Branch"].where(a["IVR Branch"].notna(), "").astype(str).str.strip()
    tags3 = a["Tags"].where(a["Tags"].notna(), "").astype(str).str[:3].str.upper()
    log = pd.Series("Inconnu", index=a.index, dtype="object")
    log[tags3.eq("AFD")] = "Affid"
    log[tags3.eq("STE")] = "Stellair"
    log[a["line_norm"].eq("armatistechnique")] = "Stellair"
    m_ivr = ivr.ne("")
    log[m_ivr] = ivr[m_ivr]
    a["Logiciel"] = log

    # Univers (Stellair prioritaire, cohérent avec est_stellair)
    u = pd.Series("Autre", index=a.index, dtype="object")
    u[a["Logiciel"].eq("Affid")] = "Affid"
    u[a["line_norm"].eq("xmed")] = "XMED"
    u[a["line_norm"].eq("supporthardware")] = "TMAJ"
    u[a["line_norm"].eq("armatistechnique") | a["Logiciel"].eq("Stellair")] = "Stellair"
    a["univers"] = u

    a["answered"] = a["answered_raw"].astype(str).str.lower().isin(["yes", "answered"])
    if "call_id" in a.columns:  # entier propre (sans .0) pour l'API Aircall
        a["call_id"] = pd.to_numeric(a["call_id"], errors="coerce").astype("Int64")
    a["mois"] = a["StartTime"].dt.to_period("M").astype(str)
    a["Date"] = a["StartTime"].dt.date
    return a


def charger_tickets():
    fichiers = sorted(glob.glob(os.path.join(TICKETS_DIR, "*.xlsx")) +
                      glob.glob(os.path.join(TICKETS_DIR, "*.xls")))
    if not fichiers:
        sys.exit(f"Aucun export tickets dans {TICKETS_DIR}.")
    t = pd.read_excel(max(fichiers, key=os.path.getmtime))  # le plus récent
    t["_crea"] = pd.to_datetime(t["Date de création"], errors="coerce")
    t = t[t["_crea"].notna()]
    if "Ticket ID" in t.columns:                             # dédoublonnage
        t = t.sort_values("_crea").drop_duplicates("Ticket ID", keep="last")
    t["mois"] = t["_crea"].dt.to_period("M").astype(str)
    return t


def main():
    p = argparse.ArgumentParser(description="Échantillon mensuel stratifié appels & tickets.")
    p.add_argument("--mois", default=None, help="Mois cible AAAA-MM (défaut : mois précédent)")
    p.add_argument("--n-tickets", type=int, default=150)
    p.add_argument("--n-appels", type=int, default=150)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--sortie", default="echantillons", help="Dossier de sortie")
    args = p.parse_args()

    mois = args.mois or mois_precedent()
    os.makedirs(args.sortie, exist_ok=True)
    print(f"Mois cible : {mois} | seed : {args.seed}")

    # ---- TICKETS ----
    t = charger_tickets()
    t_mois = t[(t["mois"] == mois) & (t["Pipeline"].isin(PIPELINES_SUPPORT))].copy()
    ech_t = echantillon_stratifie(t_mois, "Pipeline", args.n_tickets, args.seed)
    cols_t = [c for c in ["Ticket ID", "Date de création", "Pipeline", "Source",
                          "Propriétaire du ticket", "Passé par le support N2", "Catégorie",
                          "Sujet de la demande"] if c in ech_t.columns]
    f_t = os.path.join(args.sortie, f"echantillon_tickets_{mois}.csv")
    ech_t[cols_t].to_csv(f_t, index=False, encoding="utf-8-sig")
    print(f"\nTickets support {mois} : {len(t_mois)} -> échantillon {len(ech_t)}")
    print(ech_t["Pipeline"].value_counts().to_string())
    print(f"  -> {f_t}")

    # ---- TICKETS CIBLÉS N2 (couverture, hors % aléatoires) ----
    if "Passé par le support N2" in t_mois.columns:
        n2 = t_mois[t_mois["Passé par le support N2"] == "Oui"]
        f_n2 = os.path.join(args.sortie, f"cibles_tickets_N2_{mois}.csv")
        n2[cols_t].to_csv(f_n2, index=False, encoding="utf-8-sig")
        print(f"Ciblé N2 (tous) : {len(n2)} -> {f_n2}")

    # ---- APPELS ----
    a = charger_appels()
    a_mois = a[(a["mois"] == mois) & a["answered"] & (a["direction"] == "inbound")].copy()
    ech_a = echantillon_stratifie(a_mois, "univers", args.n_appels, args.seed)
    cols_a = [c for c in ["call_id", "Date", "univers", "line", "UserName", "FromNumber",
                          "direction"] if c in ech_a.columns]
    f_a = os.path.join(args.sortie, f"echantillon_appels_{mois}.csv")
    ech_a[cols_a].to_csv(f_a, index=False, encoding="utf-8-sig")
    print(f"\nAppels répondus {mois} : {len(a_mois)} -> échantillon {len(ech_a)}")
    print(ech_a["univers"].value_counts().to_string())
    n_id = ech_a["call_id"].notna().sum() if "call_id" in ech_a.columns else 0
    print(f"  dont Call ID interne renseigné : {n_id}/{len(ech_a)}")
    print(f"  -> {f_a}")


if __name__ == "__main__":
    main()
