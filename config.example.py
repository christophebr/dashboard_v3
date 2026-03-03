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
def _strip_env_quotes(s):
    if s and isinstance(s, str):
        s = s.strip()
        if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
            return s[1:-1]
    return s or ''

_cookie_raw = os.getenv('COOKIE_KEY', 'Changez-moi-en-production')
COOKIE_KEY = _strip_env_quotes(_cookie_raw) if _cookie_raw else 'Changez-moi-en-production'

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
    # Mode déploiement : Railway/Render (os.getenv) ou Streamlit Cloud (st.secrets)
    import bcrypt
    def _hash_password(pwd: str) -> str:
        return bcrypt.hashpw(pwd.encode(), bcrypt.gensalt()).decode()

    def _is_bcrypt_hash(s: str) -> bool:
        import re
        return bool(re.match(r'^\$2[aby]\$\d+\$.{53}$', str(s)))

    CREDENTIALS = None

    # 1. Essayer Streamlit secrets (format: [users.cbri] name="...", password="..."
    try:
        import streamlit as st
        users_sec = getattr(st.secrets, 'users', None) or st.secrets.get('users', None) if hasattr(st, 'secrets') else None
        if users_sec:
            usernames = {}
            for username in users_sec:
                data = users_sec[username]
                name = data.get('name', username) if hasattr(data, 'get') else getattr(data, 'name', username)
                pwd = data.get('password', '') if hasattr(data, 'get') else getattr(data, 'password', '')
                if pwd:
                    hashed = pwd if _is_bcrypt_hash(str(pwd)) else _hash_password(str(pwd))
                    usernames[str(username)] = {'name': str(name), 'password': hashed}
            if usernames:
                CREDENTIALS = {'usernames': usernames}
    except Exception:
        pass

    # 2. Sinon variables d'environnement ou secrets Streamlit ADMIN_*
    if CREDENTIALS is None:
        def _secret(key, default=''):
            try:
                import streamlit as _st
                if hasattr(_st, 'secrets') and _st.secrets:
                    v = getattr(_st.secrets, key, None)
                    return _strip_env_quotes(str(v)) if v else default
            except Exception:
                pass
            return default

        def _env(key, default=''):
            v = os.getenv(key)
            return _strip_env_quotes(str(v)) if v else default

        usernames = {}

        # 1. Toujours d'abord ADMIN_USERNAME + ADMIN_PASSWORD (le plus fiable sur Railway)
        admin_username = _env('ADMIN_USERNAME') or _secret('ADMIN_USERNAME') or ''
        admin_password = _env('ADMIN_PASSWORD') or _secret('ADMIN_PASSWORD') or ''
        admin_name = _env('ADMIN_NAME') or _secret('ADMIN_NAME') or 'Administrateur'
        if admin_username and admin_password:
            usernames[admin_username] = {'name': admin_name or admin_username, 'password': _hash_password(admin_password)}

        # 2. ADMIN_USERNAME_2 + ADMIN_PASSWORD_2 pour un 2e utilisateur
        admin_username_2 = _env('ADMIN_USERNAME_2') or _secret('ADMIN_USERNAME_2') or ''
        admin_password_2 = _env('ADMIN_PASSWORD_2') or _secret('ADMIN_PASSWORD_2') or ''
        admin_name_2 = _env('ADMIN_NAME_2') or _secret('ADMIN_NAME_2') or admin_username_2
        if admin_username_2 and admin_password_2:
            usernames[admin_username_2] = {'name': admin_name_2 or admin_username_2, 'password': _hash_password(admin_password_2)}

        # 3. ADMIN_USERS (format user:pass:nom;user2:pass2:nom2) - ajoute des utilisateurs
        admin_users_raw = _env('ADMIN_USERS') or _secret('ADMIN_USERS') or ''
        for part in admin_users_raw.replace(',', ';').split(';'):
            part = part.strip()
            if not part:
                continue
            elts = part.split(':', 2)
            if len(elts) >= 2 and elts[0] and elts[1]:
                u, p = elts[0].strip(), elts[1].strip()
                n = elts[2].strip() if len(elts) > 2 else u
                if u and p:
                    usernames[u] = {'name': n or u, 'password': _hash_password(p)}

        if usernames:
            CREDENTIALS = {'usernames': usernames}
        else:
            CREDENTIALS = {'usernames': {'admin': {'name': 'Admin', 'password': _hash_password('admin')}}}

# MCP Analyst
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', None)
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', None)
MCP_PROVIDER = os.getenv('MCP_PROVIDER', 'anthropic')
MCP_MODEL = os.getenv('MCP_MODEL', 'claude-sonnet-4-20250514')
