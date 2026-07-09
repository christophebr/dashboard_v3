#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Analyse des appels entrants et détection d'anomalies de taux de service.

Reproduit l'analyse "pourquoi le taux de service a baissé" sur une période donnée :
contexte hebdomadaire, détail par jour / par heure, motifs des non-répondus,
plages où personne ne répond, créneaux sans agent disponible, clients insistants,
et comparaison du volume à la moyenne des autres semaines.

Périmètre = appels ENTRANTS, jours ouvrés, hors horaires fermés / abandons IVR
(mêmes règles que le dashboard).

Exemples :
    python scripts/analyse_appels.py                        # dernière semaine dispo, univers Stellair
    python scripts/analyse_appels.py --semaine 2026-27
    python scripts/analyse_appels.py --semaine S2026-27 --univers stellair
    python scripts/analyse_appels.py --du 2026-06-29 --au 2026-07-03
    python scripts/analyse_appels.py --univers affid --top 15 --seuil-plage 5

Lancer depuis la racine du dépôt (ou préciser --dossier).
"""
import argparse
import glob
import os
import sys

import pandas as pd

DOSSIER_DEFAUT = "data/Affid/Aircall/data_v3"
# Motifs exclus du calcul du taux de service (hors périmètre)
EXCLUS_HORS_SCOPE = {"out_of_opening_hours", "abandoned_in_ivr", "short_abandoned", "fermé", "ferme"}


def _logiciel(row):
    """Dérive 'Stellair' / 'Affid' comme aircall_processing.get_ivr_or_tags_transformed."""
    ivr = row["IVR Branch"]
    if pd.notna(ivr) and str(ivr).strip():
        return str(ivr)
    if row["line_norm"] == "armatistechnique":
        return "Stellair"
    tags = row["Tags"]
    t3 = str(tags)[:3].upper() if pd.notna(tags) else ""
    return {"STE": "Stellair", "AFD": "Affid"}.get(t3, "Inconnu")


def charger(dossier, verbose=True):
    """Charge et normalise tous les fichiers Aircall .xls d'un dossier."""
    fichiers = sorted(glob.glob(os.path.join(dossier, "*.xls")))
    if not fichiers:
        sys.exit(f"Aucun fichier .xls trouvé dans {dossier!r}. Lancez depuis la racine ou utilisez --dossier.")
    frames = []
    for f in fichiers:
        try:
            frames.append(pd.read_excel(f))
        except Exception:
            frames.append(pd.read_excel(f, engine="xlrd"))
    df = pd.concat(frames, ignore_index=True)
    if verbose:
        print(f"[i] {len(fichiers)} fichier(s) chargé(s), {len(df)} appels.", file=sys.stderr)

    df = df.rename(columns={
        "from": "FromNumber", "answered": "answered_raw", "missed_call_reason": "reason",
        "user": "UserName", "tags": "Tags", "ivr branch": "IVR Branch",
        "datetime (tz offset incl.)": "StartTime", "line": "line",
    })
    df["StartTime"] = pd.to_datetime(df["StartTime"], errors="coerce")
    df = df[df["StartTime"].notna()]
    df["line_norm"] = df["line"].astype(str).str.replace(" ", "", regex=False).str.lower()
    df["Logiciel"] = df.apply(_logiciel, axis=1)
    df["Semaine"] = df["StartTime"].dt.strftime("S%Y-%V")
    df["Jour"] = df["StartTime"].dt.day_name()
    df["Date"] = df["StartTime"].dt.date
    df["Heure"] = df["StartTime"].dt.hour
    df["inbound"] = df["direction"] == "inbound"
    df["answered"] = df["answered_raw"].astype(str).str.lower().isin(["yes", "answered"])
    df["reason_l"] = df["reason"].astype(str).str.lower()
    df["hors_scope"] = df["reason_l"].isin(EXCLUS_HORS_SCOPE)
    return df


