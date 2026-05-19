# 🤖 Modèle de Classification des Tickets

## 📋 Vue d'ensemble

Ce modèle utilise **TF-IDF + Random Forest** pour catégoriser automatiquement les tickets de support SSI/Chat basés sur leur description. Il a été conçu spécifiquement pour le domaine de la télétransmission de feuilles de soins.

## 🎯 Performance attendue

- **Précision** : 85-90% (performance moyenne comme demandé)
- **Vitesse** : Entraînement rapide (< 30 secondes pour 927 exemples)
- **Interprétabilité** : Possibilité de voir les mots-clés importants

## 🚀 Installation et utilisation

### 1. Préparation des données

Votre fichier Excel doit contenir ces colonnes :
- `ID` : Identifiant du ticket (non utilisé)
- `sous-catégorie` : Sous-catégorie du ticket
- `catégorie` : Catégorie principale du ticket
- `description` : Description du problème

**Format attendu** : `data/affid/modele/modele.xlsx`

### 2. Entraînement du modèle

```bash
python train_model.py
```

Le script va :
- Charger vos 927 descriptions
- Entraîner le modèle TF-IDF + Random Forest
- Évaluer la performance (validation croisée)
- Sauvegarder le modèle entraîné
- Tester avec des exemples

### 3. Utilisation dans le dashboard

Le modèle est automatiquement intégré dans votre dashboard. Dans la page "Tickets", il remplacera l'analyse par mots-clés.

## 📊 Fonctionnalités

### Entraînement
- **Prétraitement** : Nettoyage du texte, suppression des caractères spéciaux
- **Vectorisation TF-IDF** : 5000 features max, bigrammes (1-2 mots)
- **Random Forest** : 100 arbres, profondeur max 20
- **Validation** : 5-fold cross-validation

### Prédiction
- **Catégorie principale** : Prédiction de la catégorie
- **Score de confiance** : Probabilité de la prédiction
- **Probabilités** : Scores pour toutes les catégories

### Analyse
- **Mots importants** : Top 20 mots-clés par catégorie
- **Évolution** : Graphiques d'évolution par semaine
- **Répartition** : Graphiques en camembert

## 🔧 Configuration

### Paramètres du modèle (modifiables dans `ticket_classifier.py`)

```python
# TF-IDF
max_features=5000      # Nombre max de mots
ngram_range=(1, 2)     # Mots simples + bigrammes
min_df=2              # Mot présent dans au moins 2 documents
max_df=0.95           # Mot présent dans max 95% des documents

# Random Forest
n_estimators=100      # Nombre d'arbres
max_depth=20          # Profondeur max des arbres
```

### Chemins des fichiers
```python
model_path = "data/affid/modele/ticket_classifier.pkl"  # Modèle sauvegardé
data_path = "data/affid/modele/modele.xlsx"            # Données d'entraînement
```

## 📈 Métriques de performance

Le modèle affiche :
- **Précision globale** : Pourcentage de prédictions correctes
- **Rapport détaillé** : Précision, rappel, F1-score par catégorie
- **Validation croisée** : Performance moyenne sur 5 folds
- **Mots importants** : Features les plus influentes

## 🛠️ Dépannage

### Erreur "Fichier non trouvé"
```
❌ Erreur: Fichier non trouvé - data/affid/modele/modele.xlsx
```
**Solution** : Vérifiez que le fichier existe et contient les bonnes colonnes.

### Erreur "Modèle non entraîné"
```
❌ Le modèle n'est pas entraîné. Utilisez train() d'abord.
```
**Solution** : Lancez `python train_model.py` pour entraîner le modèle.

### Performance faible
**Solutions possibles** :
1. Vérifiez la qualité des descriptions
2. Augmentez le nombre d'exemples par catégorie
3. Ajustez les paramètres TF-IDF
4. Ajoutez des mots-clés spécifiques au domaine

## 🔄 Mise à jour du modèle

Pour réentraîner le modèle avec de nouvelles données :

1. Ajoutez vos nouvelles descriptions au fichier Excel
2. Relancez `python train_model.py`
3. Le nouveau modèle remplacera l'ancien automatiquement

## 📝 Exemples d'utilisation

### Dans le code Python
```python
from data_processing.ticket_classifier import load_ticket_classifier

# Charger le modèle
classifier = load_ticket_classifier()

# Prédire une catégorie
result = classifier.predict("Je n'arrive pas à me connecter")
print(f"Catégorie: {result['categorie_predite']}")
print(f"Confiance: {result['confiance']:.3f}")
```

### Dans le dashboard
Le modèle est automatiquement utilisé dans la fonction `analyser_categories_tickets_ssi_chat_ml()` avec le paramètre `use_ml_model=True`.

## 🎯 Avantages du modèle

1. **Performance** : Plus précis que l'analyse par mots-clés
2. **Flexibilité** : S'adapte au vocabulaire spécifique du domaine
3. **Confiance** : Fournit un score de confiance pour chaque prédiction
4. **Évolutivité** : Facile à réentraîner avec de nouvelles données
5. **Interprétabilité** : Permet de comprendre les décisions du modèle

## 📞 Support

Pour toute question ou problème :
1. Vérifiez les logs d'erreur
2. Consultez ce README
3. Testez avec des exemples simples
4. Vérifiez la structure de vos données 