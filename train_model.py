#!/usr/bin/env python3
"""
Script d'entraînement des modèles de classification des tickets
"""

import sys
import os

# Ajouter le répertoire courant au path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_processing.ticket_classifier import train_ticket_classifier
from data_processing.facturation_classifier import train_facturation_classifier

def main():
    """
    Fonction principale pour entraîner les modèles
    """
    print("🚀 Démarrage de l'entraînement des modèles de classification")
    print("=" * 80)
    
    try:
        # Entraîner le modèle principal de classification des tickets
        print("\n📋 ENTRAÎNEMENT DU MODÈLE PRINCIPAL DE CLASSIFICATION")
        print("-" * 50)
        classifier_tickets, accuracy_tickets = train_ticket_classifier()
        
        print("\n" + "=" * 80)
        print(f"✅ Entraînement du modèle principal terminé!")
        print(f"📊 Précision finale: {accuracy_tickets:.3f}")
        
        # Test avec quelques exemples pour le modèle principal
        print("\n🧪 Test du modèle principal avec quelques exemples:")
        test_examples = [
            "Je n'arrive pas à me connecter avec ma carte CPS",
            "L'application est très lente lors de la saisie des actes",
            "Erreur lors de la télétransmission des feuilles de soins",
            "Problème d'affichage sur l'écran de saisie",
            "Impossible de sauvegarder les données du patient"
        ]
        
        for example in test_examples:
            classifier_tickets.evaluate_sample(example)
            print("-" * 40)
        
        # Afficher les mots les plus importants pour le modèle principal
        print("\n🔍 Mots les plus importants pour la classification principale:")
        importance_df = classifier_tickets.get_feature_importance(top_n=15)
        print(importance_df.to_string(index=False))
        
        # Entraîner le modèle spécialisé de facturation
        print("\n\n💶 ENTRAÎNEMENT DU MODÈLE SPÉCIALISÉ DE FACTURATION")
        print("-" * 50)
        classifier_facturation, accuracy_facturation = train_facturation_classifier()
        
        print("\n" + "=" * 80)
        print(f"✅ Entraînement du modèle de facturation terminé!")
        print(f"📊 Précision finale: {accuracy_facturation:.3f}")
        
        # Test avec quelques exemples pour le modèle de facturation
        print("\n🧪 Test du modèle de facturation avec quelques exemples:")
        test_examples_facturation = [
            "Problème avec la cotation CCAM QZM001",
            "Exonération ALD pour le patient",
            "Téléconsultation à 50 euros",
            "Majoration MD avec VSP",
            "PAV pour patient hospitalisé"
        ]
        
        for example in test_examples_facturation:
            result = classifier_facturation.predict(example)
            print(f"📝 Description: {result['description']}")
            print(f"🎯 Sous-catégorie prédite: {result['sous_categorie_predite']}")
            print(f"📊 Confiance: {result['confiance']:.3f}")
            print("-" * 40)
        
        # Résumé final
        print("\n" + "=" * 80)
        print("📊 RÉSUMÉ DE L'ENTRAÎNEMENT")
        print("=" * 80)
        print(f"✅ Modèle principal (tickets): {accuracy_tickets:.3f}")
        print(f"✅ Modèle facturation: {accuracy_facturation:.3f}")
        print(f"📈 Amélioration moyenne: {((accuracy_tickets + accuracy_facturation) / 2):.3f}")
        
        print("\n🔑 Mots-clés intégrés:")
        print(f"  - Modèle principal: {len(classifier_tickets.mots_cles_dict)} catégories")
        print(f"  - Modèle facturation: {len(classifier_facturation.mots_cles_dict)} catégories")
        
        print("\n💾 Modèles sauvegardés:")
        print(f"  - {classifier_tickets.model_path}")
        print(f"  - {classifier_facturation.model_path}")
        
    except FileNotFoundError as e:
        print(f"❌ Erreur: Fichier non trouvé - {e}")
        print("📁 Assurez-vous que les fichiers suivants existent:")
        print("   - data/Affid/modele/modele.xlsx")
        print("   - data/Affid/modele/Mots_cles.xlsx")
        print("   - data/Affid/modele/Mots_cles_ssi.xlsx")
        return 1
    except Exception as e:
        print(f"❌ Erreur lors de l'entraînement: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 