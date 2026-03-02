import pandas as pd
import os
import unicodedata
from datetime import datetime, timedelta
import numpy as np
import sqlite3
import hashlib
import pickle


def get_data_hash(data):
    """Calcule un hash des données pour détecter les changements"""
    return hashlib.md5(pd.util.hash_pandas_object(data).values).hexdigest()


def save_processed_data_to_cache(processed_data, cache_key, cache_path="data/Affid/Cache/processed_cache.pkl"):
    """Sauvegarde les données traitées avec leur hash"""
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    cache_data = {
        'data': processed_data,
        'hash': get_data_hash(processed_data),
        'timestamp': datetime.now()
    }
    with open(cache_path, 'wb') as f:
        pickle.dump(cache_data, f)


def load_processed_data_from_cache(cache_key, cache_path="data/Affid/Cache/processed_cache.pkl"):
    """Charge les données traitées depuis le cache"""
    try:
        if os.path.exists(cache_path):
            with open(cache_path, 'rb') as f:
                cache_data = pickle.load(f)
            return cache_data['data']
    except Exception as e:
        print(f"Erreur lors du chargement du cache: {e}")
    return None


def save_to_sqlite(df, table_name, db_path="data/Affid/Cache/cache.sqlite"):
    with sqlite3.connect(db_path) as conn:
        # Créer les index pour les colonnes fréquemment utilisées
        df.to_sql(table_name, conn, if_exists="replace", index=False)
        cursor = conn.cursor()
        cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_date ON {table_name}(Date)")
        cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_semaine ON {table_name}(Semaine)")
        cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_username ON {table_name}(UserName)")
        conn.commit()

def read_from_sqlite(table_name, db_path="data/Affid/Cache/cache.sqlite"):
    # Utiliser une seule connexion pour toute la session
    if not hasattr(read_from_sqlite, 'conn'):
        read_from_sqlite.conn = sqlite3.connect(db_path)
    
    df = pd.read_sql(f"SELECT * FROM {table_name}", read_from_sqlite.conn, 
                      parse_dates=['StartTime', 'Date', 'time (TZ offset incl.)', 'HangupTime'])
    
    # Normalisation de LastState pour corriger le problème avec les données Affid
    if 'LastState' in df.columns:
        def normalize_laststate(value):
            if isinstance(value, bool):
                return 'yes' if value else 'no'
            elif isinstance(value, str):
                return value
            else:
                return 'no'
        df['LastState'] = df['LastState'].apply(normalize_laststate)
    
    return df


def normalize_v3_data(df_v3):
    """
    Normalise les données du format V3 vers le format standard attendu.
    Le format V3 a 'datetime (tz offset incl.)' au lieu de 'date' et 'time' séparés.
    """
    df = df_v3.copy()
    
    # Normaliser les noms de colonnes (minuscules vers format standard)
    column_mapping = {
        'datetime (tz offset incl.)': 'datetime_combined',
        'datetime (utc)': 'datetime (UTC)',
        'ivr branch': 'IVR Branch',
    }
    
    # Renommer les colonnes si elles existent
    for old_col, new_col in column_mapping.items():
        if old_col in df.columns:
            df = df.rename(columns={old_col: new_col})
    
    # Si on a 'datetime_combined', le séparer en 'date' et 'time'
    if 'datetime_combined' in df.columns:
        # Convertir en datetime avec gestion des erreurs (errors='coerce' pour mettre NaT si invalide)
        df['datetime_combined'] = pd.to_datetime(df['datetime_combined'], errors='coerce')
        # Filtrer les lignes avec des dates valides
        valid_dates = df['datetime_combined'].notna()
        # Extraire la date et la formater en string (seulement pour les dates valides)
        df.loc[valid_dates, 'date (TZ offset incl.)'] = df.loc[valid_dates, 'datetime_combined'].dt.date.astype(str)
        # Extraire le temps et le formater en string au format HH:MM:SS (seulement pour les dates valides)
        df.loc[valid_dates, 'time (TZ offset incl.)'] = df.loc[valid_dates, 'datetime_combined'].dt.strftime('%H:%M:%S')
        # Pour les dates invalides, mettre des valeurs par défaut
        df.loc[~valid_dates, 'date (TZ offset incl.)'] = ''
        df.loc[~valid_dates, 'time (TZ offset incl.)'] = ''
        df = df.drop(columns=['datetime_combined'])
    
    # Ajouter la colonne 'via' si elle n'existe pas (peut être vide pour V3)
    if 'via' not in df.columns:
        df['via'] = ''
    
    # S'assurer que 'IVR Branch' existe (peut être en minuscules dans V3)
    if 'IVR Branch' not in df.columns and 'ivr branch' in df.columns:
        df['IVR Branch'] = df['ivr branch']
        df = df.drop(columns=['ivr branch'])
    elif 'IVR Branch' not in df.columns:
        df['IVR Branch'] = ''
    
    # Normaliser la colonne line (Excel peut exporter "Line" avec majuscule)
    if 'Line' in df.columns and 'line' not in df.columns:
        df = df.rename(columns={'Line': 'line'})
    
    return df


