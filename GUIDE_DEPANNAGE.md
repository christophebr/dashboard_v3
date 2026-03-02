# 🔧 Guide de Dépannage - Catégorisation Enrichie

## 🚨 Erreurs courantes et solutions

### ❌ Erreur 1: KeyError: 'enhanced_categories_count'

**Symptôme :**
```
KeyError: 'enhanced_categories_count'
```

**Cause :** La clé `enhanced_categories_count` n'existe pas dans le dictionnaire retourné par `get_model_info()`.

**Solution :** ✅ **CORRIGÉ**
- Vérification de sécurité ajoutée dans `app.py`
- La clé est maintenant vérifiée avant utilisation

### ❌ Erreur 2: KeyError: 'scores_par_categorie'

**Symptôme :**
```
KeyError: 'scores_par_categorie'
```

**Cause :** La clé `scores_par_categorie` n'existe pas dans les prédictions.

**Solution :** ✅ **CORRIGÉ**
- Gestion d'erreur robuste ajoutée dans `app.py`
- Extraction sécurisée des prédictions avec valeurs par défaut

### ❌ Erreur 3: KeyError: 'Categorie_Final'

**Symptôme :**
```
KeyError: 'Categorie_Final'
```

**Cause :** La colonne `Categorie_Final` n'est pas créée correctement.

**Solution :** ✅ **CORRIGÉ**
- Processus de création du DataFrame amélioré
- Gestion d'erreur pour toutes les colonnes

## 🧪 Tests de diagnostic

### 1. Test de la structure des prédictions
```bash
python test_prediction_structure.py
```

### 2. Test du processus complet
```bash
python test_app_categorisation.py
```

### 3. Test du module enrichi
```bash
python test_enhanced_model.py
```

## 🔍 Vérifications préventives

### 1. Vérifier les fichiers requis
```python
import os

required_files = [
    "data/Affid/modele/enhanced_ticket_classifier.pkl",
    "data/Affid/modele/definitions_categories.yaml",
    "data/Affid/modele/definitions_sous_categories.yaml"
]

for file_path in required_files:
    if os.path.exists(file_path):
        print(f"✅ {file_path}")
    else:
        print(f"❌ {file_path} manquant")
```

### 2. Vérifier les imports
```python
try:
    from data_processing.enhanced_ticket_classifier import predict_with_enhanced_model, get_model_info
    print("✅ Imports réussis")
except ImportError as e:
    print(f"❌ Erreur d'import: {e}")
```

### 3. Vérifier les informations du modèle
```python
from data_processing.enhanced_ticket_classifier import get_model_info

info = get_model_info()
print("📊 Informations du modèle:")
for key, value in info.items():
    print(f"  {key}: {value}")
```

## 🛠️ Corrections appliquées

### ✅ Correction 1: Gestion sécurisée des prédictions
```python
# AVANT (problématique)
df_categorise['Categorie_Enrichie'] = [pred['categorie_predite'] for pred in predictions]

# APRÈS (sécurisé)
categories_predites = []
for pred in predictions:
    if 'categorie_predite' in pred:
        categories_predites.append(pred['categorie_predite'])
    else:
        categories_predites.append('Non catégorisé')
df_categorise['Categorie_Enrichie'] = categories_predites
```

### ✅ Correction 2: Vérification des clés conditionnelles
```python
# AVANT (problématique)
if model_info['enhanced_model_available']:
    st.info(f"📊 {model_info['enhanced_categories_count']} catégories")

# APRÈS (sécurisé)
if model_info['enhanced_model_available'] and 'enhanced_categories_count' in model_info:
    st.info(f"📊 {model_info['enhanced_categories_count']} catégories")
```

### ✅ Correction 3: Gestion des scores détaillés
```python
# AVANT (problématique)
scores = row['Scores_par_categorie']
scores_tries = sorted(scores.items(), key=lambda x: x[1], reverse=True)

# APRÈS (sécurisé)
scores = row['Scores_par_categorie']
if scores and isinstance(scores, dict):
    scores_tries = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    # Traitement des scores
else:
    st.write("Aucun score détaillé disponible")
```

## 📊 Monitoring et logs

### Logs de diagnostic
Le système génère maintenant des logs détaillés :
- ✅ Chargement du modèle
- 📊 Nombre de catégories
- 🔧 Utilisation des descriptions enrichies
- 🎯 Type de modèle utilisé

### Métriques de performance
- Taux de catégorisation
- Confiance moyenne
- Temps de traitement
- Nombre de tickets traités

## 🚀 Prévention des erreurs

### 1. Validation des données d'entrée
- Vérification de la colonne de description
- Gestion des valeurs manquantes
- Conversion sécurisée en string

### 2. Gestion des cas limites
- Modèle non disponible → Fallback
- Définitions manquantes → Mode classique
- Erreurs de prédiction → Valeurs par défaut

### 3. Cache intelligent
- Mise en cache des résultats
- Invalidation automatique
- Gestion des erreurs de cache

## 📞 Support

### En cas de problème persistant :
1. **Exécutez les tests de diagnostic**
2. **Vérifiez les logs d'erreur**
3. **Consultez ce guide de dépannage**
4. **Relancez l'entraînement si nécessaire**

### Commandes de récupération :
```bash
# Réentraîner le modèle
python train_model_with_definitions.py

# Tester le système
python test_enhanced_model.py

# Vérifier l'application
python test_app_categorisation.py
```

## 🎯 Résumé des améliorations

- ✅ **Gestion d'erreur robuste** pour toutes les clés
- ✅ **Fallback automatique** vers le modèle classique
- ✅ **Validation des données** d'entrée
- ✅ **Logs détaillés** pour le diagnostic
- ✅ **Tests automatisés** pour la validation
- ✅ **Cache intelligent** pour les performances

Le système est maintenant **robuste** et **fiable** ! 🎉 