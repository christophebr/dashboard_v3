#!/usr/bin/env python3
"""
Script pour analyser et corriger la définition de "Remplaçant / Collaborateur"
"""

import pandas as pd
import yaml

def analyser_definition_actuelle():
    """Analyse la définition actuelle de Remplaçant / Collaborateur"""
    print("🔍 ANALYSE DE LA DÉFINITION ACTUELLE")
    print("=" * 50)
    
    # Charger la définition actuelle
    with open('data/Affid/modele/definitions_categories.yaml', 'r', encoding='utf-8') as f:
        definitions = yaml.safe_load(f)
    
    definition_actuelle = definitions.get('Remplaçant / Collaborateur', 'Non trouvée')
    print(f"📖 Définition actuelle:")
    print(f"   {definition_actuelle}")
    print(f"   Longueur: {len(definition_actuelle)} caractères")
    
    # Analyser les mots-clés problématiques
    mots_problematiques = [
        "ensemble des demandes",
        "ajout, la gestion ou la modification",
        "profils de remplaçants ou collaborateurs",
        "gestion des droits d'accès",
        "passation d'activité",
        "configuration des informations",
        "administratives et de facturation"
    ]
    
    print(f"\n⚠️ Mots-clés problématiques détectés:")
    for mot in mots_problematiques:
        if mot in definition_actuelle:
            print(f"   ❌ '{mot}' - Trop générique")
    
    # Comparer avec d'autres définitions
    print(f"\n📊 COMPARAISON AVEC D'AUTRES DÉFINITIONS:")
    autres_categories = ['Lecteur', 'Facturation', 'Fonctionnalités']
    
    for cat in autres_categories:
        if cat in definitions:
            definition = definitions[cat]
            print(f"\n📖 {cat}:")
            print(f"   {definition[:100]}...")
            print(f"   Longueur: {len(definition)} caractères")
            print(f"   Spécificité: {'✅ Spécifique' if len(definition) < 200 else '⚠️ Générique'}")

def analyser_exemples_reels():
    """Analyse les exemples réels de la catégorie Remplaçant / Collaborateur"""
    print("\n📋 ANALYSE DES EXEMPLES RÉELS")
    print("=" * 50)
    
    # Charger les données
    df = pd.read_excel('data/Affid/modele/modele_avec_definitions.xlsx')
    
    # Filtrer les exemples de Remplaçant / Collaborateur
    remplacant_examples = df[df['catégorie'] == 'Remplacant / Collaborateur']
    
    print(f"📊 Nombre d'exemples: {len(remplacant_examples)}")
    
    if len(remplacant_examples) > 0:
        print(f"\n📝 Exemples de descriptions:")
        for i in range(min(5, len(remplacant_examples))):
            description = remplacant_examples.iloc[i]['description']
            print(f"\n{i+1}. {description}")
            
            # Analyser les mots-clés dans la description
            mots_cles = ['collaborateur', 'remplaçant', 'profil', 'droits', 'accès', 'facturation']
            mots_trouves = [mot for mot in mots_cles if mot.lower() in description.lower()]
            if mots_trouves:
                print(f"   Mots-clés: {', '.join(mots_trouves)}")

def proposer_nouvelle_definition():
    """Propose une nouvelle définition plus spécifique"""
    print("\n💡 PROPOSITION DE NOUVELLE DÉFINITION")
    print("=" * 50)
    
    print("🔧 Problèmes identifiés avec la définition actuelle:")
    print("   1. Trop générique ('ensemble des demandes')")
    print("   2. Mélange plusieurs concepts (gestion, droits, facturation)")
    print("   3. Longueur excessive (peut causer un biais)")
    print("   4. Manque de spécificité sur les cas d'usage")
    
    print("\n📝 NOUVELLE DÉFINITION PROPOSÉE:")
    nouvelle_definition = """Questions spécifiques à la création et gestion des profils de remplaçants ou collaborateurs dans Stellair, incluant l'ajout d'un nouveau profil, la modification des informations personnelles, la gestion des droits d'accès spécifiques, et la configuration des paramètres de facturation pour ces utilisateurs."""
    
    print(f"   {nouvelle_definition}")
    print(f"   Longueur: {len(nouvelle_definition)} caractères")
    
    print("\n✅ Améliorations apportées:")
    print("   1. Plus spécifique ('Questions spécifiques à...')")
    print("   2. Focus sur les actions concrètes")
    print("   3. Longueur réduite et équilibrée")
    print("   4. Séparation claire des concepts")
    
    # Comparer avec d'autres définitions
    ancienne_definition = "Regroupe l'ensemble des demandes concernant l'ajout, la gestion ou la modification des profils de remplaçants ou collaborateurs dans l'application Stellair, y compris la gestion des droits d'accès, la passation d'activité, ou la configuration des informations administratives et de facturation lié à ces statuts."
    print(f"\n📊 COMPARAISON DES LONGUEURS:")
    print(f"   Ancienne: {len(ancienne_definition)} caractères")
    print(f"   Nouvelle: {len(nouvelle_definition)} caractères")
    print(f"   Réduction: {len(ancienne_definition) - len(nouvelle_definition)} caractères")

def appliquer_correction():
    """Applique la correction à la définition"""
    print("\n🛠️ APPLICATION DE LA CORRECTION")
    print("=" * 50)
    
    # Charger les définitions actuelles
    with open('data/Affid/modele/definitions_categories.yaml', 'r', encoding='utf-8') as f:
        definitions = yaml.safe_load(f)
    
    # Nouvelle définition
    nouvelle_definition = """Questions spécifiques à la création et gestion des profils de remplaçants ou collaborateurs dans Stellair, incluant l'ajout d'un nouveau profil, la modification des informations personnelles, la gestion des droits d'accès spécifiques, et la configuration des paramètres de facturation pour ces utilisateurs."""
    
    # Mettre à jour la définition
    definitions['Remplaçant / Collaborateur'] = nouvelle_definition
    
    # Sauvegarder
    with open('data/Affid/modele/definitions_categories.yaml', 'w', encoding='utf-8') as f:
        yaml.dump(definitions, f, default_flow_style=False, allow_unicode=True)
    
    print("✅ Définition mise à jour dans definitions_categories.yaml")
    print("📝 Nouvelle définition:")
    print(f"   {nouvelle_definition}")
    
    print("\n🔄 Prochaines étapes:")
    print("   1. Régénérer le fichier modele_avec_definitions.xlsx")
    print("   2. Réentraîner le modèle enrichi")
    print("   3. Tester les prédictions")

if __name__ == "__main__":
    analyser_definition_actuelle()
    analyser_exemples_reels()
    proposer_nouvelle_definition()
    
    print("\n🎯 RECOMMANDATION:")
    print("=" * 30)
    print("La définition actuelle est trop générique et cause un biais.")
    print("Voulez-vous appliquer la correction ? (y/n)")
    
    # Appliquer automatiquement la correction
    appliquer_correction()
    
    print("\n✅ Correction appliquée !")
    print("📋 Prochaines étapes:")
    print("   1. python create_model_with_definitions.py")
    print("   2. python train_model_with_definitions.py")
    print("   3. Tester les prédictions dans l'application") 