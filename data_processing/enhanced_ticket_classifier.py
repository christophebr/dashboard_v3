#!/usr/bin/env python3
"""
Module pour charger et utiliser le modèle de classification enrichi avec définitions
"""

import pickle
import os
import pandas as pd
import numpy as np
from typing import List, Dict, Any

class EnhancedTicketClassifier:
    def __init__(self):
        self.vectorizer = None
        self.classifier = None
        self.categories = None
        self.use_enriched_descriptions = True
        
    def preprocess_text(self, text):
        """Prétraitement du texte"""
        if pd.isna(text) or text == '':
            return ''
        
        text = str(text).lower()
        # Suppression des caractères spéciaux mais garder les accents
        import re
        text = re.sub(r'[^\w\sàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def load_model(self, file_path="data/Affid/modele/enhanced_ticket_classifier.pkl"):
        """Charge un modèle entraîné"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Modèle non trouvé: {file_path}")
            
        with open(file_path, 'rb') as f:
            model_data = pickle.load(f)
        
        self.vectorizer = model_data['vectorizer']
        self.classifier = model_data['classifier']
        self.categories = model_data['categories']
        
        # Gestion de la compatibilité avec les anciens modèles
        if 'sous_categories' in model_data:
            print("⚠️ Modèle avec sous-catégories détecté (ignorées)")
        else:
            print("✅ Modèle simplifié (sans sous-catégories)")
        
        self.use_enriched_descriptions = model_data.get('use_enriched_descriptions', True)
        
        print(f"✅ Modèle enrichi chargé: {file_path}")
        print(f"📊 {len(self.categories)} catégories principales disponibles")
        print(f"🔧 Utilisation des descriptions enrichies: {self.use_enriched_descriptions}")
    
    def predict(self, descriptions: List[str]) -> List[Dict[str, Any]]:
        """Prédit les catégories pour de nouvelles descriptions"""
        if self.vectorizer is None or self.classifier is None:
            raise ValueError("Le modèle doit être chargé avant de faire des prédictions")
        
        # Prétraitement
        descriptions_clean = [self.preprocess_text(desc) for desc in descriptions]
        
        # Vectorisation
        X_new = self.vectorizer.transform(descriptions_clean)
        
        # Prédiction
        predictions = self.classifier.predict(X_new)
        probabilities = self.classifier.predict_proba(X_new)
        
        # Formatage des résultats
        results = []
        for i, (pred, prob) in enumerate(zip(predictions, probabilities)):
            # Trouver l'index de la prédiction
            pred_idx = list(self.classifier.classes_).index(pred)
            confidence = prob[pred_idx]
            
            # Créer un dictionnaire des scores par catégorie
            scores_dict = {cat: prob[j] for j, cat in enumerate(self.classifier.classes_)}
            
            results.append({
                'categorie_predite': pred,
                'confiance': confidence,
                'scores_par_categorie': scores_dict
            })
        
        return results

def load_enhanced_ticket_classifier():
    """
    Fonction de chargement du modèle enrichi pour compatibilité avec le système existant
    """
    try:
        # Essayer de charger le modèle enrichi
        classifier = EnhancedTicketClassifier()
        classifier.load_model("data/Affid/modele/enhanced_ticket_classifier.pkl")
        print("✅ Modèle enrichi avec définitions chargé")
        return classifier
    except FileNotFoundError:
        print("⚠️ Modèle enrichi non trouvé, utilisation du modèle classique")
        # Fallback vers le modèle classique
        from data_processing.ticket_classifier import load_ticket_classifier
        return load_ticket_classifier()

def predict_with_enhanced_model(descriptions: List[str], use_enriched: bool = True) -> List[Dict[str, Any]]:
    """
    Fonction de prédiction qui utilise le modèle enrichi si disponible
    
    Parameters:
    -----------
    descriptions : List[str]
        Liste des descriptions à catégoriser
    use_enriched : bool
        Si True, utilise le modèle enrichi avec définitions
        
    Returns:
    --------
    List[Dict[str, Any]]
        Liste des prédictions avec catégorie, confiance et scores
    """
    
    if use_enriched:
        try:
            classifier = load_enhanced_ticket_classifier()
            if hasattr(classifier, 'use_enriched_descriptions') and classifier.use_enriched_descriptions:
                print("🎯 Utilisation du modèle enrichi avec définitions de contexte")
            else:
                print("🎯 Utilisation du modèle classique")
            return classifier.predict(descriptions)
        except Exception as e:
            print(f"⚠️ Erreur avec le modèle enrichi: {e}")
            print("🔄 Fallback vers le modèle classique...")
    
    # Fallback vers le modèle classique
    from data_processing.ticket_classifier import load_ticket_classifier
    classifier = load_ticket_classifier()
    return classifier.predict(descriptions)

def get_model_info():
    """
    Retourne les informations sur le modèle disponible
    """
    info = {
        'enhanced_model_available': False,
        'enhanced_model_path': "data/Affid/modele/enhanced_ticket_classifier.pkl",
        'classic_model_available': False,
        'classic_model_path': "data/Affid/modele/ticket_classifier.pkl",
        'definitions_available': False,
        'definitions_path': "data/Affid/modele/definitions_categories.yaml"
    }
    
    # Vérifier le modèle enrichi
    if os.path.exists(info['enhanced_model_path']):
        info['enhanced_model_available'] = True
        try:
            classifier = EnhancedTicketClassifier()
            classifier.load_model(info['enhanced_model_path'])
            info['enhanced_categories_count'] = len(classifier.categories) if classifier.categories else 0
            info['enhanced_uses_definitions'] = classifier.use_enriched_descriptions
        except Exception as e:
            print(f"⚠️ Erreur lors du chargement du modèle enrichi: {e}")
            info['enhanced_model_available'] = False
    
    # Vérifier le modèle classique
    if os.path.exists(info['classic_model_path']):
        info['classic_model_available'] = True
    
    # Vérifier les définitions
    if os.path.exists(info['definitions_path']):
        info['definitions_available'] = True
    
    return info

if __name__ == "__main__":
    # Test du module
    print("🧪 TEST DU MODULE ENHANCED TICKET CLASSIFIER")
    print("=" * 50)
    
    # Informations sur les modèles
    info = get_model_info()
    print("\n📊 INFORMATIONS SUR LES MODÈLES:")
    for key, value in info.items():
        print(f"  {key}: {value}")
    
    # Test de prédiction si le modèle est disponible
    if info['enhanced_model_available']:
        print("\n🧪 TEST DE PRÉDICTION:")
        test_descriptions = [
            "Problème de connexion à l'application",
            "Question sur la facturation CCAM",
            "L'interface est lente"
        ]
        
        try:
            predictions = predict_with_enhanced_model(test_descriptions)
            for i, (desc, pred) in enumerate(zip(test_descriptions, predictions), 1):
                print(f"\n{i}. Description: {desc}")
                print(f"   Catégorie: {pred['categorie_predite']}")
                print(f"   Confiance: {pred['confiance']:.2f}")
        except Exception as e:
            print(f"❌ Erreur lors du test: {e}")
    else:
        print("\n❌ Aucun modèle enrichi disponible")
        print("💡 Exécutez 'python train_model_with_definitions.py' pour créer le modèle") 