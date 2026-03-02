"""
Configuration exemple pour le déploiement.
Copiez ce fichier vers config.py et configurez les variables d'environnement.

Variables d'environnement requises pour le déploiement :
- COOKIE_KEY : Clé secrète pour les cookies (générer une clé aléatoire)
- ADMIN_USERNAME : Identifiant de l'administrateur (ex: admin)
- ADMIN_PASSWORD : Mot de passe en clair (sera haché automatiquement)
- ADMIN_NAME : Nom affiché (ex: Administrateur)
- ANTHROPIC_API_KEY : (optionnel) Clé API Anthropic pour l'Analyste IA
"""
import os
from pathlib import Path
import pickle

# Chemins des fichiers de données (relatifs à la racine du projet)
AIRCALL_DATA_PATH_V1 = os.getenv('AIRCALL_DATA_PATH_V1', 'data/Affid/Aircall/data_v1')
AIRCALL_DATA_PATH_V2 = os.getenv('AIRCALL_DATA_PATH_V2', 'data/Affid/Aircall/data_v2')
AIRCALL_DATA_PATH_V3 = os.getenv('AIRCALL_DATA_PATH_V3', 'data/Affid/Aircall/data_v3')
HUBSPOT_TICKET_DATA_PATH = os.getenv('HUBSPOT_TICKET_PATH', 'data/Affid/Hubspot/ticket')
HUBSPOT_AGENT_DATA_PATH = os.getenv('HUBSPOT_AGENT_PATH', 'data/Affid/Hubspot/agent')
EVALUATION_DATA_PATH = os.getenv('EVALUATION_DATA_PATH', 'data/Affid/Evaluation/support_notes_filtered.xlsx')
YELDA_DATA_PATH = os.getenv('YELDA_DATA_PATH', 'data/Affid/yelda/yelda.xlsx')

MODEL_PATH = 'models/random_forest_model.pkl'
TFIDF_PATH = 'models/tfidf_vectorizer.pkl'

CACHE_PATH = 'data/Affid/Cache'
SQLITE_CACHE_PATH = f'{CACHE_PATH}/cache.sqlite'
PICKLE_CACHE_PATH = f'{CACHE_PATH}/processed_cache.pkl'
HUBSPOT_CACHE_PATH = f'{CACHE_PATH}/data_cache.db'

ENABLE_CACHE = True
ENABLE_VECTORIZATION = True
ENABLE_PARALLEL_PROCESSING = False

# Authentification : hashed_pw.pkl ou variables d'environnement
COOKIE_KEY = os.getenv('COOKIE_KEY', 'Changez-moi-en-production')

try:
    file_path = Path(__file__).parent / 'hashed_pw.pkl'
    with file_path.open('rb') as file:
        hashed_passwords = pickle.load(file)
    CREDENTIALS = {
        'usernames': {
            'cbri': {'name': 'Christophe Bri', 'password': hashed_passwords.get('cbri')},
            'mpec': {'name': 'Mourad Pec', 'password': hashed_passwords.get('mpec')},
            'elap': {'name': 'Emilie Lap', 'password': hashed_passwords.get('elap')},
            'pgou': {'name': 'Pierre Gou', 'password': hashed_passwords.get('pgou')},
            'osai': {'name': 'Olivier Sai', 'password': hashed_passwords.get('osai')},
            'fsau': {'name': 'Frédéric Sau', 'password': hashed_passwords.get('fsau')},
            'mhum': {'name': 'Morgane Hum', 'password': hashed_passwords.get('mhum')},
            'akes': {'name': 'Archimède Kes', 'password': hashed_passwords.get('akes')},
            'dlau': {'name': 'David Lau', 'password': hashed_passwords.get('dlau')},
            'jdel': {'name': 'Jean Del', 'password': hashed_passwords.get('jdel')},
        }
    }
except FileNotFoundError:
    # Mode déploiement : créer un utilisateur admin depuis les variables d'environnement
    import streamlit_authenticator as stauth
    admin_username = os.getenv('ADMIN_USERNAME', 'admin')
    admin_password = os.getenv('ADMIN_PASSWORD', '')
    admin_name = os.getenv('ADMIN_NAME', 'Administrateur')
    
    if admin_password:
        hashed = stauth.Hasher.hash(admin_password)
        CREDENTIALS = {
            'usernames': {admin_username: {'name': admin_name, 'password': hashed}}
        }
    else:
        # Fallback minimal si aucune config (éviter crash au démarrage)
        CREDENTIALS = {
            'usernames': {'admin': {'name': 'Admin', 'password': stauth.Hasher.hash('admin')}}
        }

# MCP Analyst
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', None)
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', None)
MCP_PROVIDER = os.getenv('MCP_PROVIDER', 'anthropic')
MCP_MODEL = os.getenv('MCP_MODEL', 'claude-sonnet-4-20250514')
