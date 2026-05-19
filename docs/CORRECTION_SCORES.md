# 🔧 Correction de l'incohérence des scores - Page Agent

## 🚨 **Problème identifié**

Sur la page agent, les **points du graphique de l'historique des scores** ne correspondaient pas aux **chiffres du tableau** de scoring automatique.

## 🔍 **Cause racine**

Le problème venait du fait que **deux calculs différents** étaient utilisés pour les scores :

### 1. **Tableau des scores** (`app.py` lignes 610-620)
```python
df_conforme['score_performance'] = df_conforme.apply(
    lambda row: calculate_performance_score(
        row,
        objectif_total=objectif_total,        # ← Paramètre personnalisable (25 par défaut)
        ratio_appels=ratio_appels,            # ← Paramètre personnalisable (0.7 par défaut)
        ratio_tickets=ratio_tickets,          # ← Paramètre personnalisable (0.3 par défaut)
        objectif_taux_service=objectif_taux_service
    ),
    axis=1
)
```

### 2. **Graphique historique des scores** (`kpi_generation.py` ligne 1878)
```python
df_historique['score_performance'] = df_historique.apply(
    lambda row: calculate_performance_score(
        row,
        objectif_total=30,                    # ← Paramètre fixe à 30 ❌
        ratio_appels=0.7,                     # ← Paramètre fixe à 0.7
        ratio_tickets=0.3,                    # ← Paramètre fixe à 0.3
        objectif_taux_service=0.70
    ),
    axis=1
)
```

## 🛠️ **Solution appliquée**

### **Étape 1 : Modification de la fonction `historique_scores_total`**

**Fichier :** `data_processing/kpi_generation.py`

**Changements :**
1. **Ajout des paramètres de scoring** à la signature de la fonction
2. **Utilisation des mêmes valeurs par défaut** que le tableau

```python
# AVANT
def historique_scores_total(agents_n1, df_tickets, df_support, date_debut=None, nb_semaines=None):

# APRÈS  
def historique_scores_total(agents_n1, df_tickets, df_support, date_debut=None, nb_semaines=None, objectif_total=25, ratio_appels=0.7, ratio_tickets=0.3, objectif_taux_service=0.70):
```

### **Étape 2 : Mise à jour de l'appel dans `app.py`**

**Fichier :** `app.py`

**Changements :**
1. **Passage des paramètres personnalisables** à la fonction `historique_scores_total`
2. **Mise à jour de la clé de cache** pour inclure les paramètres

```python
# AVANT
fig_historique = historique_scores_total(agents_scores, df_tickets_filtered, df_support_filtered)

# APRÈS
fig_historique = historique_scores_total(
    agents_scores, 
    df_tickets_filtered, 
    df_support_filtered,
    objectif_total=objectif_total,
    ratio_appels=ratio_appels,
    ratio_tickets=ratio_tickets,
    objectif_taux_service=objectif_taux_service
)
```

### **Étape 3 : Mise à jour de la clé de cache**

```python
# AVANT
cache_key_historique = f'historique_scores_{periode_selectbox}_{hash(str(df_tickets_filtered.shape))}_{hash(str(df_support_filtered.shape))}_{hash(str(agents_scores))}'

# APRÈS
cache_key_historique = f'historique_scores_{periode_selectbox}_{objectif_total}_{ratio_appels}_{ratio_tickets}_{objectif_taux_service}_{hash(str(df_tickets_filtered.shape))}_{hash(str(df_support_filtered.shape))}_{hash(str(agents_scores))}'
```

## ✅ **Résultat**

Maintenant, **les scores du tableau et du graphique historique utilisent exactement les mêmes paramètres** :

- **Objectif total** : 25 (au lieu de 30)
- **Ratio appels** : 0.7
- **Ratio tickets** : 0.3  
- **Objectif taux service** : 0.70

## 🧪 **Test de validation**

Un script de test `test_scores.py` a été créé pour vérifier la cohérence des scores entre les deux calculs.

## 📋 **Impact**

- ✅ **Cohérence** : Les scores du tableau et du graphique correspondent maintenant
- ✅ **Flexibilité** : Les paramètres de scoring sont personnalisables et appliqués partout
- ✅ **Cache intelligent** : Le cache prend en compte les paramètres de scoring
- ✅ **Maintenabilité** : Plus facile de modifier les paramètres de scoring

## 🔄 **Pour tester**

1. Relancer l'application
2. Aller sur la page "Agents"
3. Vérifier que les scores du tableau correspondent aux points du graphique historique
4. Modifier les paramètres de scoring dans la sidebar et vérifier que les deux s'actualisent 