#!/usr/bin/env python3
"""
Analyse des sous-catégories de facturation
"""

import pandas as pd

# Charger les données
df = pd.read_excel('data/Affid/modele/modele.xlsx')
facturation = df[df['catégorie'] == 'Facturation']

print(f"Nombre de tickets Facturation: {len(facturation)}")
print("\n=== RÉPARTITION DES SOUS-CATÉGORIES ===")
print(facturation['sous-catégorie'].value_counts())

print("\n=== EXEMPLES PAR SOUS-CATÉGORIE ===")
for sous_cat in facturation['sous-catégorie'].unique():
    print(f"\n--- {sous_cat} ---")
    exemples = facturation[facturation['sous-catégorie'] == sous_cat]['description'].head(2).tolist()
    for ex in exemples:
        print(f"  • {ex}")

# Analyser les mots-clés par sous-catégorie
print("\n=== MOTS-CLÉS PAR SOUS-CATÉGORIE ===")
for sous_cat in facturation['sous-catégorie'].unique():
    if facturation[facturation['sous-catégorie'] == sous_cat].shape[0] >= 3:  # Au moins 3 exemples
        descriptions = facturation[facturation['sous-catégorie'] == sous_cat]['description'].str.lower().str.cat(sep=' ')
        mots = descriptions.split()
        mots_freq = pd.Series(mots).value_counts().head(5)
        print(f"\n{sous_cat}: {', '.join(mots_freq.index.tolist())}") 