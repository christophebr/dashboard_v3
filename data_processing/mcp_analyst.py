"""
Module MCP Analyst - Analyse de données avec LLM cloud
Permet d'interroger les bases SQLite locales en langage naturel via OpenAI/Anthropic
"""

import sqlite3
import os
import pandas as pd
from typing import Optional, Dict, List, Tuple
import json
from datetime import datetime

# Import conditionnel des clients LLM
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


class MCPAnalyst:
    """
    Analyste de données utilisant MCP (Model Context Protocol) avec LLM cloud.
    Interroge les bases SQLite locales en langage naturel.
    """
    
    def __init__(
        self,
        provider: str = "openai",
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        hubspot_db_path: str = "data/Cache/data_cache.db",
        aircall_db_path: str = "data/cache.sqlite"  # Chemin corrigé : données Aircall sont ici
    ):
        """
        Initialise l'analyste MCP.
        
        Args:
            provider: "openai" ou "anthropic"
            api_key: Clé API pour le LLM (si None, cherche dans les variables d'environnement)
            model: Modèle à utiliser (par défaut selon le provider)
            hubspot_db_path: Chemin vers la base SQLite Hubspot
            aircall_db_path: Chemin vers la base SQLite Aircall
        """
        self.provider = provider.lower()
        self.hubspot_db_path = hubspot_db_path
        self.aircall_db_path = aircall_db_path
        
        # Configuration par défaut des modèles
        if model is None:
            if self.provider == "openai":
                self.model = "gpt-4o-mini"  # Modèle économique et performant
            elif self.provider == "anthropic":
                self.model = "claude-sonnet-4-20250514"  # Modèle Anthropic par défaut
            else:
                raise ValueError(f"Provider non supporté: {provider}")
        else:
            self.model = model
        
        # Initialiser le client LLM
        self.api_key = api_key or os.getenv(f"{self.provider.upper()}_API_KEY")
        if not self.api_key:
            raise ValueError(
                f"Clé API {self.provider} non trouvée. "
                f"Définissez {self.provider.upper()}_API_KEY dans les variables d'environnement "
                f"ou passez api_key lors de l'initialisation."
            )
        
        if self.provider == "openai":
            if not OPENAI_AVAILABLE:
                raise ImportError("openai n'est pas installé. Installez-le avec: pip install openai")
            self.client = OpenAI(api_key=self.api_key)
        elif self.provider == "anthropic":
            if not ANTHROPIC_AVAILABLE:
                raise ImportError("anthropic n'est pas installé. Installez-le avec: pip install anthropic")
            self.client = Anthropic(api_key=self.api_key)
        else:
            raise ValueError(f"Provider non supporté: {provider}")
        
        # Charger les schémas des bases de données
        self.schemas = self._load_database_schemas()
    
    def _load_database_schemas(self) -> Dict[str, Dict]:
        """
        Charge les schémas de toutes les bases de données disponibles.
        
        Returns:
            Dictionnaire avec les schémas de chaque base
        """
        schemas = {}
        
        # Schéma Hubspot
        if os.path.exists(self.hubspot_db_path):
            try:
                conn = sqlite3.connect(self.hubspot_db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                
                hubspot_schema = {}
                for table in tables:
                    cursor.execute(f"PRAGMA table_info({table})")
                    columns = cursor.fetchall()
                    hubspot_schema[table] = {
                        'columns': [col[1] for col in columns],
                        'types': {col[1]: col[2] for col in columns}
                    }
                
                schemas['hubspot'] = {
                    'path': self.hubspot_db_path,
                    'tables': hubspot_schema
                }
                conn.close()
            except Exception as e:
                print(f"⚠️ Erreur lors du chargement du schéma Hubspot: {e}")
        
        # Schéma Aircall (seulement si des tables existent)
        if os.path.exists(self.aircall_db_path):
            try:
                conn = sqlite3.connect(self.aircall_db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                
                # Ne charger le schéma que s'il y a des tables
                if tables:
                    aircall_schema = {}
                    for table in tables:
                        cursor.execute(f"PRAGMA table_info({table})")
                        columns = cursor.fetchall()
                        aircall_schema[table] = {
                            'columns': [col[1] for col in columns],
                            'types': {col[1]: col[2] for col in columns}
                        }
                    
                    schemas['aircall'] = {
                        'path': self.aircall_db_path,
                        'tables': aircall_schema
                    }
                # Si pas de tables, on ne l'ajoute pas au schéma (pas d'erreur)
                conn.close()
            except Exception as e:
                print(f"⚠️ Erreur lors du chargement du schéma Aircall: {e}")
        
        return schemas
    
    def _get_schema_description(self) -> str:
        """
        Génère une description textuelle des schémas pour le LLM.
        
        Returns:
            Description formatée des schémas
        """
        description = "Bases de données disponibles:\n\n"
        
        for db_name, db_info in self.schemas.items():
            description += f"=== Base de données: {db_name.upper()} ===\n"
            description += f"Chemin: {db_info['path']}\n\n"
            
            for table_name, table_info in db_info['tables'].items():
                description += f"Table: {table_name}\n"
                description += "Colonnes:\n"
                for col in table_info['columns']:
                    col_type = table_info['types'].get(col, 'TEXT')
                    description += f"  - {col} ({col_type})\n"
                description += "\n"
        
        return description
    
    def _generate_sql_query(self, question: str, max_retries: int = 3) -> str:
        """
        Génère une requête SQL à partir d'une question en langage naturel.
        
        Args:
            question: Question en langage naturel
            max_retries: Nombre maximum de tentatives en cas d'erreur
            
        Returns:
            Requête SQL générée
        """
        schema_description = self._get_schema_description()
        
        system_prompt = """Tu es un expert SQL qui génère des requêtes SQL pour interroger des bases de données SQLite.
Tu dois générer UNIQUEMENT la requête SQL, sans explication, sans markdown, sans backticks.
La requête doit être valide SQLite et utiliser les noms de tables et colonnes exacts du schéma fourni.

Règles importantes:
- Utilise les noms de tables et colonnes EXACTEMENT comme indiqués dans le schéma
- SQLite ne supporte pas certains types de JOIN complexes, privilégie des requêtes simples
- Pour les dates, utilise les fonctions SQLite (DATE(), strftime(), etc.)
- Retourne UNIQUEMENT la requête SQL, rien d'autre
- Ne mets pas de backticks, de markdown, ou d'explications autour de la requête

Exemple de réponse attendue:
SELECT COUNT(*) FROM df_tickets WHERE "Date de création" > date('now', '-30 days')
"""
        
        user_prompt = f"""Schéma des bases de données:
{schema_description}

Question de l'utilisateur: {question}

Génère la requête SQL pour répondre à cette question:"""
        
        for attempt in range(max_retries):
            try:
                if self.provider == "openai":
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        temperature=0.1,  # Faible température pour des requêtes plus déterministes
                        max_tokens=500
                    )
                    sql_query = response.choices[0].message.content.strip()
                else:  # anthropic
                    response = self.client.messages.create(
                        model=self.model,
                        max_tokens=500,
                        temperature=0.1,
                        system=system_prompt,
                        messages=[
                            {"role": "user", "content": user_prompt}
                        ]
                    )
                    sql_query = response.content[0].text.strip()
                
                # Nettoyer la requête (enlever les backticks markdown si présents)
                sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
                
                return sql_query
                
            except Exception as e:
                if attempt == max_retries - 1:
                    raise Exception(f"Erreur lors de la génération SQL après {max_retries} tentatives: {e}")
                continue
        
        raise Exception("Impossible de générer la requête SQL")
    
    def _execute_query(self, sql_query: str) -> Tuple[pd.DataFrame, Optional[str]]:
        """
        Exécute une requête SQL sur les bases de données.
        
        Args:
            sql_query: Requête SQL à exécuter
            
        Returns:
            Tuple (DataFrame avec les résultats, message d'erreur éventuel)
        """
        # Détecter quelle base de données utiliser
        db_to_use = None
        
        # D'abord, chercher si une table spécifique est mentionnée dans la requête
        for db_name, db_info in self.schemas.items():
            for table_name in db_info['tables'].keys():
                # Vérifier si le nom de table apparaît dans la requête (insensible à la casse)
                if table_name.lower() in sql_query.lower():
                    db_to_use = db_info['path']
                    break
            if db_to_use:
                break
        
        # Si aucune base n'est détectée par table, essayer de détecter par nom de table
        if not db_to_use:
            # Si la requête mentionne "df_tickets", c'est probablement Hubspot
            if 'df_tickets' in sql_query.lower():
                if 'hubspot' in self.schemas:
                    db_to_use = self.schemas['hubspot']['path']
            # Si la requête mentionne "aircall_processed", c'est Aircall
            elif 'aircall_processed' in sql_query.lower() or 'aircall' in sql_query.lower():
                if 'aircall' in self.schemas:
                    db_to_use = self.schemas['aircall']['path']
        
        # Si toujours aucune base, utiliser hubspot par défaut (le plus courant)
        if not db_to_use:
            if 'hubspot' in self.schemas:
                db_to_use = self.schemas['hubspot']['path']
            elif 'aircall' in self.schemas:
                db_to_use = self.schemas['aircall']['path']
            else:
                return pd.DataFrame(), "Aucune base de données disponible"
        
        try:
            conn = sqlite3.connect(db_to_use)
            df = pd.read_sql(sql_query, conn)
            conn.close()
            return df, None
        except Exception as e:
            return pd.DataFrame(), f"Erreur SQL: {str(e)}"
    
    def query(self, question: str) -> Dict:
        """
        Répond à une question en langage naturel en interrogeant les bases de données.
        
        Args:
            question: Question en langage naturel
            
        Returns:
            Dictionnaire avec les résultats, la requête SQL, et d'éventuelles erreurs
        """
        try:
            # Générer la requête SQL
            sql_query = self._generate_sql_query(question)
            
            # Exécuter la requête
            df, error = self._execute_query(sql_query)
            
            if error:
                return {
                    "success": False,
                    "error": error,
                    "sql_query": sql_query,
                    "data": None
                }
            
            # Vérifier si le DataFrame est valide
            if df is None:
                return {
                    "success": False,
                    "error": "Aucun résultat retourné par la requête",
                    "sql_query": sql_query,
                    "data": None
                }
            
            return {
                "success": True,
                "sql_query": sql_query,
                "data": df,
                "row_count": len(df) if not df.empty else 0,
                "columns": list(df.columns) if not df.empty else []
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "sql_query": None,
                "data": None
            }
    
    def get_available_tables(self) -> Dict[str, List[str]]:
        """
        Retourne la liste des tables disponibles dans chaque base.
        
        Returns:
            Dictionnaire {nom_base: [liste_tables]}
        """
        result = {}
        for db_name, db_info in self.schemas.items():
            result[db_name] = list(db_info['tables'].keys())
        return result