def masque_univers(df, univers):
    """Renvoie le masque booléen du périmètre demandé."""
    u = univers.lower()
    if u == "stellair":
        return (df["line_norm"] == "armatistechnique") | (df["Logiciel"] == "Stellair")
    if u == "affid":
        return df["Logiciel"] == "Affid"
    if u == "xmed":
        return df["line_norm"] == "xmed"
    if u == "tmaj":
        return df["line_norm"] == "supporthardware"
    if u == "tous":
        return pd.Series(True, index=df.index)
    sys.exit(f"Univers inconnu : {univers!r} (stellair|affid|xmed|tmaj|tous)")


def normaliser_semaine(s):
    s = s.upper().replace("S", "")
    if "-" in s:
        an, sem = s.split("-")
    elif len(s) == 6:
        an, sem = s[:4], s[4:]
    else:
        sys.exit(f"Format de semaine non reconnu : {s!r} (ex. 2026-27, S2026-27, 202627)")
    return f"S{int(an)}-{int(sem):02d}"


def _table_taux(g):
    g = g.copy()
    g["manques"] = g["entrants"] - g["repondus"]
    g["taux_%"] = (100 * g["repondus"] / g["entrants"]).round(1)
    return g


def analyser(df, univers, cible, top, seuil_plage):
    scope = df[df["inbound"] & masque_univers(df, univers)
               & ~df["Jour"].isin(["Saturday", "Sunday"]) & ~df["hors_scope"]].copy()
    if scope.empty:
        sys.exit(f"Aucun appel entrant dans le périmètre '{univers}'.")

    # Sélection de la période cible
    if cible["type"] == "semaine":
        target = scope[scope["Semaine"] == cible["valeur"]]
        libelle = cible["valeur"]
    elif cible["type"] == "dates":
        d1, d2 = cible["valeur"]
        target = scope[(scope["StartTime"] >= d1) & (scope["StartTime"] <= d2)]
        libelle = f"{d1:%d/%m/%Y} → {d2:%d/%m/%Y}"
    else:  # dernière semaine
        libelle = scope["Semaine"].max()
        target = scope[scope["Semaine"] == libelle]
    if target.empty:
        sys.exit(f"Aucune donnée pour la période demandée ({libelle}).")

    ligne = "=" * 78
    print(f"\n{ligne}\n  ANALYSE APPELS ENTRANTS — univers {univers.upper()} — période {libelle}\n{ligne}")

    print("\n[1] TAUX DE SERVICE PAR SEMAINE (contexte)")
    print(_table_taux(scope.groupby("Semaine").agg(entrants=("answered", "size"),
                                                    repondus=("answered", "sum"))).to_string())

    print("\n[2] DÉTAIL PAR JOUR (période cible)")
    print(_table_taux(target.groupby("Date").agg(entrants=("answered", "size"),
                                                  repondus=("answered", "sum"))).to_string())

    print("\n[3] DÉTAIL PAR HEURE (période cible)")
    print(_table_taux(target.groupby("Heure").agg(entrants=("answered", "size"),
                                                   repondus=("answered", "sum"))).to_string())

    print("\n[4] MOTIFS DES APPELS NON RÉPONDUS (dans le périmètre)")
    manq = target[~target["answered"]]
    print(manq["reason"].value_counts(dropna=False).to_string() if not manq.empty else "  (aucun)")

    print(f"\n[5] PLAGES 'PERSONNE NE RÉPOND' (≥ {seuil_plage} appels non répondus consécutifs)")
    s = target.sort_values("StartTime").reset_index(drop=True)
    runs, start, last, cnt = [], None, None, 0
    for _, row in s.iterrows():
        if not row["answered"]:
            if start is None:
                start = last = row["StartTime"]; cnt = 1
            else:
                last = row["StartTime"]; cnt += 1
        else:
            if start is not None and cnt >= seuil_plage:
                runs.append((start, last, cnt))
            start, cnt = None, 0
    if start is not None and cnt >= seuil_plage:
        runs.append((start, last, cnt))
    if runs:
        for st, en, c in sorted(runs, key=lambda x: -x[2]):
            dur = (en - st).total_seconds() / 60
            print(f"  {c:>2} appels manqués d'affilée : {st:%a %d/%m %H:%M} → {en:%H:%M}  (~{dur:.0f} min)")
    else:
        print("  (aucune plage détectée)")

    print("\n[6] CRÉNEAUX SANS AGENT DISPONIBLE ('no_available_agent') — jour × heure")
    naa = target[target["reason_l"] == "no_available_agent"]
    if not naa.empty:
        print(pd.pivot_table(naa, index="Date", columns="Heure", values="answered",
                             aggfunc="size", fill_value=0).to_string())
    else:
        print("  (aucun)")

    print(f"\n[7] CLIENTS INSISTANTS (top {top} numéros par nombre d'appels)")
    t = target.groupby("FromNumber").agg(appels=("answered", "size"), repondus=("answered", "sum"))
    t["manques"] = t["appels"] - t["repondus"]
    t = t.sort_values("appels", ascending=False).head(top)
    print(t.to_string())
    n5 = t["appels"].head(5).sum()
    print(f"\n  Total entrants (scope) : {len(target)} | numéros uniques : {target['FromNumber'].nunique()}"
          f" | top 5 = {n5} appels ({100 * n5 / len(target):.0f}%)")

    print("\n[8] VOLUME QUOTIDIEN vs MOYENNE DES AUTRES SEMAINES")
    autres = scope[~scope.index.isin(target.index)]
    if not autres.empty:
        jours = ["Lun", "Mar", "Mer", "Jeu", "Ven"]
        target = target.assign(DOW=pd.to_datetime(target["StartTime"]).dt.dayofweek)
        autres = autres.assign(DOW=pd.to_datetime(autres["StartTime"]).dt.dayofweek)
        moy = autres.groupby("DOW").size() / autres["Semaine"].nunique()
        cur = target.groupby("DOW").size()
        comp = pd.DataFrame({"cible": cur, "moy_autres": moy.round(0)}).dropna(how="all")
        comp["ecart_%"] = (100 * (comp["cible"] / comp["moy_autres"] - 1)).round(0)
        comp.index = [jours[i] if i < len(jours) else str(i) for i in comp.index]
        print(comp.to_string())
    else:
        print("  (pas assez de semaines pour comparer)")
    print()


