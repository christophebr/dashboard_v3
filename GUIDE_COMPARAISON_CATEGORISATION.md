# 📊 Guide de Comparaison des Méthodes de Catégorisation

## 🎯 Vue d'ensemble

Ce guide présente les trois méthodes de catégorisation disponibles dans l'application pour analyser les tickets SSI/Chat :

1. **🤖 Catégorisation Enrichie avec Définitions**
2. **🔧 Catégorisation Classique**
3. **📊 Catégorisation HubSpot (Référence)**

## 📋 Méthodes de Catégorisation

### 1. 🤖 **Catégorisation Enrichie avec Définitions**

#### **Description :**
- **Modèle** : Modèle de machine learning entraîné avec des définitions de contexte
- **Données d'entraînement** : `modele.xlsx` enrichi avec des définitions YAML
- **Avantages** : Précision améliorée grâce au contexte enrichi
- **Inconvénients** : Dépend de la qualité des définitions

#### **Caractéristiques :**
- ✅ **Définitions de contexte** : Chaque catégorie a une définition détaillée
- ✅ **Descriptions originales** : Utilise les descriptions originales (plus fiables)
- ✅ **19 catégories principales** : Focus sur les catégories principales
- ✅ **Seuil de confiance ajustable** : Contrôle de la qualité des prédictions

#### **Fichiers utilisés :**
- `data/Affid/modele/enhanced_ticket_classifier.pkl` - Modèle entraîné
- `data/Affid/modele/definitions_categories.yaml` - Définitions des catégories
- `data/Affid/modele/modele_avec_definitions.xlsx` - Données d'entraînement enrichies

### 2. 🔧 **Catégorisation Classique**

#### **Description :**
- **Modèle** : Modèle de machine learning standard (sans définitions enrichies)
- **Données d'entraînement** : `modele.xlsx` original
- **Avantages** : Modèle éprouvé et stable
- **Inconvénients** : Moins de contexte que la version enrichie

#### **Caractéristiques :**
- ✅ **Modèle standard** : Random Forest classique
- ✅ **Données originales** : Utilise les descriptions originales
- ✅ **Même seuil de confiance** : Cohérence avec la méthode enrichie
- ✅ **Comparaison directe** : Base de référence pour l'amélioration

#### **Fichiers utilisés :**
- `data/Affid/modele/ticket_classifier.pkl` - Modèle classique
- `data/Affid/modele/modele.xlsx` - Données d'entraînement originales

### 3. 📊 **Catégorisation HubSpot (Référence)**

#### **Description :**
- **Source** : Champ catégorie directement depuis HubSpot
- **Entraînement** : Aucun (données natives)
- **Avantages** : Vérité terrain, pas d'erreur de prédiction
- **Inconvénients** : Dépend de la qualité de la saisie manuelle

#### **Caractéristiques :**
- ✅ **Vérité terrain** : Catégories assignées manuellement
- ✅ **Confiance maximale** : Score de 1.0 pour tous les tickets
- ✅ **Référence absolue** : Base de comparaison pour les modèles
- ✅ **Analyse directe** : Pas de traitement ML
- ✅ **Filtrage top 20** : Seules les 20 catégories les plus fréquentes sont conservées
- ✅ **Catégorie "Autres"** : Les catégories moins fréquentes sont regroupées

#### **Colonnes recherchées :**
- `Catégorie`, `Category`, `Categorie`
- `Type`, `Type de ticket`, `Ticket Type`
- `Classification`, `Classe`

#### **Filtrage top 20 :**
```python
# Calculer le top 20 des catégories les plus fréquentes
categories_counts = df_categorise_hubspot['Categorie_HubSpot'].value_counts()
top_20_categories = categories_counts.head(20).index.tolist()

# Appliquer le filtrage : garder seulement les top 20, les autres deviennent "Autres"
df_categorise_hubspot['Categorie_Final_HubSpot'] = df_categorise_hubspot['Categorie_HubSpot'].apply(
    lambda x: x if x in top_20_categories else 'Autres'
)
```

## 🔍 Filtrage Commun

### **Critères de filtrage :**
Toutes les méthodes utilisent le même filtrage :
- **Pipeline** : Doit contenir "SSI" (insensible à la casse)
- **Source** : Doit contenir "Chat" (insensible à la casse)

### **Code de filtrage :**
```python
df_tickets_ssi_chat = df_tickets_periode[
    (df_tickets_periode['Pipeline'].str.lower().str.contains('ssi', na=False)) & 
    (df_tickets_periode['Source'].str.lower().str.contains('chat', na=False))
].copy()
```

## 🎯 Filtrage Top 20 HubSpot

### **Objectif :**
Limiter l'affichage aux 20 catégories HubSpot les plus fréquentes pour améliorer la lisibilité et la pertinence de l'analyse.

### **Processus :**
1. **Calcul des fréquences** : Compter le nombre d'occurrences de chaque catégorie
2. **Sélection top 20** : Prendre les 20 catégories les plus fréquentes
3. **Regroupement "Autres"** : Les catégories moins fréquentes deviennent "Autres"
4. **Optimisation graphique** : Exclure "Autres" du graphique si < 5% des tickets