def detect_file_format(file_path):
    """
    Détecte le format d'un fichier Aircall en examinant ses colonnes.
    Retourne 'v1', 'v2', ou 'v3'
    """
    try:
        # Lire seulement la première ligne pour détecter les colonnes
        df_sample = pd.read_excel(file_path, nrows=1)
        columns = [col.lower() for col in df_sample.columns]
        
        # V3 a 'datetime (tz offset incl.)' en minuscules
        if 'datetime (tz offset incl.)' in columns:
            return 'v3'
        # V2 a 'IVR Branch' (avec majuscules)
        elif 'ivr branch' in [col for col in df_sample.columns]:
            return 'v2'
        # Sinon c'est V1
        else:
            return 'v1'
    except Exception as e:
        print(f"Erreur lors de la détection du format pour {file_path}: {e}")
        # Par défaut, supposer V1
        return 'v1'


def load_aircall_data(path_v1, path_v2, path_v3=None, force_reload=False, db_path="data/cache.sqlite"):
    table_name = "aircall_processed"
    
    # Vérifier d'abord le cache des données traitées
    if not force_reload:
        cached_data = load_processed_data_from_cache("aircall_processed")
        if cached_data is not None:
            print("✅ Données traitées chargées depuis le cache pickle")
            return cached_data
    
    # Vérifier le cache SQLite
    if not force_reload:
        try:
            df = read_from_sqlite(table_name, db_path)
            
            print("✅ Données chargées depuis SQLite")
            # Sauvegarder dans le cache pickle pour les prochaines fois
            save_processed_data_to_cache(df, "aircall_processed")
            return df
        except Exception as e:
            print("❌ Échec chargement cache SQLite :", e)

    # Sinon, traitement complet avec optimisations
    print("🔄 Traitement complet des données Aircall...")
    
    # Chargement parallèle des fichiers
    files_v1 = [file for file in os.listdir(path_v1) if not file.startswith('.')] if os.path.exists(path_v1) else []
    files_v2 = [file for file in os.listdir(path_v2) if not file.startswith('.')] if os.path.exists(path_v2) else []
    files_v3 = [file for file in os.listdir(path_v3) if not file.startswith('.')] if path_v3 and os.path.exists(path_v3) else []

    # Optimisation : charger seulement les colonnes nécessaires
    needed_columns_v2 = ['line', 'date (TZ offset incl.)', 'time (TZ offset incl.)', 'number timezone', 
                     'datetime (UTC)', 'country_code', 'direction', 'from', 'to', 'answered',
                     'missed_call_reason', 'user', 'duration (total)', 'duration (in call)', 
                     'via', 'voicemail', 'tags', 'IVR Branch']
    
    needed_columns_v1 = ['line', 'date (TZ offset incl.)', 'time (TZ offset incl.)', 'number timezone', 
                     'datetime (UTC)', 'country_code', 'direction', 'from', 'to', 'answered',
                     'missed_call_reason', 'user', 'duration (total)', 'duration (in call)', 
                     'via', 'voicemail', 'tags']
    
    # Colonnes pour V3 (format différent avec datetime unifié)
    needed_columns_v3 = ['line', 'datetime (tz offset incl.)', 'number timezone', 
                     'datetime (utc)', 'country_code', 'direction', 'from', 'to', 'answered',
                     'missed_call_reason', 'user', 'duration (total)', 'duration (in call)', 
                     'voicemail', 'tags', 'ivr branch']
    
    data_list = []
    
    # Charger les données V1
    if files_v1:
        try:
            data_v1 = pd.concat([pd.read_excel(os.path.join(path_v1, file), usecols=needed_columns_v1) 
                                for file in files_v1])
            data_v1['IVR Branch'] = ""
            data_list.append(data_v1)
            print(f"✅ {len(files_v1)} fichier(s) V1 chargé(s)")
        except Exception as e:
            print(f"⚠️ Erreur lors du chargement V1: {e}")
    
    # Charger les données V2
    if files_v2:
        try:
            data_v2 = pd.concat([pd.read_excel(os.path.join(path_v2, file), usecols=needed_columns_v2) 
                                for file in files_v2])
            data_list.append(data_v2)
            print(f"✅ {len(files_v2)} fichier(s) V2 chargé(s)")
        except Exception as e:
            print(f"⚠️ Erreur lors du chargement V2: {e}")
    
    # Charger les données V3
    if files_v3:
        try:
            # Pour V3, on charge toutes les colonnes disponibles puis on normalise
            data_v3_list = []
            for file in files_v3:
                df_file = pd.read_excel(os.path.join(path_v3, file))
                # Normaliser les données V3
                df_file = normalize_v3_data(df_file)
                data_v3_list.append(df_file)
            data_v3 = pd.concat(data_v3_list)
            data_list.append(data_v3)
            print(f"✅ {len(files_v3)} fichier(s) V3 chargé(s) et normalisé(s)")
        except Exception as e:
            print(f"⚠️ Erreur lors du chargement V3: {e}")
            import traceback
            traceback.print_exc()
    
    if not data_list:
        raise ValueError("Aucune donnée n'a pu être chargée depuis les dossiers spécifiés")
    
    # Concaténer toutes les données
    raw_data = pd.concat(data_list, ignore_index=True)
    
    # S'assurer que toutes les colonnes nécessaires sont présentes
    columns_order = ['line', 'date (TZ offset incl.)', 'time (TZ offset incl.)', 'number timezone', 'datetime (UTC)', 'country_code', 'direction', 'from',
                     'to', 'answered','missed_call_reason', 'user', 'duration (total)','duration (in call)', 'via', 'voicemail', 'tags', 'IVR Branch']
    
    # Ajouter les colonnes manquantes si nécessaire
    for col in columns_order:
        if col not in raw_data.columns:
            raw_data[col] = ""
    
    # Réorganiser les colonnes
    available_columns = [col for col in columns_order if col in raw_data.columns]
    raw_data = raw_data[available_columns]

    processed_data = process_aircall_data(raw_data)
    
    # Sauvegarder dans les deux caches
    save_to_sqlite(processed_data, table_name, db_path)
    save_processed_data_to_cache(processed_data, "aircall_processed")
    
    print("✅ Données traitées et sauvegardées dans SQLite et cache pickle")

    return processed_data


