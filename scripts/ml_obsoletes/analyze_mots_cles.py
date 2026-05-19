#!/usr/bin/env python3
"""
Analyse du fichier Mots_cles.xlsx
"""

import pandas as pd

# Charger le fichier
df = pd.read_excel('data/Affid/modele/Mots_cles.xlsx')

print("=== ANALYSE DU FICHIER MOTS_CLES ===")
print(f"Nombre total de mots-clés: {len(df)}")
print(f"Colonnes: {df.columns.tolist()}")

print("\n=== CATÉGORIES DISPONIBLES ===")
categories = df['Categorie'].value_counts()
print(f"Nombre de catégories: {len(categories)}")
print("\nTop 20 catégories:")
for i, (cat, count) in enumerate(categories.head(20).items(), 1):
    print(f"{i:2d}. {cat}: {count} mots")

print("\n=== EXEMPLES DE MOTS PAR CATÉGORIE ===")
for cat in categories.head(5).index:
    mots_cat = df[df['Categorie'] == cat]['Mots'].head(10).tolist()
    print(f"\n{cat}:")
    print(f"  {mots_cat}")

print("\n=== STATISTIQUES ===")
print(f"Moyenne de mots par catégorie: {categories.mean():.1f}")
print(f"Médiane de mots par catégorie: {categories.median():.1f}")
print(f"Catégorie avec le plus de mots: {categories.index[0]} ({categories.iloc[0]} mots)")
print(f"Catégorie avec le moins de mots: {categories.index[-1]} ({categories.iloc[-1]} mots)") 