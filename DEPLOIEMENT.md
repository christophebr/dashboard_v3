# Guide de déploiement

## Prérequis

- Compte [GitHub](https://github.com)
- Compte [Railway](https://railway.app) ou [Render](https://render.com)

## Étape 1 : Créer le dépôt GitHub

### Option A : Nouveau dépôt vide

1. Allez sur [github.com/new](https://github.com/new)
2. Nommez le dépôt (ex: `dashboard-support-olaqin`)
3. Choisissez **Privé**
4. **Ne cochez pas** « Initialize with README »
5. Cliquez sur **Create repository**

### Option B : Avec GitHub CLI

```bash
cd /chemin/vers/depot_new
gh repo create dashboard-support-olaqin --private --source=. --remote=origin
```

## Étape 2 : Pousser le code

```bash
cd /chemin/vers/depot_new

# Initialiser Git (si pas déjà fait)
git init

# Ajouter les fichiers
git add .
git commit -m "Initial commit - Dashboard Support"

# Lier au dépôt distant et pousser
git remote add origin https://github.com/VOTRE_USERNAME/dashboard-support-olaqin.git
git branch -M main
git push -u origin main
```

> **Note :** Les fichiers `config.py`, `data/`, `hashed_pw.pkl` sont dans `.gitignore` et ne seront pas poussés (normal pour la sécurité).

## Étape 3 : Déployer sur Railway

1. Allez sur [railway.app](https://railway.app) et connectez-vous
2. **New Project** → **Deploy from GitHub repo**
3. Sélectionnez votre dépôt `dashboard-support-olaqin`
4. Railway détecte automatiquement le Procfile

### Variables d'environnement (Railway)

Dans **Variables** du projet, ajoutez :

| Variable | Description | Exemple |
|----------|-------------|---------|
| `ADMIN_USERNAME` | Identifiant de connexion | `admin` |
| `ADMIN_PASSWORD` | Mot de passe (en clair) | `VotreMotDePasse123!` |
| `ADMIN_NAME` | Nom affiché | `Administrateur` |
| `COOKIE_KEY` | Clé pour les cookies (aléatoire) | Générer avec `openssl rand -hex 32` |
| `ANTHROPIC_API_KEY` | (Optionnel) Clé pour l'Analyste IA | `sk-ant-...` |

### Volume persistant (données)

1. Dans Railway : **Variables** → **Volumes**
2. Créez un volume monté sur `/app/data`
3. Uploadez vos fichiers Excel dans `data/Affid/` après le premier déploiement (SFTP ou Railway CLI)

### Domaine

Railway génère une URL `.railway.app`. Vous pouvez ajouter un domaine personnalisé dans **Settings**.

## Étape 4 : Déployer sur Render

1. Allez sur [render.com](https://render.com)
2. **New** → **Web Service**
3. Connectez GitHub et sélectionnez le dépôt
4. Render utilise `render.yaml` automatiquement

### Variables d'environnement (Render)

Mêmes variables que Railway (voir tableau ci-dessus).

### Stockage des données

Le fichier `render.yaml` configure un disque de 1 Go sur `data/`. Pour ajouter vos données :
- Après le déploiement, utilisez le **Shell** Render pour uploader des fichiers
- Ou synchronisez via un script (rclone, etc.)

## Structure des données attendues

```
data/
├── Affid/
│   ├── Aircall/
│   │   ├── data_v1/   # Fichiers Excel Aircall V1
│   │   ├── data_v2/   # Fichiers Excel Aircall V2
│   │   └── data_v3/   # Fichiers Excel Aircall V3
│   ├── Hubspot/
│   │   └── ticket/    # Exports Excel Hubspot tickets
│   └── Evaluation/
│       └── support_notes_filtered.xlsx
models/
├── random_forest_model.pkl
└── tfidf_vectorizer.pkl
```

## Dépannage

- **Erreur au démarrage** : Vérifiez que `ADMIN_PASSWORD` et `COOKIE_KEY` sont définis
- **Pas de données** : Créez les dossiers et uploadez au moins un fichier Excel par source
- **Port** : Railway et Render définissent `$PORT` automatiquement
