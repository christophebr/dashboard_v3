# Déploiement sur Streamlit Cloud

## 1. Prérequis

- Compte [Streamlit Cloud](https://share.streamlit.io/)
- Repository GitHub : https://github.com/christophebr/dashboard_v3

## 2. Déploiement

1. Connectez-vous sur **https://share.streamlit.io/**
2. Cliquez sur **"New app"**
3. Remplissez :
   - **Repository** : `christophebr/dashboard_v3`
   - **Branch** : `main`
   - **Main file path** : `app.py`
   - **App URL** : (optionnel) choisissez un sous-domaine

4. Cliquez sur **"Deploy"**

## 3. Secrets (Manage app → Settings → Secrets)

### Option A : Plusieurs utilisateurs (recommandé)

Pour utiliser les identifiants habituels (cbri, mpec, etc.), ajoutez dans **Secrets** :

```toml
COOKIE_KEY = "une_cle_aleatoire_longue"

[users.cbri]
name = "Christophe Bri"
password = "votre_mot_de_passe_cbri"

[users.mpec]
name = "Miguel Pecqueux"
password = "mot_de_passe_mpec"

[users.pgou]
name = "Pierre Goupillon"
password = "mot_de_passe_pgou"
# ... ajoutez les autres utilisateurs (elap, fsau, mhum, akes, dlau, jdel, osai)
```

### Option B : Un seul admin

```toml
COOKIE_KEY = "une_cle_aleatoire"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "votre_mot_de_passe"
ADMIN_NAME = "Administrateur"
```

### Optionnel : Analyste IA
```toml
ANTHROPIC_API_KEY = "votre_cle_anthropic"
```

## 4. Fichier config.py au démarrage

L'app crée automatiquement `config.py` à partir de `config.example.py` au premier lancement si absent.

Le `config.example.py` gère le cas où `hashed_pw.pkl` est absent : il utilise les variables d'environnement `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `ADMIN_NAME`.

## 5. Structure des données

Le dossier `data/` est inclus dans le repo. Les chemins par défaut sont :
- Aircall : `data/Affid/Aircall/data_v1`, `data_v2`, `data_v3`
- HubSpot : `data/Affid/Hubspot/ticket`
- Yelda : `data/Affid/yelda/yelda.xlsx`
- Évaluation : `data/Affid/Evaluation/support_notes_filtered.xlsx`
