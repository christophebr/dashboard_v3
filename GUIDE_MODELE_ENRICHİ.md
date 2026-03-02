# 🚀 Guide du Modèle de Catégorisation Enrichi

## 📋 Vue d'ensemble

Ce guide explique comment utiliser le nouveau système de catégorisation des tickets enrichi avec des définitions de contexte. Ce système améliore significativement la précision de la catégorisation automatique.

## 🎯 Améliorations apportées

### ✅ Avantages du nouveau système :
- **+18.3% de précision** par rapport au modèle original
- **Définitions de contexte** pour chaque catégorie
- **Compatibilité** avec le système existant
- **Fallback automatique** vers l'ancien modèle si nécessaire

### 📊 Résultats de performance :
- **Modèle enrichi** : 68.9% de précision (CV: 72.3%)
- **Modèle original** : 58.2% de précision (CV: 59.1%)
- **Amélioration** : +18.3%

## 📁 Structure des fichiers

### Fichiers créés :
```
data/Affid/modele/
├── definitions_categories.yaml          # Définitions des catégories principales
├── definitions_sous_categories.yaml     # Définitions des sous-catégories
├── modele_avec_definitions.xlsx         # Données d'entraînement enrichies
├── enhanced_ticket_classifier.pkl       # Modèle entraîné enrichi
└── ticket_classifier.pkl                # Modèle original (fallback)
```

### Contenu des définitions :

#### Catégories principales (`definitions_categories.yaml`) :
- **Connexion/Accès** : Problèmes d'authentification, connexion, mots de passe
- **Fonctionnalités** : Dysfonctionnements, erreurs système, bugs
- **Données** : Problèmes de fichiers, sauvegarde, synchronisation
- **Interface** : Problèmes d'affichage, navigation, ergonomie
- **Performance** : Lenteur, timeouts, optimisation
- **Configuration** : Paramètres, installation, mise à jour
- **Facturation** : Codes CCAM, NGAP, exonérations, etc.
- **Autres** : Problèmes divers

#### Sous-catégories de facturation (`definitions_sous_categories.yaml`) :
- **Facturation-Cotation CCAM** : Codes CCAM, tarification
- **Facturation-Exoneration** : ALD, C2S, exonérations
- **Facturation-Teleconsultation** : TCS, consultation à distance
- **Facturation-Majoration** : MD, VSP, MN, MM
- **Et 13 autres sous-catégories...**

## 🔧 Utilisation dans le code

### 1. Import et chargement automatique

Le système utilise automatiquement le meilleur modèle disponible :

```python
from data_processing.enhanced_ticket_classifier import predict_with_enhanced_model

# Prédiction automatique avec le modèle enrichi
descriptions = [
    "Je n'arrive pas à me connecter",
    "Problème avec la facturation CCAM"
]

predictions = predict_with_enhanced_model(descriptions)
```

### 2. Chargement manuel du modèle

```python
from data_processing.enhanced_ticket_classifier import load_enhanced_ticket_classifier

# Charger le modèle enrichi
classifier = load_enhanced_ticket_classifier()

# Faire des prédictions
predictions = classifier.predict(descriptions)
```

### 3. Informations sur les modèles

```python
from data_processing.enhanced_ticket_classifier import get_model_info

# Obtenir l'état des modèles
info = get_model_info()
print(f"Modèle enrichi disponible: {info['enhanced_model_available']}")
print(f"Nombre de catégories: {info['enhanced_categories_count']}")
```

## 🎯 Intégration dans le dashboard

### Modification automatique

Le système est déjà intégré dans votre dashboard. Dans la page "Tickets", il utilisera automatiquement :

1. **Le modèle enrichi** s'il est disponible
2. **Le modèle classique** en fallback
3. **Les définitions de contexte** pour améliorer la précision

### Utilisation dans `app.py`

Le code existant dans `app.py` utilise déjà le nouveau système via :

```python
from data_processing.kpi_generation import analyser_categories_tickets_ssi_chat_ml

# Cette fonction utilise automatiquement le modèle enrichi
df_categorise, fig_categories, fig_evolution, df_tableau_complet = analyser_categories_tickets_ssi_chat_ml(df_tickets, use_ml_model=True)
```

