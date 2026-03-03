# Guide d'utilisation de l'Analyste IA MCP

## 📋 Vue d'ensemble

L'Analyste IA MCP permet d'interroger vos bases de données SQLite (Hubspot et Aircall) en langage naturel. Il utilise un LLM cloud (OpenAI ou Anthropic) pour générer automatiquement des requêtes SQL à partir de questions en français.

## 🚀 Installation

### 1. Installer les dépendances

```bash
pip install openai>=1.0.0 anthropic>=0.18.0
```

Ou réinstaller toutes les dépendances :

```bash
pip install -r requirements.txt
```

### 2. Configurer les clés API

Vous avez deux options pour configurer les clés API :

#### Option A : Variables d'environnement (recommandé)

```bash
# Pour OpenAI
export OPENAI_API_KEY="sk-votre-clé-api-openai"

# Pour Anthropic
export ANTHROPIC_API_KEY="sk-ant-votre-clé-api-anthropic"
```

#### Option B : Fichier config.py

Ajoutez directement dans `config.py` :

```python
OPENAI_API_KEY = "sk-votre-clé-api-openai"
ANTHROPIC_API_KEY = "sk-ant-votre-clé-api-anthropic"
```

⚠️ **Important** : Le fichier `config.py` est dans `.gitignore` pour éviter de commiter vos clés API.

### 3. Obtenir une clé API

- **OpenAI** : https://platform.openai.com/api-keys
- **Anthropic** : https://console.anthropic.com/settings/keys

## 💻 Utilisation

### Accès à l'interface

1. Lancez l'application Streamlit
2. Connectez-vous avec vos identifiants
3. Dans la sidebar, sélectionnez **"Analyste IA"**

### Interface

L'interface propose :

- **Sélection du provider** : Choisissez entre OpenAI et Anthropic
- **Sélection du modèle** : Choisissez le modèle selon le provider
- **Zone de saisie** : Posez votre question en français
- **Bouton "Analyser"** : Lance la génération SQL et l'exécution

### Exemples de questions

- "Combien de tickets ont été créés ce mois-ci ?"
- "Quel est le nombre total de tickets par statut ?"
- "Quels sont les 10 tickets les plus récents ?"
- "Combien de tickets ont été créés par semaine sur les 4 dernières semaines ?"
- "Quel est le temps de réponse moyen par agent ?"
- "Combien de tickets ont été créés par source (E-mail, Chat, Téléphone) ?"

### Résultats

L'interface affiche :

1. ✅ **Statut de succès** ou ❌ **message d'erreur**
2. 📝 **Requête SQL générée** (dans un expander)
3. 📊 **Résultats sous forme de tableau**
4. 📥 **Bouton de téléchargement CSV**

## 🔧 Configuration avancée

### Modèles disponibles

**OpenAI :**
- `gpt-4o-mini` (recommandé, économique)
- `gpt-4o` (plus performant)
- `gpt-4-turbo`
- `gpt-3.5-turbo`

**Anthropic :**
- `claude-3-5-sonnet-20241022` (recommandé)
- `claude-3-opus-20240229`
- `claude-3-haiku-20240307`

### Bases de données

L'analyste interroge automatiquement :

- **Hubspot** : `data/Cache/data_cache.db` → table `df_tickets`
- **Aircall** : `data/Affid/Cache/cache.sqlite` → tables disponibles

Les schémas sont chargés automatiquement au démarrage.

## 💰 Coûts estimés

### OpenAI
- `gpt-4o-mini` : ~$0.001-0.002 par requête
- `gpt-4o` : ~$0.03-0.06 par requête

### Anthropic
- `claude-3-5-sonnet` : ~$0.008-0.015 par requête
- `claude-3-haiku` : ~$0.001-0.002 par requête

**Estimation** : Pour ~100 requêtes/mois, comptez entre $0.10 et $6 selon le modèle.

## 🐛 Dépannage

### Erreur : "Clé API non configurée"

Vérifiez que :
1. La clé API est définie dans `config.py` ou en variable d'environnement
2. Le nom de la variable est correct (`OPENAI_API_KEY` ou `ANTHROPIC_API_KEY`)
3. La clé API est valide et active

### Erreur : "Aucune base de données trouvée"

Assurez-vous que :
1. Les données ont été chargées au moins une fois dans l'application
2. Les fichiers SQLite existent :
   - `data/Cache/data_cache.db` (Hubspot)
   - `data/Affid/Cache/cache.sqlite` (Aircall)

### Erreur SQL lors de l'exécution

L'IA peut parfois générer des requêtes SQL incorrectes. Dans ce cas :
1. Vérifiez la requête SQL générée dans l'expander
2. Reformulez votre question de manière plus précise
3. Essayez avec un autre modèle (gpt-4o au lieu de gpt-4o-mini par exemple)

## 🔒 Sécurité

- ✅ Les données restent **100% locales** (bases SQLite)
- ✅ Seules les **questions et schémas** sont envoyés au LLM cloud
- ✅ Les **résultats des requêtes** ne quittent jamais votre machine
- ⚠️ Les clés API doivent être gardées **secrètes** (jamais dans le code versionné)

## 📚 Ressources

- [Documentation OpenAI](https://platform.openai.com/docs)
- [Documentation Anthropic](https://docs.anthropic.com)
- [Documentation SQLite](https://www.sqlite.org/docs.html)