### **Avantages :**
- ✅ **Lisibilité améliorée** : Graphiques plus clairs avec moins de catégories
- ✅ **Focus sur l'essentiel** : Concentration sur les catégories les plus importantes
- ✅ **Performance** : Traitement plus rapide avec moins de catégories
- ✅ **Cohérence** : Alignement avec les modèles ML qui ont un nombre limité de catégories

### **Gestion de la catégorie "Autres" :**
- **Création automatique** : Regroupement des catégories hors top 20
- **Exclusion conditionnelle** : Retirée du graphique si < 5% des tickets
- **Information utilisateur** : Affichage du pourcentage représenté par "Autres"

## 📈 Métriques de Comparaison

### **Métriques affichées :**
1. **Tickets SSI/Chat** : Nombre total de tickets filtrés
2. **Tickets catégorisés** : Nombre de tickets avec catégorie valide
3. **Taux de catégorisation** : Pourcentage de tickets catégorisés
4. **Confiance moyenne** : Moyenne des scores de confiance

### **Calculs :**
```python
taux_categorisation = (tickets_categorises / total_tickets_ssi_chat) * 100
confiance_moyenne = df['Confiance'].mean()
```

## 🎯 Utilisation dans l'Application

### **Interface utilisateur :**
1. **Page Tickets** → Section "Catégorisation Enrichie avec Définitions"
2. **Page Tickets** → Section "Catégorisation Classique"
3. **Page Tickets** → Section "Catégorisation HubSpot"
4. **Page Tickets** → Section "Comparaison des Méthodes"

### **Paramètres communs :**
- **Seuil de confiance** : Ajustable (défaut: 0.15)
- **Période** : Même période pour toutes les méthodes
- **Cache** : Système de cache indépendant pour chaque méthode

## 📊 Analyse des Résultats

### **Interprétation des métriques :**

#### **Taux de catégorisation :**
- **Élevé (>80%)** : Modèle performant
- **Moyen (50-80%)** : Modèle acceptable
- **Faible (<50%)** : Modèle à améliorer

#### **Confiance moyenne :**
- **Élevée (>0.7)** : Prédictions fiables
- **Moyenne (0.4-0.7)** : Prédictions modérément fiables
- **Faible (<0.4)** : Prédictions peu fiables

### **Comparaison avec HubSpot :**
- **Convergence** : Les modèles ML se rapprochent-ils de HubSpot ?
- **Divergence** : Où les modèles diffèrent-ils de HubSpot ?
- **Qualité** : Quelle méthode donne les meilleurs résultats ?

## 🔄 Maintenance et Amélioration

### **Réentraînement des modèles :**
```bash
# Modèle enrichi
python train_model_with_definitions.py

# Modèle classique
python train_model.py
```

### **Tests de validation :**
```bash
# Test des prédictions spécifiques
python test_specific_predictions.py

# Test de la fonction d'export
python test_export_function.py

# Test complet du système
python test_enhanced_model.py
```

### **Amélioration des performances :**
1. **Augmentation des données** : Plus d'exemples d'entraînement
2. **Optimisation des définitions** : Amélioration des descriptions YAML
3. **Ajustement des paramètres** : Tuning du Random Forest
4. **Prétraitement amélioré** : Nettoyage du texte optimisé

## 📞 Support et Dépannage

### **Problèmes courants :**

#### **Modèle enrichi non disponible :**
- Vérifier l'existence de `enhanced_ticket_classifier.pkl`
- Réentraîner avec `python train_model_with_definitions.py`

#### **Modèle classique non disponible :**
- Vérifier l'existence de `ticket_classifier.pkl`
- Réentraîner avec `python train_model.py`

#### **Aucune colonne catégorie HubSpot :**
- Vérifier les noms de colonnes dans les données
- Ajouter des alias dans `colonnes_categorie_possibles`

### **Commandes de diagnostic :**
```bash
# Vérifier les modèles disponibles
python test_enhanced_model.py

# Tester les prédictions
python test_specific_predictions.py

# Analyser les données HubSpot
python -c "import pandas as pd; df = pd.read_excel('data.xlsx'); print(df.columns.tolist())"
```

## 🎉 Avantages de la Comparaison

### **Analyse comparative :**
- **Performance** : Quelle méthode est la plus performante ?
- **Fiabilité** : Quelle méthode est la plus fiable ?
- **Cohérence** : Les méthodes donnent-elles des résultats cohérents ?

### **Décisions basées sur les données :**
- **Choix de méthode** : Quelle méthode utiliser en production ?
- **Amélioration** : Comment améliorer les modèles ?
- **Validation** : Les modèles sont-ils suffisamment fiables ?

### **ROI et efficacité :**
- **Temps de traitement** : Quelle méthode est la plus rapide ?
- **Précision** : Quelle méthode donne les meilleurs résultats ?
- **Maintenance** : Quelle méthode est la plus facile à maintenir ?

## 🚀 Conclusion

La comparaison des trois méthodes de catégorisation permet de :

1. **Évaluer les performances** de chaque approche
2. **Identifier les améliorations** nécessaires
3. **Choisir la meilleure méthode** pour vos besoins
4. **Valider la qualité** des prédictions ML

Cette approche comparative garantit une analyse robuste et éclairée des tickets de support ! 🎯 