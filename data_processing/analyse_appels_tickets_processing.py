"""
Traitement des données d'analyse d'appels et tickets (échantillon 30%).
Charge les données depuis data/Affid/analyse_appels_tickets/dashboard_support_stellair.xlsx
Onglets : Données, Synthèse globale, Synthèse dernier mois, Synthèse par secteur
"""
import pandas as pd
import os
import re

ANALYSE_APPELS_TICKETS_PATH = os.getenv(
    'ANALYSE_APPELS_TICKETS_PATH',
    'data/Affid/analyse_appels_tickets/dashboard_support_stellair.xlsx'
)


def load_analyse_appels_tickets(path=None):
    """
    Charge le fichier Excel d'analyse des appels et tickets.
    Returns: dict avec les clés suivantes ou None si fichier absent :
        - 'donnees': DataFrame des données brutes
        - 'synthese_globale': dict avec appels_analyses, tickets_analyses, total, repartition_secteurs
        - 'synthese_dernier_mois': dict idem pour le dernier mois
        - 'synthese_par_secteur': list of dict [{secteur, nb, pct, synthese_textuelle}, ...]
    """
    p = path or ANALYSE_APPELS_TICKETS_PATH
    if not os.path.exists(p):
        return None
    try:
        xl = pd.ExcelFile(p)
        result = {}

        # Données brutes
        if 'Données' in xl.sheet_names:
            result['donnees'] = pd.read_excel(xl, sheet_name='Données')

        # Synthèse globale
        if 'Synthèse globale' in xl.sheet_names:
            df_glob = pd.read_excel(xl, sheet_name='Synthèse globale', header=None)
            result['synthese_globale'] = _parse_synthese(df_glob)

        # Synthèse dernier mois
        if 'Synthèse dernier mois' in xl.sheet_names:
            df_mois = pd.read_excel(xl, sheet_name='Synthèse dernier mois', header=None)
            result['synthese_dernier_mois'] = _parse_synthese(df_mois)

        # Synthèse par secteur (dernier mois - synthèses textuelles par catégorie)
        if 'Synthèse par secteur' in xl.sheet_names:
            df_sect = pd.read_excel(xl, sheet_name='Synthèse par secteur')
            result['synthese_par_secteur'] = _parse_synthese_par_secteur(df_sect)

        return result if result else None
    except Exception:
        return None


def _parse_synthese(df):
    """
    Parse un onglet Synthèse (globale ou dernier mois).
    df: DataFrame avec colonnes 0 (label) et 1 (valeur)
    """
    res = {
        'appels_analyses': None,
        'tickets_analyses': None,
        'total': None,
        'repartition_secteurs': []  # list of {secteur, nb, pct}
    }
    if df is None or df.empty:
        return res
    col0 = df.iloc[:, 0].astype(str).str.strip()
    col1 = df.iloc[:, 1].astype(str) if df.shape[1] > 1 else pd.Series([''] * len(df))

    for i in range(len(df)):
        label = col0.iloc[i] if i < len(col0) else ''
        val = col1.iloc[i] if i < len(col1) else ''
        if pd.isna(label) or label == 'nan':
            continue
        label_lower = label.lower()
        if 'appels analysés' in label_lower or 'appels analysés (dernier mois)' in label_lower:
            try:
                res['appels_analyses'] = int(re.sub(r'[^\d]', '', str(val)) or 0)
            except ValueError:
                res['appels_analyses'] = 0
        elif 'tickets analysés' in label_lower or 'tickets analysés (dernier mois)' in label_lower:
            try:
                res['tickets_analyses'] = int(re.sub(r'[^\d]', '', str(val)) or 0)
            except ValueError:
                res['tickets_analyses'] = 0
        elif 'total analysé' in label_lower:
            try:
                res['total'] = int(re.sub(r'[^\d]', '', str(val)) or 0)
            except ValueError:
                res['total'] = 0
        elif 'répartition par secteur' in label_lower:
            continue
        elif val and val != 'nan' and '(' in str(val) and '%' in str(val):
            # ligne type "Lecteurs Stellair  42 (42 %)"
            match = re.match(r'^(\d+)\s*\(\s*(\d+)\s*%\s*\)', str(val).strip())
            if match:
                nb, pct = int(match.group(1)), int(match.group(2))
                res['repartition_secteurs'].append({'secteur': label, 'nb': nb, 'pct': pct})
            else:
                res['repartition_secteurs'].append({'secteur': label, 'nb': None, 'pct': None, 'raw': val})
    # Total = appels + tickets si non renseigné
    if res['total'] is None and res['appels_analyses'] is not None and res['tickets_analyses'] is not None:
        res['total'] = res['appels_analyses'] + res['tickets_analyses']
    return res