def main():
    p = argparse.ArgumentParser(description="Analyse des appels entrants / anomalies de taux de service.")
    p.add_argument("--dossier", default=DOSSIER_DEFAUT, help=f"Dossier des .xls Aircall (défaut: {DOSSIER_DEFAUT})")
    p.add_argument("--univers", default="stellair", help="stellair | affid | xmed | tmaj | tous (défaut: stellair)")
    p.add_argument("--semaine", help="Semaine cible : 2026-27, S2026-27 ou 202627")
    p.add_argument("--du", help="Début de période (YYYY-MM-DD)")
    p.add_argument("--au", help="Fin de période (YYYY-MM-DD)")
    p.add_argument("--top", type=int, default=12, help="Nombre de clients insistants à afficher (défaut: 12)")
    p.add_argument("--seuil-plage", type=int, default=4, help="Nb min d'appels manqués consécutifs pour une 'plage' (défaut: 4)")
    args = p.parse_args()

    if args.semaine:
        cible = {"type": "semaine", "valeur": normaliser_semaine(args.semaine)}
    elif args.du or args.au:
        if not (args.du and args.au):
            sys.exit("Précisez --du ET --au pour une plage de dates.")
        d1 = pd.to_datetime(args.du)
        d2 = pd.to_datetime(args.au) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
        cible = {"type": "dates", "valeur": (d1, d2)}
    else:
        cible = {"type": "derniere"}

    df = charger(args.dossier)
    analyser(df, args.univers, cible, args.top, args.seuil_plage)


if __name__ == "__main__":
    main()
