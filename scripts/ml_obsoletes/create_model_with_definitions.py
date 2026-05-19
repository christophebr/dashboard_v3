#!/usr/bin/env python3
"""
Script pour créer un fichier Excel d'entraînement enrichi avec les définitions de contexte
"""

import pandas as pd
import yaml
import os

def load_definitions():
    """Charge les définitions depuis les fichiers YAML"""
    
    # Charger les définitions des catégories principales
    with open('data/Affid/modele/definitions_categories.yaml', 'r', encoding='utf-8') as f:
        categories_def = yaml.safe_load(f)
    
    # Charger les définitions des sous-catégories
    with open('data/Affid/modele/definitions_sous_categories.yaml', 'r', encoding='utf-8') as f:
        sous_categories_def = yaml.safe_load(f)
    
    return categories_def, sous_categories_def

def create_enriched_model():
    """Crée un fichier Excel enrichi avec les définitions de contexte"""
    
    print("📚 Chargement des définitions...")
    categories_def, sous_categories_def = load_definitions()
    
    print("📊 Chargement du fichier modèle existant...")
    # Charger le fichier modèle existant
    df_model = pd.read_excel('data/Affid/modele/modele.xlsx')
    
    print(f"✅ {len(df_model)} exemples chargés")
    print(f"📋 Catégories trouvées: {df_model['catégorie'].unique()}")
    
    # Ajouter les colonnes de définitions
    df_model['definition_categorie'] = df_model['catégorie'].map(categories_def)
    df_model['definition_sous_categorie'] = df_model['sous-catégorie'].map(sous_categories_def)
    
    # Créer une colonne combinée pour l'entraînement enrichi
    df_model['description_enrichie'] = df_model.apply(
        lambda row: f"Catégorie: {row['definition_categorie']} | Sous-catégorie: {row['definition_sous_categorie']} | Description: {row['description']}",
        axis=1
    )
    
    # Créer le dossier s'il n'existe pas
    os.makedirs('data/Affid/modele', exist_ok=True)
    
    # Sauvegarder le fichier enrichi
    output_path = 'data/Affid/modele/modele_avec_definitions.xlsx'
    df_model.to_excel(output_path, index=False)
    
    print(f"✅ Fichier enrichi créé: {output_path}")
    print(f"📊 Structure du fichier:")
    print(f"   - {len(df_model)} exemples")
    print(f"   - {len(df_model.columns)} colonnes")
    print(f"   - Colonnes: {list(df_model.columns)}")
    
    # Afficher quelques exemples
    print(f"\n📋 Exemples d'enrichissement:")
    for i, row in df_model.head(3).iterrows():
        print(f"\n--- Exemple {i+1} ---")
        print(f"Catégorie: {row['catégorie']}")
        print(f"Définition: {row['definition_categorie']}")
        print(f"Description originale: {row['description'][:100]}...")
        print(f"Description enrichie: {row['description_enrichie'][:150]}...")
    
    return df_model

def create_training_summary():
    """Crée un résumé des données d'entraînement"""
    
    df_model = pd.read_excel('data/Affid/modele/modele_avec_definitions.xlsx')
    
    print("\n📊 RÉSUMÉ DES DONNÉES D'ENTRAÎNEMENT")
    print("=" * 50)
    
    # Statistiques par catégorie
    print("\n📈 Répartition par catégorie principale:")
    cat_stats = df_model['catégorie'].value_counts()
    for cat, count in cat_stats.items():
        print(f"  - {cat}: {count} exemples")
    
    # Statistiques par sous-catégorie (pour facturation)
    print("\n📈 Répartition des sous-catégories de facturation:")
    facturation = df_model[df_model['catégorie'] == 'Facturation']
    if not facturation.empty:
        sous_cat_stats = facturation['sous-catégorie'].value_counts()
        for sous_cat, count in sous_cat_stats.items():
            print(f"  - {sous_cat}: {count} exemples")
    
    # Longueur moyenne des descriptions
    df_model['longueur_desc'] = df_model['description'].str.len()
    print(f"\n📏 Statistiques des descriptions:")
    print(f"  - Longueur moyenne: {df_model['longueur_desc'].mean():.1f} caractères")
    print(f"  - Longueur min: {df_model['longueur_desc'].min()} caractères")
    print(f"  - Longueur max: {df_model['longueur_desc'].max()} caractères")
    
    # Longueur moyenne des descriptions enrichies
    df_model['longueur_enrichie'] = df_model['description_enrichie'].str.len()
    print(f"\n📏 Statistiques des descriptions enrichies:")
    print(f"  - Longueur moyenne: {df_model['longueur_enrichie'].mean():.1f} caractères")
    print(f"  - Longueur min: {df_model['longueur_enrichie'].min()} caractères")
    print(f"  - Longueur max: {df_model['longueur_enrichie'].max()} caractères")

if __name__ == "__main__":
    print("🚀 CRÉATION DU MODÈLE AVEC DÉFINITIONS")
    print("=" * 50)
    
    # Créer le fichier enrichi
    df_enriched = create_enriched_model()
    
    # Créer le résumé
    create_training_summary()
    
    print("\n✅ PROCESSUS TERMINÉ")
    print("\n📁 Fichiers créés:")
    print("  - data/Affid/modele/modele_avec_definitions.xlsx (fichier enrichi)")
    print("  - data/Affid/modele/definitions_categories.yaml (définitions catégories)")
    print("  - data/Affid/modele/definitions_sous_categories.yaml (définitions sous-catégories)")
    
    print("\n🎯 Prochaines étapes:")
    print("  1. Utiliser le fichier 'modele_avec_definitions.xlsx' pour l'entraînement")
    print("  2. Modifier les scripts d'entraînement pour utiliser la colonne 'description_enrichie'")
    print("  3. Tester les performances du modèle enrichi") 