def _parse_synthese_par_secteur(df):
    """
    Parse l'onglet Synthèse par secteur.
    Colonnes : Secteur, Nb, %, Synthèse textuelle
    """
    result = []
    if df is None or df.empty:
        return result
    # Chercher la ligne d'en-tête (Secteur, Nb, %)
    for idx in range(len(df)):
        row = df.iloc[idx]
        vals = [str(v).strip() for v in row if pd.notna(v)]
        if 'Secteur' in vals and 'Nb' in vals:
            # En-tête trouvé, les lignes suivantes sont les données
            col_secteur = row.index[0] if len(row.index) > 0 else None
            col_nb = row.index[1] if len(row.index) > 1 else None
            col_pct = row.index[2] if len(row.index) > 2 else None
            col_synthese = row.index[3] if len(row.index) > 3 else None
            for j in range(idx + 1, len(df)):
                r = df.iloc[j]
                secteur = str(r[col_secteur]).strip() if col_secteur is not None and pd.notna(r.get(col_secteur, r.iloc[0] if len(r) > 0 else '')) else ''
                nb_val = r[col_nb] if col_nb is not None else r.iloc[1] if len(r) > 1 else None
                pct_val = r[col_pct] if col_pct is not None else r.iloc[2] if len(r) > 2 else None
                synthese = r[col_synthese] if col_synthese is not None else r.iloc[3] if len(r) > 3 else None
                if not secteur or secteur == 'nan':
                    continue
                try:
                    nb = int(nb_val) if pd.notna(nb_val) and str(nb_val).replace(' ', '').isdigit() else None
                except (ValueError, TypeError):
                    nb = None
                pct_str = str(pct_val) if pd.notna(pct_val) else ''
                pct = None
                if '%' in pct_str:
                    m = re.search(r'(\d+)\s*%', pct_str)
                    if m:
                        pct = int(m.group(1))
                result.append({
                    'secteur': secteur,
                    'nb': nb,
                    'pct': pct,
                    'synthese_textuelle': str(synthese).strip() if pd.notna(synthese) and str(synthese) != 'nan' else ''
                })
            break
        # Format alternatif : colonnes Unnamed avec structure connue
        if idx >= 1 and len(row) >= 4:
            secteur = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ''
            nb_val = row.iloc[1]
            pct_val = row.iloc[2]
            synthese = row.iloc[3] if len(row) > 3 else ''
            if secteur and secteur != 'nan' and not secteur.lower().startswith('secteur'):
                try:
                    nb = int(nb_val) if pd.notna(nb_val) and str(nb_val).replace(' ', '').replace('.0', '').isdigit() else int(float(nb_val)) if pd.notna(nb_val) else None
                except (ValueError, TypeError):
                    nb = None
                pct_str = str(pct_val) if pd.notna(pct_val) else ''
                pct = None
                if '%' in pct_str:
                    m = re.search(r'(\d+)\s*%', pct_str)
                    if m:
                        pct = int(m.group(1))
                syn_text = str(synthese).strip() if pd.notna(synthese) and str(synthese) != 'nan' else ''
                if secteur or syn_text:
                    result.append({'secteur': secteur, 'nb': nb, 'pct': pct, 'synthese_textuelle': syn_text})
    # Si result vide, parser manuellement avec les noms de colonnes réels
    if not result and len(df) > 2:
        c0, c1, c2, c3 = df.columns[0], df.columns[1], df.columns[2], df.columns[3] if len(df.columns) > 3 else None
        for idx, row in df.iterrows():
            if idx < 2:
                continue
            secteur = str(row[c0]).strip() if pd.notna(row[c0]) else ''
            if not secteur or secteur == 'nan' or 'secteur' in secteur.lower():
                continue
            try:
                nb = int(row[c1]) if pd.notna(row[c1]) else None
            except (ValueError, TypeError):
                nb = None
            pct_str = str(row[c2]) if pd.notna(row[c2]) else ''
            pct = None
            if '%' in pct_str:
                m = re.search(r'(\d+)\s*%', pct_str)
                if m:
                    pct = int(m.group(1))
            syn = str(row[c3]).strip() if c3 and pd.notna(row.get(c3, '')) else ''
            result.append({'secteur': secteur, 'nb': nb, 'pct': pct, 'synthese_textuelle': syn})
    return result