## 🔄 Mise à jour et maintenance

### 1. Ajouter de nouvelles définitions

Pour ajouter ou modifier des définitions :

1. **Éditer les fichiers YAML** :
   ```bash
   # Éditer les définitions des catégories
   nano data/Affid/modele/definitions_categories.yaml
   
   # Éditer les définitions des sous-catégories
   nano data/Affid/modele/definitions_sous_categories.yaml
   ```

2. **Recréer le fichier enrichi** :
   ```bash
   python create_model_with_definitions.py
   ```

3. **Réentraîner le modèle** :
   ```bash
   python train_model_with_definitions.py
   ```

### 2. Ajouter de nouveaux exemples d'entraînement

1. **Ajouter des exemples** dans `data/Affid/modele/modele.xlsx`
2. **Recréer le fichier enrichi** :
   ```bash
   python create_model_with_definitions.py
   ```
3. **Réentraîner le modèle** :
   ```bash
   python train_model_with_definitions.py
   ```

### 3. Vérifier l'état du système

```bash
python test_enhanced_model.py
```

## 🧪 Tests et validation

### Test rapide

```bash
python test_enhanced_model.py
```

### Test de prédiction

```python
from data_processing.enhanced_ticket_classifier import predict_with_enhanced_model

# Exemples de test
test_descriptions = [
    "Problème de connexion à l'application",
    "Question sur la facturation CCAM",
    "L'interface est lente"
]

predictions = predict_with_enhanced_model(test_descriptions)

for desc, pred in zip(test_descriptions, predictions):
    print(f"Description: {desc}")
    print(f"Catégorie: {pred['categorie_predite']}")
    print(f"Confiance: {pred['confiance']:.2f}")
    print("---")
```

## 📊 Monitoring des performances

### Métriques à surveiller :

1. **Précision globale** : Doit être > 65%
2. **Confiance moyenne** : Doit être > 0.15
3. **Répartition des catégories** : Équilibrée
4. **Temps de prédiction** : < 1 seconde

### Amélioration continue :

1. **Analyser les erreurs** de catégorisation
2. **Ajouter des exemples** pour les catégories peu performantes
3. **Affiner les définitions** si nécessaire
4. **Réentraîner régulièrement** le modèle

## 🚨 Dépannage

### Problèmes courants :

#### 1. Modèle non trouvé
```
❌ Modèle enrichi non trouvé
```
**Solution** : Exécuter `python train_model_with_definitions.py`

#### 2. Erreur de compatibilité scikit-learn
```
⚠️ Trying to unpickle estimator from version 1.6.1 when using version 1.2.1
```
**Solution** : Réentraîner le modèle avec la version actuelle

#### 3. Définitions manquantes
```
❌ Fichier de définitions non trouvé
```
**Solution** : Vérifier que les fichiers YAML existent

### Logs utiles :

```python
import logging
logging.basicConfig(level=logging.INFO)

# Les logs montreront quel modèle est utilisé
from data_processing.enhanced_ticket_classifier import predict_with_enhanced_model
```

## 🎯 Prochaines étapes

### Améliorations possibles :

1. **Ajouter plus d'exemples** d'entraînement
2. **Affiner les définitions** de catégories
3. **Tester avec d'autres algorithmes** (BERT, etc.)
4. **Ajouter des métriques** de performance en temps réel
5. **Interface d'administration** pour gérer les définitions

### Maintenance recommandée :

- **Mensuelle** : Vérifier les performances
- **Trimestrielle** : Ajouter de nouveaux exemples
- **Semestrielle** : Réentraîner le modèle complet

## 📞 Support

Pour toute question ou problème :

1. **Vérifier les logs** du système
2. **Exécuter les tests** : `python test_enhanced_model.py`
3. **Consulter ce guide** pour les solutions courantes
4. **Réentraîner le modèle** si nécessaire

---

**✅ Le système est maintenant opérationnel et améliorera automatiquement la catégorisation de vos tickets !** 