def process_aircall_data(data):
    # Copie pour éviter les modifications sur l'original
    data = data.copy()
    
    # Renommage des colonnes
    data.rename(columns={"answered": "LastState", 
                        'date (TZ offset incl.)': "StartTime", 
                        "duration (total)": "TotalDuration", 
                        "duration (in call)": "InCallDuration", 
                        "from": "FromNumber", "to": "ToNumber", 
                        "user": "UserName", 
                        "comments": "Note", 
                        "tags": "Tags", "missed_call_reason": "ScenarioName"}, inplace=True)
    
    # Optimisation : conversions de dates vectorisées
    data['time (TZ offset incl.)'] = pd.to_datetime(data['time (TZ offset incl.)'], format='%H:%M:%S', errors='coerce')
    data['StartTime'] = pd.to_datetime(data['StartTime'], errors='coerce')
    # Convertir InCallDuration en numérique, remplacer les valeurs invalides par 0
    data['InCallDuration'] = pd.to_numeric(data['InCallDuration'], errors='coerce').fillna(0)
    data['HangupTime'] = data['time (TZ offset incl.)'] + pd.to_timedelta(data['InCallDuration'], unit='s')
    
    # Calculs vectorisés
    data['Semaine'] = data['StartTime'].dt.strftime("S%Y-%V")
    data['Heure'] = data['time (TZ offset incl.)'].dt.hour
    data['Date'] = data['StartTime'].dt.normalize()
    data['Jour'] = data['StartTime'].dt.day_name()
    
    # Filtrage vectorisé
    weekend_mask = ~data["Jour"].isin(["Saturday", "Sunday"])
    scenario_mask = ~data["ScenarioName"].isin(["Fermé", "out_of_opening_hours", "abandoned_in_ivr", 'short_abandoned'])
    data = data[weekend_mask & scenario_mask]
    
    # Mapping vectorisé pour LastState
    state_mapping = {"ANSWERED": "yes", "VOICEMAIL": "no", "MISSED": "no", 
                    "VOICEMAIL_ANSWERED": "no", "BLIND_TRANSFERED": "no", 
                    "NOANSWER_TRANSFERED": "no", "FAILED": "no", "CANCELLED": "no", 
                    "QUEUE_TIMEOUT": "no", "yes": "yes", "no": "no", 
                    "Yes": "yes", "No": "no"}
    data['LastState'] = data['LastState'].map(state_mapping)
    
    # Optimisation : nettoyage des tags vectorisé
    data['Tags'] = data['Tags'].astype(str).str.replace('[^a-zA-Z-,]', '', regex=True)
    data['NRP'] = 'no'
    
    # Condition vectorisée pour NRP
    nrp_mask = (data['Tags'].isin(['NRP'])) & (data['direction'] == 'outbound')
    data.loc[nrp_mask, 'LastState'] = data.loc[nrp_mask, 'NRP']
    
    # Sélection des colonnes finales
    final_columns = ['line', 'Semaine', 'Date', 'Jour', 'Heure', 'direction', 'LastState', 
                    'ScenarioName', 'StartTime', 'HangupTime', 'time (TZ offset incl.)', 
                    'TotalDuration', 'InCallDuration', 'FromNumber', 'ToNumber', 
                    'UserName', 'Tags', 'IVR Branch']
    data = data[final_columns]
    
    # Remplacements vectorisés pour les noms d'utilisateurs
    data['UserName'] = data['UserName'].str.replace("Archimède KESSI", "Archimede KESSI")
    data['UserName'] = data['UserName'].str.replace("Olivier SAINTE-ROSE", "Olivier Sainte-Rose")
    # Normalisation des variantes de Cédeline DUVAL (liste explicite + matching souple pour tout variant)
    cedeline_variants = [
        ("C√©deline DUVAL", "Cédeline DUVAL"),
        ("CÃ©deline DUVAL", "Cédeline DUVAL"),
        ("cedeline duval", "Cédeline DUVAL"),
        ("Cedeline duval", "Cédeline DUVAL"),
        ("Cedeline Duval", "Cédeline DUVAL"),
        ("Cédeline Duval", "Cédeline DUVAL"),
        ("Cedeline DUVAL", "Cédeline DUVAL"),
        ("CÉDELINE DUVAL", "Cédeline DUVAL"),
        ("CÉDELINE Duval", "Cédeline DUVAL"),
    ]
    for old_val, new_val in cedeline_variants:
        data['UserName'] = data['UserName'].str.replace(old_val, new_val, regex=False)
    # Matching souple : tout UserName contenant "cedeline" et "duval" (insensible casse/accents) -> Cédeline DUVAL
    # Inclut C√©deline (√© = é avec encodage corrompu)
    def _normalize_cedeline(val):
        if pd.isna(val) or not isinstance(val, str):
            return val
        v = str(val).strip().lower()
        if '√©deline' in v or 'c√©deline' in v:  # encodage corrompu de Cédeline
            if 'duval' in v:
                return "Cédeline DUVAL"
        v_norm = ''.join(c for c in unicodedata.normalize('NFD', v) if unicodedata.category(c) != 'Mn')
        if 'cedeline' in v_norm and 'duval' in v_norm:
            return "Cédeline DUVAL"
        return val
    data['UserName'] = data['UserName'].apply(_normalize_cedeline)
    
    # Filtrage par date vectorisé - 2 ans de données historiques
    # Permet d'inclure les données depuis 2023 et début 2024
    today = pd.Timestamp.today()
    week_prior = today - pd.Timedelta(weeks=104)  # 2 ans = 104 semaines
    data = data[data['Date'] >= week_prior]
    
    # Tri final
    data = data.sort_values(by='Semaine', ascending=True)
    
    return data


