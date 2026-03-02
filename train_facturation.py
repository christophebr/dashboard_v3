#!/usr/bin/env python3
"""
Script d'entraînement du modèle spécialisé de facturation
"""

import sys
import os

# Ajouter le répertoire courant au path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_processing.facturation_classifier import train_facturation_classifier

def main():
    """
    Fonction principale pour entraîner le modèle de facturation
    """
    print("🚀 Démarrage de l'entraînement du modèle spécialisé de facturation")
    print("=" * 70)
    
    try:
        # Entraîner le modèle
        classifier, accuracy = train_facturation_classifier()
        
        print("\n" + "=" * 70)
        print(f"✅ Entraînement terminé avec succès!")
        print(f"📊 Précision finale: {accuracy:.3f}")
        
        # Test avec des exemples spécifiques
        print("\n🧪 Test du modèle avec des exemples de facturation:")
        test_examples = [
            "Problème avec la cotation CCAM QZM001",
            "Comment appliquer une exonération ALD ?",
            "La téléconsultation est facturée 30€ au lieu de 50€",
            "Impossible d'appliquer la majoration MD avec VSP",
            "Patient hospitalisé avec PAV à 24€",
            "Problème de dépassement d'honoraires",
            "Comment facturer un patient étranger ?",
            "Taux de prise en charge incorrect sur la FSE"
        ]
        
        for example in test_examples:
            result = classifier.predict(example)
            print(f"\n📝 {example}")
            print(f"🎯 Sous-catégorie: {result['sous_categorie_predite']}")
            print(f"📊 Confiance: {result['confiance']:.3f}")
            print("-" * 50)
        
        # Afficher les sous-catégories disponibles
        print(f"\n📋 Sous-catégories disponibles ({len(classifier.sous_categories)}):")
        for i, sous_cat in enumerate(classifier.sous_categories, 1):
            print(f"  {i:2d}. {sous_cat}")
        
    except FileNotFoundError as e:
        print(f"❌ Erreur: Fichier non trouvé - {e}")
        print("📁 Assurez-vous que le fichier 'data/Affid/modele/modele.xlsx' existe")
        return 1
    except Exception as e:
        print(f"❌ Erreur lors de l'entraînement: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 