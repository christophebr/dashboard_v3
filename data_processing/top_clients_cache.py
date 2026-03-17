"""
Cache SQLite pour la liste des clients à fort volume (top_clients_stellair)
et les métriques de concentration. Évite les recalculs et les timeouts (OneDrive).
"""
import sqlite3
import pandas as pd
import os
import json
from datetime import datetime

try:
    from config import SQLITE_CACHE_PATH
except ImportError:
    SQLITE_CACHE_PATH = 'data/Affid/Cache/cache.sqlite'

TABLE_NAME = 'top_clients_stellair'
TABLE_METRICS = 'metrics_concentration_stellair'


def _get_db_path():
    """Chemin DB avec fallback si config non chargée."""
    try:
        from config import SQLITE_CACHE_PATH as p
        return p
    except Exception:
        return 'data/Affid/Cache/cache.sqlite'


def _ensure_table(conn):
    """Crée les tables si elles n'existent pas."""
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
            cache_key TEXT PRIMARY KEY,
            top_appels_json TEXT,
            top_tickets_json TEXT,
            updated_at TEXT
        )
    """)
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE_METRICS} (
            period_key TEXT PRIMARY KEY,
            metrics_json TEXT,
            updated_at TEXT
        )
    """)


def _make_cache_key(period_str, seuil_min):
    """Clé unique pour le cache."""
    return f"{period_str}|{seuil_min}"


def save_top_clients_stellair(period_str, seuil_min, top_appels_df, top_tickets_df):
    """
    Stocke les listes top clients en BDD.
    """
    db_path = _get_db_path()
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    key = _make_cache_key(period_str, seuil_min)
    appels_json = top_appels_df.to_json(orient='records', date_format='iso', force_ascii=False) if top_appels_df is not None and not top_appels_df.empty else None
    tickets_json = top_tickets_df.to_json(orient='records', date_format='iso', force_ascii=False) if top_tickets_df is not None and not top_tickets_df.empty else None
    try:
        with sqlite3.connect(db_path) as conn:
            _ensure_table(conn)
            conn.execute(
                f"INSERT OR REPLACE INTO {TABLE_NAME} (cache_key, top_appels_json, top_tickets_json, updated_at) VALUES (?, ?, ?, ?)",
                (key, appels_json, tickets_json, datetime.now().isoformat())
            )
    except Exception:
        pass  # Silencieux en cas d'erreur disque


def load_top_clients_stellair(period_str, seuil_min):
    """
    Charge les listes top clients depuis la BDD.
    Returns: dict avec 'top_appels' et 'top_tickets' (DataFrames ou None) si trouvé, sinon None.
    """
    db_path = _get_db_path()
    if not os.path.exists(db_path):
        return None
    key = _make_cache_key(period_str, seuil_min)
    try:
        with sqlite3.connect(db_path, timeout=5) as conn:
            row = conn.execute(
                f"SELECT top_appels_json, top_tickets_json FROM {TABLE_NAME} WHERE cache_key = ?",
                (key,)
            ).fetchone()
        if row is None:
            return None
        appels_json, tickets_json = row
        result = {'top_appels': None, 'top_tickets': None}
        if appels_json:
            result['top_appels'] = pd.read_json(appels_json, orient='records')
        if tickets_json:
            result['top_tickets'] = pd.read_json(tickets_json, orient='records')
        return result
    except Exception:
        return None


def _serialize_metrics(metrics):
    """Sérialise les métriques de concentration pour stockage."""
    if not metrics:
        return None
    out = {}
    for k in ('appels', 'tickets'):
        m = metrics.get(k)
        if m is None:
            continue
        out[k] = {kk: vv for kk, vv in m.items() if kk not in ('pareto_data', 'distribution')}
        if m.get('pareto_data') is not None:
            out[k]['pareto_data'] = m['pareto_data'].to_json(orient='records', date_format='iso', force_ascii=False)
        if m.get('distribution') is not None:
            out[k]['distribution'] = m['distribution'].to_json()
    return json.dumps(out, ensure_ascii=False)


def _deserialize_metrics(metrics_json):
    """Désérialise les métriques depuis le cache."""
    if not metrics_json:
        return None
    try:
        out = json.loads(metrics_json)
        result = {}
        for k in ('appels', 'tickets'):
            if k not in out:
                continue
            m = dict(out[k])
            if 'pareto_data' in m:
                m['pareto_data'] = pd.read_json(m['pareto_data'], orient='records')
            if 'distribution' in m:
                d = json.loads(m['distribution']) if isinstance(m['distribution'], str) else m['distribution']
                m['distribution'] = pd.Series({int(k): v for k, v in d.items()}) if isinstance(d, dict) else pd.Series(d)
            result[k] = m
        return result if result else None
    except Exception:
        return None


def save_metrics_concentration(period_str, metrics):
    """Stocke les métriques de concentration en BDD."""
    db_path = _get_db_path()
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    payload = _serialize_metrics(metrics)
    if not payload:
        return
    try:
        with sqlite3.connect(db_path, timeout=10) as conn:
            _ensure_table(conn)
            conn.execute(
                f"INSERT OR REPLACE INTO {TABLE_METRICS} (period_key, metrics_json, updated_at) VALUES (?, ?, ?)",
                (period_str, payload, datetime.now().isoformat())
            )
    except Exception:
        pass


def load_metrics_concentration(period_str):
    """Charge les métriques de concentration depuis la BDD."""
    db_path = _get_db_path()
    if not os.path.exists(db_path):
        return None
    try:
        with sqlite3.connect(db_path, timeout=5) as conn:
            row = conn.execute(
                f"SELECT metrics_json FROM {TABLE_METRICS} WHERE period_key = ?",
                (period_str,)
            ).fetchone()
        return _deserialize_metrics(row[0]) if row else None
    except Exception:
        return None


def clear_top_clients_cache():
    """Vide le cache top_clients et métriques (appelé au rechargement des données)."""
    db_path = _get_db_path()
    if not os.path.exists(db_path):
        return
    try:
        with sqlite3.connect(db_path, timeout=10) as conn:
            conn.execute(f"DELETE FROM {TABLE_NAME}")
            conn.execute(f"DELETE FROM {TABLE_METRICS}")
    except Exception:
        pass
