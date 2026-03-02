import streamlit as st
import pandas as pd
import os
import time
from config import AIRCALL_DATA_PATH_V1, AIRCALL_DATA_PATH_V2, AIRCALL_DATA_PATH_V3, HUBSPOT_TICKET_DATA_PATH, EVALUATION_DATA_PATH
from data_processing.hubspot_processing import load_hubspot_data, process_hubspot_data
from data_processing.aircall_processing import load_aircall_data, process_aircall_data
from concurrent.futures import ThreadPoolExecutor


def needs_update(source_paths, parquet_path):
    if not os.path.exists(parquet_path):
        return True
    parquet_mtime = os.path.getmtime(parquet_path)
    for path in source_paths:
        # Si c'est un dossier, vérifier tous les fichiers Excel à l'intérieur
        if os.path.isdir(path):
            excel_files = [os.path.join(path, f) for f in os.listdir(path) 
                          if f.endswith((".xls", ".xlsx")) and not f.startswith(".")]
            if excel_files:
                # Si un fichier Excel est plus récent que le cache, mettre à jour
                if any(os.path.getmtime(f) > parquet_mtime for f in excel_files):
                    return True
            else:
                # Si le dossier lui-même est plus récent, mettre à jour
                if os.path.getmtime(path) > parquet_mtime:
                    return True
        else:
            # Si c'est un fichier, comparer directement
            if os.path.getmtime(path) > parquet_mtime:
                return True
    return False

def read_excel_parallel(paths):
    with ThreadPoolExecutor() as executor:
        dfs = list(executor.map(lambda p: pd.read_excel(p, dtype=str), paths))
    return pd.concat(dfs, ignore_index=True)

def read_with_retry(file_path, max_retries=3, delay=1):
    """Lit un fichier Parquet avec mécanisme de retry."""
    for attempt in range(max_retries):
        try:
            return pd.read_parquet(file_path)
        except Exception as e:
            if attempt == max_retries - 1:  # Dernière tentative
                raise e
            time.sleep(delay * (attempt + 1))  # Délai exponentiel

@st.cache_data(ttl=3600)  # Cache pour 1 heure
def process_aircall_and_cache(aircall_v1_path, aircall_v2_path, aircall_v3_path=None, parquet_path=None):
    try:
        source_paths = [aircall_v1_path, aircall_v2_path]
        if aircall_v3_path:
            source_paths.append(aircall_v3_path)
        
        if parquet_path and needs_update(source_paths, parquet_path):
            print("Mise à jour des données Aircall nécessaire...")
            df_raw = load_aircall_data(aircall_v1_path, aircall_v2_path, aircall_v3_path)
            df_support = process_aircall_data(df_raw)
            
            # Créer le répertoire parent si nécessaire
            os.makedirs(os.path.dirname(parquet_path), exist_ok=True)
            
            # Sauvegarder avec compression snappy
            df_support.to_parquet(parquet_path, compression='snappy')
            print("✅ Données Aircall mises à jour et sauvegardées")
        elif parquet_path:
            print("Chargement des données Aircall depuis le cache...")
            df_support = read_with_retry(parquet_path)
            print("✅ Données Aircall chargées depuis le cache")
        else:
            # Pas de cache, charger directement
            df_raw = load_aircall_data(aircall_v1_path, aircall_v2_path, aircall_v3_path)
            df_support = process_aircall_data(df_raw)
        
        return df_support
    
    except Exception as e:
        print(f"❌ Erreur lors du traitement des données Aircall: {str(e)}")
        # En cas d'erreur, essayer de charger directement depuis les fichiers source
        df_raw = load_aircall_data(aircall_v1_path, aircall_v2_path, aircall_v3_path)
        return process_aircall_data(df_raw)

@st.cache_data(ttl=3600)  # Cache pour 1 heure
def process_hubspot_and_cache(hubspot_xls_path, parquet_path):
    try:
        if needs_update([hubspot_xls_path], parquet_path):
            print("Mise à jour des données Hubspot nécessaire...")
            df_raw = load_hubspot_data(hubspot_xls_path)
            df_tickets = process_hubspot_data(df_raw)

            # Colonnes à nettoyer avant export
            cols_to_cast = ["Associated Conversation IDs", "Associated Note IDs"]
            for col in cols_to_cast:
                if col in df_tickets.columns:
                    df_tickets[col] = df_tickets[col].fillna("").astype(str)

            # Créer le répertoire parent si nécessaire
            os.makedirs(os.path.dirname(parquet_path), exist_ok=True)
            
            # Sauvegarder avec compression snappy
            df_tickets.to_parquet(parquet_path, compression='snappy')
            print("✅ Données Hubspot mises à jour et sauvegardées")
        else:
            print("Chargement des données Hubspot depuis le cache...")
            df_tickets = read_with_retry(parquet_path)
            print("✅ Données Hubspot chargées depuis le cache")
        
        return df_tickets
    
    except Exception as e:
        print(f"❌ Erreur lors du traitement des données Hubspot: {str(e)}")
        # En cas d'erreur, essayer de charger directement depuis le fichier source
        df_raw = load_hubspot_data(hubspot_xls_path)
        return process_hubspot_data(df_raw)

def read_excel_and_convert_to_parquet(xls_path, parquet_path):
    try:
        if needs_update([xls_path], parquet_path):
            print("Mise à jour des données Excel nécessaire...")
            df = pd.read_excel(xls_path)
            
            # Créer le répertoire parent si nécessaire
            os.makedirs(os.path.dirname(parquet_path), exist_ok=True)
            
            df.to_parquet(parquet_path, compression='snappy')
            print("✅ Données Excel converties et sauvegardées")
        else:
            print("Chargement des données depuis le cache Parquet...")
            df = read_with_retry(parquet_path)
            print("✅ Données chargées depuis le cache")
        return df
    except Exception as e:
        print(f"❌ Erreur lors de la lecture/conversion du fichier Excel: {str(e)}")
        # En cas d'erreur, charger directement depuis Excel
        return pd.read_excel(xls_path)

@st.cache_data(ttl=3600)  # Cache pour 1 heure
def load_data():
    df_support = process_aircall_and_cache(
        AIRCALL_DATA_PATH_V1,
        AIRCALL_DATA_PATH_V2,
        AIRCALL_DATA_PATH_V3,
        "data/Affid/Cache/df_support.parquet"
    )

    df_tickets = process_hubspot_and_cache(
        HUBSPOT_TICKET_DATA_PATH,
        "data/Affid/Cache/df_tickets.parquet"
    )

    parquet_eval_path = EVALUATION_DATA_PATH.replace(".xls", ".parquet").replace(".xlsx", ".parquet")
    df_evaluation = read_excel_and_convert_to_parquet(EVALUATION_DATA_PATH, parquet_eval_path)

    return df_support, df_tickets, df_evaluation
