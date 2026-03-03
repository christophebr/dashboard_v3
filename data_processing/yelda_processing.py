"""
Traitement des données Yelda (chatbot Stellair).
- Charge les conversations depuis data/Affid/yelda/yelda.xlsx
- Filtre par URL d'origine (https://fse.stellair.fr uniquement)
- Identifie les tickets créés via Parcours contenant "creation_ticket_hubspot"
"""
import pandas as pd
import os

YELDA_DATA_PATH = os.getenv('YELDA_DATA_PATH', 'data/Affid/yelda/yelda.xlsx')

# Noms de colonnes (avec/sans accents selon l'Excel)
COL_PARCOURS = 'Parcours'
COL_URL = 'URL d\'origine'
COL_EVALUATION = 'Évaluation'
COL_EVALUATION_LLM = 'Évaluation LLM'
COL_SCORE_LLM = 'Score LLM'
COL_DATE = 'Date'
COL_ID_CONV = 'identifiant de la conversation'
COL_INTENTIONS = 'Intentions'
URL_FILTER_PREFIX = 'https://fse.stellair.fr'


def load_yelda_data(path=None):
    """
    Charge le fichier Excel Yelda.
    Returns: DataFrame ou None si fichier absent.
    """
    p = path or YELDA_DATA_PATH
    if not os.path.exists(p):
        return None
    try:
        df = pd.read_excel(p)
        df[COL_DATE] = pd.to_datetime(df[COL_DATE], errors='coerce')
        return df
    except Exception:
        return None


def filter_yelda_stellair(df_yelda):
    """
    Filtre les conversations Yelda pour ne garder que celles dont l'URL d'origine
    commence par https://fse.stellair.fr.
    """
    if df_yelda is None or df_yelda.empty:
        return pd.DataFrame()
    url_col = COL_URL if COL_URL in df_yelda.columns else None
    if not url_col:
        return df_yelda
    mask = df_yelda[url_col].astype(str).str.startswith(URL_FILTER_PREFIX, na=False)
    return df_yelda[mask].copy()


def filter_yelda_evaluated(df_yelda):
    """
    Ne garde que les conversations évaluées (Satisfait, Insatisfait, À revoir).
    Exclut les "Non évaluable" qui sont de simples ouvertures du chat sans question utilisateur.
    """
    if df_yelda is None or df_yelda.empty:
        return pd.DataFrame()
    eval_col = COL_EVALUATION if COL_EVALUATION in df_yelda.columns else None
    if not eval_col:
        return df_yelda
    s = df_yelda[eval_col].fillna('').astype(str).str.lower()
    mask = s.str.contains('satisfait') | s.str.contains('revoir')
    return df_yelda[mask].copy()


def has_ticket_created(parcours_value):
    """Retourne True si le parcours contient 'creation_ticket_hubspot'."""
    if pd.isna(parcours_value):
        return False
    return 'creation_ticket_hubspot' in str(parcours_value)


