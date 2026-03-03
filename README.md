# Dashboard Support Olaqin

Tableau de bord Streamlit pour le suivi des activités support (Aircall, Hubspot).

## Installation locale

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Créer `config.py` à partir de `config.example.py` et configurer les chemins / identifiants.

```bash
streamlit run app.py
```

## Déploiement (Railway, Render)

Voir [DEPLOIEMENT.md](DEPLOIEMENT.md) pour les instructions complètes.
