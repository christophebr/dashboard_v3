#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Analyse des résumés IA d'appels + tickets -> agrégat ANONYME committable, sur 2 niveaux.

Taxonomie : Thème (socle = 8 sujets tickets) -> Sous-catégorie (hybride :
socle = catégories tickets, le LLM en ajoute pour les appels si nécessaire).

Étapes :
1. Charge les résumés d'appels du mois + les tickets support du mois.
2. Classe (LLM, Claude) chaque appel dans un THÈME (seedé sujets tickets).
3. Rattache les tickets à un thème (mapping macro + LLM pour les catégories non couvertes).
4. Sous-catégories : tickets = leur Catégorie ; appels = classés par LLM (seed = catégories
   tickets du thème, ajout possible).
5. Agrège volumes / sentiment / préférence de canal par thème ET par sous-catégorie.
6. Exemples de résumés ANONYMISÉS (LLM). Sortie JSON anonyme (committable).

Clé : config.ANTHROPIC_API_KEY. Modèle : claude-haiku-4-5-20251001.
"""
import argparse
import collections
import json
import os
import re
import sqlite3
import sys

import pandas as pd

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.dirname(_HERE))
from echantillon_analyse import mois_precedent

from data_processing.hubspot_ticket_category_macros import HUBSPOT_CATEGORIE_VERS_SUJET

MODEL = "claude-haiku-4-5-20251001"
PIPELINES_SUPPORT = ("SSI", "SSIA", "SPSA")
SEED_THEMES = sorted(set(HUBSPOT_CATEGORIE_VERS_SUJET.values())) + ["Autre"]
MAX_SOUS_CAT = 8  # sous-catégories max affichées par thème (reste regroupé en "Autres")


def _client():
    try:
        import config
        key = getattr(config, "ANTHROPIC_API_KEY", None) or os.getenv("ANTHROPIC_API_KEY")
    except Exception:
        key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        sys.exit("ANTHROPIC_API_KEY manquante (config.py).")
    import anthropic
    return anthropic.Anthropic(api_key=key)


def _llm_json(client, prompt, max_tokens=4000):
    r = client.messages.create(model=MODEL, max_tokens=max_tokens,
                               messages=[{"role": "user", "content": prompt}])
    txt = r.content[0].text.strip()
    m = re.search(r"\{.*\}|\[.*\]", txt, re.DOTALL)
    return json.loads(m.group(0) if m else txt)


def classer(client, textes, choix, consigne, batch=40):
    """Classe chaque texte dans un élément de `choix` (nouvel élément si vraiment nécessaire).

    Contrat : le LLM renvoie un TABLEAU JSON de N valeurs, dans l'ordre des éléments.
    """
    out = ["Autre"] * len(textes)
    for i in range(0, len(textes), batch):
        lot = [(textes[i + j] or "")[:300] for j in range(len(textes[i:i + batch]))]
        numerote = "\n".join(f"{j}. {txt}" for j, txt in enumerate(lot))
        prompt = (
            f"{consigne}\nPour chaque élément, choisis UNE valeur PARMI cette liste :\n{choix}\n"
            "N'ajoute une valeur hors liste que si aucune ne convient vraiment.\n"
            f"Réponds UNIQUEMENT par un tableau JSON de {len(lot)} valeurs, dans le même ordre "
            "(ex. [\"Lecteur\", \"Facturation\", ...]).\n\n"
            f"Éléments :\n{numerote}"
        )
        try:
            arr = _llm_json(client, prompt)
            if isinstance(arr, dict):                       # tolérance : {"0": "...", ...}
                arr = [arr.get(str(j)) for j in range(len(lot))]
            for j, v in enumerate(arr[:len(lot)]):
                if isinstance(v, str) and v.strip():
                    out[i + j] = v.strip()
        except Exception as e:
            print(f"  ⚠️ classif lot {i}: {e}")
    return out


def anonymiser(client, textes):
    if not textes:
        return []
    prompt = (
        "Anonymise ces résumés d'appels : noms de personnes -> [NOM], téléphones -> [TEL], "
        "emails -> [EMAIL], numéros de contrat/client -> [ID]. Conserve le sens métier. "
        "Réponds UNIQUEMENT en JSON : une liste de chaînes, même ordre.\n\n"
        f"{json.dumps(textes, ensure_ascii=False)}"
    )
    def scrub(t):
        t = re.sub(r"[\w.\-]+@[\w.\-]+", "[EMAIL]", str(t))
        return re.sub(r"\d[\d ().\-]{6,}\d", "[TEL]", t)   # numéros même espacés
    try:
        out = _llm_json(client, prompt)
        if isinstance(out, list) and len(out) == len(textes):
            return [scrub(x) for x in out]                 # passe regex APRÈS le LLM (ceinture+bretelles)
    except Exception as e:
        print(f"  ⚠️ anonymisation: {e}")
    return [scrub(t) for t in textes]


def cat_clean(c):
    c = str(c or "").split(";")[0].split(",")[0].strip()
    return c


def part(na, nt):
    tot = na + nt
    return (round(100 * na / tot, 1), round(100 * nt / tot, 1)) if tot else (None, None)


def signal_appel(row):
    s = row["topics"] if isinstance(row["topics"], str) and row["topics"].strip() else str(row.get("resume", ""))
    return s[:300]


def main():
    p = argparse.ArgumentParser(description="Analyse résumés appels/tickets -> agrégat anonyme (2 niveaux).")
    p.add_argument("--mois", default=None)
    p.add_argument("--exemples", type=int, default=2)
    args = p.parse_args()
    mois = args.mois or mois_precedent()

    f_in = f"resumes_appels/resumes_appels_{mois}.csv"
    if not os.path.exists(f_in):
        sys.exit(f"Fichier introuvable : {f_in}")
    calls = pd.read_csv(f_in)
    ai = calls[calls["a_resume"] == True].copy().reset_index(drop=True)
    ai["signal"] = ai.apply(signal_appel, axis=1)

    con = sqlite3.connect("data/Cache/data_cache.db")
    t = pd.read_sql("SELECT * FROM df_tickets", con); con.close()
    t = t[t["Pipeline"].isin(PIPELINES_SUPPORT)].copy()
    t["mois"] = pd.to_datetime(t["Date de création"], errors="coerce").dt.to_period("M").astype(str)
    tickets = t[t["mois"] == mois].copy().reset_index(drop=True)
    tickets["sous_cat"] = tickets["Catégorie"].apply(cat_clean).replace("", "Non précisé")

    client = _client()

    # --- Thème des TICKETS (mapping macro + LLM pour les catégories non couvertes) ---
    cats = sorted({c for c in tickets["sous_cat"] if c and c != "Non précisé"})
    non_mappees = [c for c in cats if c not in HUBSPOT_CATEGORIE_VERS_SUJET]
    map_llm = {}
    if non_mappees:
        themes_llm = classer(client, non_mappees, SEED_THEMES,
                             "Classe chaque CATÉGORIE de ticket support Stellair dans un thème.")
        map_llm = dict(zip(non_mappees, themes_llm))
    def theme_ticket(sc):
        return HUBSPOT_CATEGORIE_VERS_SUJET.get(sc) or map_llm.get(sc, "Autre")
    tickets["theme"] = tickets["sous_cat"].apply(theme_ticket)
    # Tickets à catégorie vide : thème via le sujet de la demande
    vides = tickets["sous_cat"] == "Non précisé"
    if vides.any() and "Sujet de la demande" in tickets.columns:
        themes_vides = classer(client, tickets.loc[vides, "Sujet de la demande"].fillna("").tolist(),
                               SEED_THEMES, "Classe chaque demande de ticket support Stellair dans un thème.")
        tickets.loc[vides, "theme"] = themes_vides

    # --- Thème des APPELS (niveau 1) ---
    print(f"Classement thème de {len(ai)} appels…")
    ai["theme"] = classer(client, ai["signal"].tolist(), SEED_THEMES,
                          "Classe chaque appel de support Stellair dans un thème.")

    # --- Sous-catégorie des APPELS (niveau 2, hybride : seed = catégories tickets du thème) ---
    ai["sous_cat"] = "Autres"
    for th in sorted(ai["theme"].unique()):
        idx = ai.index[ai["theme"] == th]
        seed = sorted(set(tickets.loc[tickets["theme"] == th, "sous_cat"]) - {"Non précisé"})
        choix = (seed or ["Divers"]) + ["Autres"]
        sc = classer(client, ai.loc[idx, "signal"].tolist(), choix,
                     f"Sous-catégorie d'un appel du thème « {th} » (support Stellair).")
        ai.loc[idx, "sous_cat"] = sc

    # --- Agrégation 2 niveaux ---
    themes = sorted(set(ai["theme"]) | set(tickets["theme"]))
    out = {"mois": mois,
           "meta": {"nb_appels_entrants": int(len(calls)), "nb_appels_avec_ia": int(len(ai)),
                    "taux_couverture_ia_pct": round(100 * len(ai) / len(calls), 1) if len(calls) else 0,
                    "nb_tickets_support": int(len(tickets)),
                    "note": "Volumes d'appels = sur les appels avec résumé IA (couverture partielle)."},
           "themes": []}
    for th in themes:
        ca, ti = ai[ai["theme"] == th], tickets[tickets["theme"] == th]
        na, nt = len(ca), len(ti)
        pt, pe = part(na, nt)
        sent = ca["sentiment_externe"].replace("", "INCONNU").value_counts().to_dict()
        # sous-catégories (union), triées par volume, top N + "Autres"
        subs = {}
        for sc in set(ca["sous_cat"]) | set(ti["sous_cat"]):
            sna, snt = int((ca["sous_cat"] == sc).sum()), int((ti["sous_cat"] == sc).sum())
            spt, spe = part(sna, snt)
            subs[sc] = {"sous_cat": sc, "nb_appels": sna, "nb_tickets": snt,
                        "part_telephone_pct": spt, "part_ecrit_pct": spe}
        sous = sorted(subs.values(), key=lambda x: -(x["nb_appels"] + x["nb_tickets"]))
        if len(sous) > MAX_SOUS_CAT:
            tete, reste = sous[:MAX_SOUS_CAT], sous[MAX_SOUS_CAT:]
            rna, rnt = sum(s["nb_appels"] for s in reste), sum(s["nb_tickets"] for s in reste)
            rpt, rpe = part(rna, rnt)
            tete.append({"sous_cat": "Autres", "nb_appels": rna, "nb_tickets": rnt,
                         "part_telephone_pct": rpt, "part_ecrit_pct": rpe})
            sous = tete
        exemples = anonymiser(client, ca["resume"].dropna().astype(str)
                              .sort_values(key=lambda s: s.str.len()).head(args.exemples).tolist())
        out["themes"].append({"theme": th, "nb_appels": na, "nb_tickets": nt,
                              "part_telephone_pct": pt, "part_ecrit_pct": pe,
                              "sentiment": {k: int(v) for k, v in sent.items()},
                              "sous_categories": sous, "exemples_anonymises": exemples})
    out["themes"].sort(key=lambda x: -(x["nb_appels"] + x["nb_tickets"]))

    os.makedirs("data/Affid/analyse_appels_tickets", exist_ok=True)
    f_out = f"data/Affid/analyse_appels_tickets/analyse_resumes_appels_{mois}.json"
    with open(f_out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)

    print(f"\n=== SYNTHÈSE {mois} ===")
    print(f"{'Thème':<22}{'Appels':>8}{'Tickets':>9}{'%Tel':>7}{'%Écrit':>8}  sous-cat.")
    for th in out["themes"]:
        top = ", ".join(s["sous_cat"] for s in th["sous_categories"][:3])
        print(f"{th['theme']:<22}{th['nb_appels']:>8}{th['nb_tickets']:>9}"
              f"{(th['part_telephone_pct'] or 0):>7}{(th['part_ecrit_pct'] or 0):>8}  {top}")
    print(f"\nAgrégat écrit : {f_out}")


if __name__ == "__main__":
    main()
