# Déploiement vers un nouveau repository GitHub

## 1. Créer le nouveau repository sur GitHub

1. Allez sur https://github.com/new
2. Choisissez un nom (ex. `dashboard-support-stellair` ou `dashboard-yelda`)
3. Ne cochez **pas** "Add a README" (le repo doit être vide)
4. Créez le repository

## 2. Préparer et pousser le code

Exécutez ces commandes dans le terminal, à la racine du projet :

```bash
# Se placer à la racine
cd /Users/cbrichet/Library/CloudStorage/OneDrive-OLAQIN/Python/depot_new

# Ajouter les fichiers modifiés et nouveaux (les données sensibles sont exclues par .gitignore)
git add app.py data_processing/yelda_processing.py data_processing/kpi_generation.py \
  data_processing/aircall_processing.py data_processing/hubspot_processing.py \
  config.example.py DEPLOIEMENT_GITHUB.md

# Commit
git commit -m "feat: Indicateurs Yelda, graphique N1 par semaine, évolution scores dans le temps"

# Remplacer l'origin par votre nouveau repository
git remote remove origin
git remote add origin https://github.com/VOTRE_UTILISATEUR/VOTRE_REPO.git

# Pousser (si des conflits avec main existent, force push après vérification)
git push -u origin main
```

Remplacez `VOTRE_UTILISATEUR/VOTRE_REPO` par l’URL de votre nouveau dépôt.

## 3. Données à configurer après clonage

- Copiez `config.example.py` vers `config.py` et adaptez les chemins / secrets
- Créez la structure de dossiers `data/Affid/yelda/` et placez-y `yelda.xlsx` pour les indicateurs Yelda
