#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Récupère les résumés IA Aircall (résumé + topics + sentiment) des appels ENTRANTS.

- Source des Call IDs : données locales (exports Aircall), filtrées entrants + répondus.
- Pour chaque appel : GET /summary ; si présent, GET /topics et /sentiments.
  (La transcription complète n'est pas récupérée — le résumé suffit et limite les données perso.)
- Respecte le rate limit Aircall (~60 req/min), gère les 404 (pas d'IA) et 429 (backoff).
- Sortie : CSV dans resumes_appels/ (gitignoré — contient des données personnelles).

Clés lues depuis .env / config.env (AIRCALL_API_ID, AIRCALL_API_TOKEN).

Exemples :
    python scripts/recup_resumes_appels.py --mois 2026-07
    python scripts/recup_resumes_appels.py --mois 2026-07 --max 20      # test
"""
import argparse
import os
import sys
import time

import pandas as pd
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from echantillon_analyse import charger_appels, mois_precedent  # réutilise le chargement/dérivations

BASE = "https://api.aircall.io/v1"


def _get(session, url, sleep):
    """GET robuste : gère le rate limit (429) et les coupures réseau (retry + backoff)."""
    for essai in range(6):
        try:
            r = session.get(url, timeout=30)
        except requests.exceptions.RequestException:
            time.sleep(min(2 ** essai, 30))   # backoff réseau
            continue
        if r.status_code == 429:
            time.sleep(int(r.headers.get("Retry-After", 10)) + 1)
            continue
        time.sleep(sleep)
        return r
    return None   # échec après plusieurs tentatives -> l'appel sera repris au prochain lancement


def main():
    p = argparse.ArgumentParser(description="Récupération des résumés IA Aircall (appels entrants).")
    p.add_argument("--mois", default=None, help="Mois AAAA-MM (défaut : mois précédent)")
    p.add_argument("--max", type=int, default=0, help="Limiter le nb d'appels traités (0 = tous)")
    p.add_argument("--sleep", type=float, default=1.05, help="Pause entre requêtes (s), rate limit ~60/min")
    p.add_argument("--sortie", default="resumes_appels", help="Dossier de sortie")
    p.add_argument("--sans-sentiment", action="store_true", help="Ne pas récupérer le sentiment")
    args = p.parse_args()

    load_dotenv(".env") if os.path.exists(".env") else load_dotenv("config.env")
    api_id, api_token = os.getenv("AIRCALL_API_ID"), os.getenv("AIRCALL_API_TOKEN")
    if not (api_id and api_token):
        sys.exit("Clés Aircall manquantes (config.env / .env).")
    session = requests.Session()
    session.auth = HTTPBasicAuth(api_id, api_token)

    mois = args.mois or mois_precedent()
    os.makedirs(args.sortie, exist_ok=True)
    fichier = os.path.join(args.sortie, f"resumes_appels_{mois}.csv")

    # ----- Call IDs entrants répondus du mois (source locale) -----
    a = charger_appels()
    sel = a[(a["mois"] == mois) & a["answered"] & (a["direction"] == "inbound")].copy()
    sel = sel[sel["call_id"].notna()].drop_duplicates("call_id")
    if args.max:
        sel = sel.head(args.max)

    # ----- Reprise : ne pas retraiter les appels déjà dans le CSV -----
    existing, deja = None, set()
    if os.path.exists(fichier):
        existing = pd.read_csv(fichier)
        if "call_id" in existing.columns:
            deja = set(pd.to_numeric(existing["call_id"], errors="coerce").dropna().astype(int))
    sel = sel[~sel["call_id"].astype(int).isin(deja)]
    n_ai = int(existing["a_resume"].sum()) if (existing is not None and "a_resume" in existing) else 0
    total = len(sel)
    print(f"Mois {mois} : {len(deja)} déjà traités, {total} restants à interroger.")

    def flush(nouvelles):
        parts = [df for df in (existing, pd.DataFrame(nouvelles)) if df is not None and len(df)]
        if parts:
            pd.concat(parts, ignore_index=True).to_csv(fichier, index=False, encoding="utf-8-sig")

    lignes = []
    for idx, (_, row) in enumerate(sel.iterrows(), 1):
        cid = int(row["call_id"])
        base = {
            "call_id": cid, "Date": row.get("Date"), "univers": row.get("univers"),
            "line": row.get("line"), "UserName": row.get("UserName"),
            "a_resume": False, "resume": "", "topics": "", "sentiment_externe": "",
        }
        rs = _get(session, f"{BASE}/calls/{cid}/summary", args.sleep)
        if rs is None:
            continue   # échec réseau : laissé pour une reprise ultérieure (non écrit)
        if rs.status_code == 200:
            n_ai += 1
            base["a_resume"] = True
            base["resume"] = (rs.json().get("summary") or {}).get("content", "")
            rt = _get(session, f"{BASE}/calls/{cid}/topics", args.sleep)
            if rt is not None and rt.status_code == 200:
                base["topics"] = " | ".join((rt.json().get("topic") or {}).get("content", []) or [])
            if not args.sans_sentiment:
                rse = _get(session, f"{BASE}/calls/{cid}/sentiments", args.sleep)
                if rse is not None and rse.status_code == 200:
                    parts = (rse.json().get("sentiment") or {}).get("participants", []) or []
                    ext = [pp.get("value") for pp in parts if pp.get("type") == "external"]
                    base["sentiment_externe"] = ext[0] if ext else ""
        lignes.append(base)

        if idx % 50 == 0 or idx == total:
            flush(lignes)
            print(f"  {idx}/{total} restants traités | total avec résumé IA : {n_ai}")

    flush(lignes)
    fait = len(deja) + len(lignes)
    taux = round(100 * n_ai / fait, 1) if fait else 0
    print(f"\nTerminé : {n_ai}/{fait} appels avec résumé IA ({taux}%).")
    print(f"Sortie : {fichier}")


if __name__ == "__main__":
    main()