agents = [
        'Mourad HUMBLOT', 
        'Pierre GOUPILLON',
        'Frederic SAUVAN', 
        'Christophe Brichet']

frederic = ['Frederic SAUVAN']

agents_support = [
                'Mourad HUMBLOT', 
                'Pierre GOUPILLON', 
                'Archimede KESSI', 
                'Frederic SAUVAN', 
                'Christophe Brichet']

agents_armatis = ['Melinda Marmin', 
                'Sandrine Sauvage', 
                'Emilie GEST', 
                'Morgane Vandenbussche']

agents_all = [ 'Melinda Marmin',
                'Sandrine Sauvage', 
                'Emilie GEST', 
                'Morgane Vandenbussche',
                'Mourad HUMBLOT', 
                'Pierre GOUPILLON', 
                'Archimede KESSI', 
                'Frederic SAUVAN', 
                'Christophe Brichet',
                'Celine Crendal',
                'Cédeline DUVAL']


line_support = 'technique'
line_armatis = 'armatistechnique'
line_xmed = 'xmed'
line_tmaj = 'supporthardware'  # Support Hardware (data_v3, à partir du 3 février)
line_tous = 'tous'


def def_df_support(df_entrant, df_sortant, line, liste_agents):
    def clean_string(s):
        return ''.join(s.split()).lower()

    # S'assurer que les dates sont au bon format
    df_entrant = df_entrant.copy()
    df_sortant = df_sortant.copy()
    
    df_entrant['Date'] = pd.to_datetime(df_entrant['Date']).dt.normalize()
    df_sortant['Date'] = pd.to_datetime(df_sortant['Date']).dt.normalize()

    df_entrant['line'] = df_entrant['line'].apply(clean_string)
    df_sortant['line'] = df_sortant['line'].apply(clean_string)

    # Filtrage vectorisé
    if line == "tous":
        entrant_mask = (df_entrant['line'].isin(['technique', 'armatistechnique', 'xmed', 'supporthardware'])) & (df_entrant['direction'] == 'inbound')
        df_entrant = df_entrant[entrant_mask]
    elif line in ['technique', 'armatistechnique', 'xmed', 'supporthardware']:
        entrant_mask = (df_entrant['line'] == line) & (df_entrant['direction'] == 'inbound')
        df_entrant = df_entrant[entrant_mask]

    sortant_mask = (df_sortant['UserName'].isin(liste_agents)) & (df_sortant['direction'] == 'outbound')
    df_sortant = df_sortant[sortant_mask]

    df_entrant['Number'] = df_entrant['FromNumber']
    df_sortant['Number'] = df_sortant['ToNumber']

    df = pd.concat([df_entrant, df_sortant])

    # Filtrage vectorisé
    weekend_mask = ~df["Jour"].isin(["Saturday", "Sunday"])
    user_mask = ~df["UserName"].isin(["Vincent Gourvat", "Thierry CAROFF", 'Armatis Agent 1'])
    df = df[weekend_mask & user_mask]

    # Calculs vectorisés
    df['Count'] = 1
    df['Entrant_connect'] = ((df['LastState'] == 'yes') & (df['direction'] == 'inbound')).astype(int)
    df['Entrant'] = (df['direction'] == 'inbound').astype(int)
    df['Sortant_connect'] = ((df['direction'] == 'outbound') & (df['InCallDuration'] > 60)).astype(int)
    df['Taux_de_service'] = df['Entrant_connect'] / df['Entrant']
    
    df["Mois"] = df['StartTime'].dt.strftime("%Y-%m")

    # Optimisation : calcul de l'effectif avec groupby vectorisé
    df_grouped = df.groupby(['Date', 'UserName']).size().reset_index(name='TotalAppels')
    df_grouped['Actif'] = (df_grouped['TotalAppels'] >= 2).astype(int)

    # Calculer l'effectif moyen par jour
    df_effectif = df_grouped.groupby('Date')['Actif'].sum().reset_index()
    df_effectif.rename(columns={'Actif': 'Effectif'}, inplace=True)

    # Fusionner l'effectif avec le DataFrame principal
    df = pd.merge(df, df_effectif, on='Date', how='left')

    # Optimisation : fonction vectorisée pour get_ivr_or_tags_transformed
    def get_ivr_or_tags_transformed(row):
            """
            Retourne la valeur de 'IVR Branch' si elle est renseignée,
            sinon 'Stellair' si 'line' est égale à 'armatistechnique',
            sinon transforme les 3 premiers caractères de 'Tags' :
            - 'STE' -> 'Stellair'
            - 'AFD' -> 'Affid'

            Args:
                row (pd.Series): Une ligne du DataFrame.

            Returns:
                str: La valeur de 'IVR Branch', 'Stellair', ou la transformation de 'Tags'.
            """
            if pd.notna(row['IVR Branch']) and row['IVR Branch'].strip():
                return row['IVR Branch']
            elif row['line'] == 'armatistechnique':
                return 'Stellair'
            else:
                tags_prefix = row['Tags'][:3].upper() if pd.notna(row['Tags']) else ''
                if tags_prefix == 'STE':
                    return 'Stellair'
                elif tags_prefix == 'AFD':
                    return 'Affid'
                else:
                    return 'Inconnu'  # Retourne 'Inconnu' si aucun préfixe ne correspond

        # Exemple d'utilisation sur un DataFrame
    df['Logiciel'] = df.apply(get_ivr_or_tags_transformed, axis=1)

    return df