def compute_yelda_kpis(df_yelda_filtered):
    """
    Calcule les KPIs Yelda à partir du DataFrame filtré (fse.stellair.fr).
    
    Returns:
        dict avec:
        - nb_interactions: nombre de conversations évaluées uniquement
        - nb_tickets_crees: nombre de conversations ayant généré un ticket HubSpot
        - evaluation_counts: {Satisfait, Insatisfait, À revoir}
        - score_llm_moyen: moyenne du Score LLM (hors NaN)
        - evaluation_llm_counts: répartition Évaluation LLM
    """
    if df_yelda_filtered is None or df_yelda_filtered.empty:
        return {
            'nb_interactions': 0,
            'nb_tickets_crees': 0,
            'evaluation_counts': {'Satisfait': 0, 'Insatisfait': 0, 'À revoir': 0},
            'score_llm_moyen': 0.0,
            'evaluation_llm_counts': {},
            'intentions_satisfaisant': 0,
            'intentions_non_satisfaisant': 0,
            'intentions_sans_avis': 0,
        }
    
    df = df_yelda_filtered.copy()
    parcours_col = COL_PARCOURS if COL_PARCOURS in df.columns else None
    eval_col = COL_EVALUATION if COL_EVALUATION in df.columns else None
    score_col = COL_SCORE_LLM if COL_SCORE_LLM in df.columns else None
    eval_llm_col = COL_EVALUATION_LLM if COL_EVALUATION_LLM in df.columns else None
    
    nb_interactions = len(df)
    
    nb_tickets_crees = 0
    if parcours_col:
        nb_tickets_crees = df[parcours_col].apply(has_ticket_created).sum()
    
    evaluation_counts = {'Satisfait': 0, 'Insatisfait': 0, 'À revoir': 0}
    if eval_col:
        for val, cnt in df[eval_col].value_counts(dropna=False).items():
            s = str(val).strip().lower()
            if 'insatisfait' in s:
                evaluation_counts['Insatisfait'] += cnt
            elif 'satisfait' in s:
                evaluation_counts['Satisfait'] += cnt
            elif 'revoir' in s:
                evaluation_counts['À revoir'] += cnt
    
    score_llm_moyen = 0.0
    if score_col and score_col in df.columns:
        s = df[score_col].dropna()
        if len(s) > 0:
            score_llm_moyen = float(s.mean())
    
    evaluation_llm_counts = {}
    if eval_llm_col and eval_llm_col in df.columns:
        evaluation_llm_counts = df[eval_llm_col].value_counts(dropna=False).to_dict()
    
    intent_satisfaisant = 0
    intent_non_satisfaisant = 0
    if COL_INTENTIONS in df.columns:
        intents = df[COL_INTENTIONS].fillna('').astype(str).str.lower()
        has_non = intents.str.contains('reponse_agent_non_satisfaisante', na=False)
        has_sat = intents.str.contains('reponse_agent_satisfaisante', na=False) & ~has_non
        intent_non_satisfaisant = has_non.sum()
        intent_satisfaisant = has_sat.sum()

    # Sans avis : conversations évaluées sans reponse_agent_satisfaisante ni non_satisfaisante
    intent_sans_avis = nb_interactions - intent_satisfaisant - intent_non_satisfaisant

    return {
        'nb_interactions': nb_interactions,
        'nb_tickets_crees': int(nb_tickets_crees),
        'evaluation_counts': evaluation_counts,
        'score_llm_moyen': round(score_llm_moyen, 2),
        'evaluation_llm_counts': evaluation_llm_counts,
        'intentions_satisfaisant': int(intent_satisfaisant),
        'intentions_non_satisfaisant': int(intent_non_satisfaisant),
        'intentions_sans_avis': max(0, int(intent_sans_avis)),
    }


def filtrer_yelda_par_periode(df_yelda, periode):
    """
    Filtre les données Yelda par période.
    periode: même format que filtrer_par_periode (string ou tuple (date_debut, date_fin))
    """
    if df_yelda is None or df_yelda.empty:
        return pd.DataFrame()
    df = df_yelda.copy()
    df['Date'] = pd.to_datetime(df['Date'])
    derniere_date = df['Date'].max()
    if pd.isna(derniere_date):
        derniere_date = pd.Timestamp.now()

    if isinstance(periode, (tuple, list)) and len(periode) == 2:
        date_limite = pd.to_datetime(periode[0])
        date_max = pd.to_datetime(periode[1])
        return df[(df['Date'] >= date_limite) & (df['Date'] <= date_max)].copy()
    elif periode == "1 an":
        date_limite = derniere_date - pd.DateOffset(years=1)
    elif periode == "6 derniers mois":
        date_limite = derniere_date - pd.DateOffset(months=6)
    elif periode == "3 derniers mois":
        date_limite = derniere_date - pd.DateOffset(months=3)
    elif periode == "Dernier mois":
        date_limite = derniere_date - pd.DateOffset(months=1)
    else:
        return df
    return df[df['Date'] >= date_limite].copy()
