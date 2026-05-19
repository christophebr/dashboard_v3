# 🚨 **Nouveau problème identifié : Agents absents**

## 🔍 **Problème décrit par l'utilisateur**

> "Ca ne correspond toujours pas. Je vois un autre probleme, lorsque l'agent est absent, tu mets dans l'historique des scores la valeur a 70"

## 🔍 **Analyse du problème**

Après investigation, j'ai identifié plusieurs problèmes potentiels :

### 1. **Gestion des agents absents dans l'historique**

Dans la fonction `historique_scores_total`, quand un agent n'a pas de données pour une semaine :
- La fonction `df_compute_ticket_appels_metrics` retourne toujours une ligne pour chaque agent
- Même avec des valeurs à 0, cela génère un score calculé
- Le graphique affiche ce score au lieu de ne rien afficher

### 2. **Calcul du score avec des valeurs à 0**

Quand un agent a des valeurs à 0 :
```python
# Données de l'agent absent
nb_appels = 0
nb_tickets = 0
volume_total = 0

# Calcul des scores
score_volume = min(100, (0 / 25) * 100) = 0
score_repartition = 0  # car volume_total = 0
score_comparaison = min(100, (0 / 25) * 100) = 0
score_taux_appels_entrants = 0  # car nb_appels = 0

# Score final
score_final = (0 * 0.55) + (0 * 0.15) + (0 * 0.15) + (0 * 0.15) = 0
```

**Le score devrait être 0, pas 70 !**

## 🛠️ **Solutions appliquées**

### **Solution 1 : Gestion des agents absents dans le graphique**

**Fichier :** `data_processing/kpi_generation.py`

**Modification :** Ajout d'une logique pour gérer les agents sans données

```python
# AVANT
for i, agent in enumerate(agents_n1):
    agent_data = df_historique[df_historique['Agent'] == agent]
    
    if not agent_data.empty:
        fig.add_trace(...)

# APRÈS
for i, agent in enumerate(agents_n1):
    agent_data = df_historique[df_historique['Agent'] == agent]
    
    if not agent_data.empty:
        fig.add_trace(...)
    else:
        # Si l'agent n'a pas de données, ajouter un point invisible
        # pour éviter les erreurs mais ne pas afficher de ligne
        fig.add_trace(
            go.Scatter(
                x=[weeks_to_process[0]],
                y=[None],  # Pas de valeur
                mode='markers',
                name=agent,
                marker=dict(size=0),  # Point invisible
                showlegend=False
            ),
            row=i+1, col=1
        )
```

### **Solution 2 : Script de debug**

**Fichier :** `debug_scores.py`

Création d'un script pour :
- Tester le calcul des scores avec des valeurs à 0
- Comparer les scores entre tableau et historique
- Identifier les différences

## 🔍 **Hypothèses sur le score de 70**

Le score de 70 mentionné pourrait venir de :

1. **Ligne de seuil** : La ligne de seuil à 70% pourrait être confondue avec un score
2. **Cache obsolète** : Les anciens calculs avec objectif_total=30 pourraient être en cache
3. **Données réelles** : L'agent pourrait avoir des données réelles qui donnent un score de 70
4. **Autre logique** : Une autre partie du code pourrait attribuer un score par défaut

## 🧪 **Tests à effectuer**

1. **Vider le cache** de l'application
2. **Relancer l'application**
3. **Vérifier les données réelles** de l'agent absent
4. **Exécuter le script de debug** : `python debug_scores.py`

## 📋 **Prochaines étapes**

1. **Identifier la source exacte** du score de 70
2. **Vérifier les données réelles** de l'agent absent
3. **S'assurer que les agents absents** n'affichent pas de score
4. **Tester avec des données réelles** de l'application

## 🔧 **Commandes de test**

```bash
# Vider le cache de Streamlit
rm -rf ~/.streamlit/cache/

# Exécuter le script de debug
python debug_scores.py

# Relancer l'application
streamlit run app.py
```

## 📊 **Résultat attendu**

- **Agents avec données** : Scores cohérents entre tableau et historique
- **Agents absents** : Pas de score affiché dans l'historique
- **Pas de score de 70** pour les agents sans activité 