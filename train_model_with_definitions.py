#!/usr/bin/env python3
"""
Script d'entraînement amélioré utilisant les définitions de contexte
"""

import pandas as pd
import numpy as np
import os
import pickle
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score
import warnings
warnings.filterwarnings('ignore')

class EnhancedTicketClassifier:
    def __init__(self):
        self.vectorizer = None
        self.classifier = None
        self.categories = None
        self.use_enriched_descriptions = False  # Utiliser les descriptions originales
        
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
    
    def load_data(self, file_path="data/Affid/modele/modele_avec_definitions.xlsx"):
        """Charge les données enrichies"""
        print("📊 Chargement des données enrichies...")
        df = pd.read_excel(file_path)
        
        # Vérification des colonnes (sous-catégories ignorées)
        required_columns = ['catégorie', 'description', 'description_enrichie']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Colonnes manquantes: {missing_columns}")
        
        # Nettoyage des données
        df = df.dropna(subset=['catégorie'])
        
        # Choisir la colonne de description à utiliser
        if self.use_enriched_descriptions:
            df['text_clean'] = df['description_enrichie'].apply(self.preprocess_text)
            print("✅ Utilisation des descriptions enrichies avec définitions")
        else:
            df['text_clean'] = df['description'].apply(self.preprocess_text)
            print("✅ Utilisation des descriptions originales")
        
        # Filtrage des descriptions vides
        df = df[df['text_clean'] != '']
        
        print(f"✅ {len(df)} descriptions valides chargées")
        print(f"📈 Répartition des catégories:")
        print(df['catégorie'].value_counts())
        
        return df
    
    def train(self, file_path="data/Affid/modele/modele_avec_definitions.xlsx"):
        """Entraîne le modèle avec les descriptions enrichies"""
        
        # Chargement des données
        df = self.load_data(file_path)
        
        # Préparation des données (sous-catégories ignorées)
        X_text = df['text_clean']
        y_categories = df['catégorie']
        
        # Sauvegarde des catégories uniques
        self.categories = sorted(y_categories.unique())
        
        print(f"🎯 {len(self.categories)} catégories principales")
        print(f"📋 Sous-catégories ignorées pour simplifier le modèle")
        
        # Vectorisation TF-IDF
        print("🔧 Création du vectoriseur TF-IDF...")
        self.vectorizer = TfidfVectorizer(
            max_features=5000,
            ngram_range=(1, 2),
            stop_words='english',
            min_df=2,
            max_df=0.95
        )
        
        X_tfidf = self.vectorizer.fit_transform(X_text)
        print(f"✅ Vectorisation terminée: {X_tfidf.shape[1]} features")
        
        # Division train/test (sans stratification si certaines catégories ont trop peu d'exemples)
        try:
            X_train, X_test, y_train, y_test = train_test_split(
                X_tfidf, y_categories, test_size=0.2, random_state=42, stratify=y_categories
            )
            print("✅ Division train/test avec stratification")
        except ValueError:
            print("⚠️ Stratification impossible, division simple")
            X_train, X_test, y_train, y_test = train_test_split(
                X_tfidf, y_categories, test_size=0.2, random_state=42
            )
        
        # Entraînement du classifieur
        print("🤖 Entraînement du classifieur Random Forest...")
        self.classifier = RandomForestClassifier(
            n_estimators=100,
            max_depth=20,
            random_state=42,
            n_jobs=-1
        )
        
        self.classifier.fit(X_train, y_train)
        
        # Évaluation
        y_pred = self.classifier.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        
        print(f"✅ Entraînement terminé")
        print(f"📊 Précision sur l'ensemble de test: {accuracy:.3f}")
        
        # Validation croisée
        print("🔄 Validation croisée...")
        cv_scores = cross_val_score(self.classifier, X_tfidf, y_categories, cv=5)
        print(f"📊 Précision moyenne (CV): {cv_scores.mean():.3f} (+/- {cv_scores.std() * 2:.3f})")
        
        # Rapport détaillé
        print("\n📋 RAPPORT DE CLASSIFICATION:")
        print(classification_report(y_test, y_pred))
        
        return accuracy, cv_scores.mean()
    
    def predict(self, descriptions):
        """Prédit les catégories pour de nouvelles descriptions"""
        if self.vectorizer is None or self.classifier is None:
            raise ValueError("Le modèle doit être entraîné avant de faire des prédictions")
        
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
    
    def save_model(self, file_path="data/Affid/modele/enhanced_ticket_classifier.pkl"):
        """Sauvegarde le modèle entraîné"""
        model_data = {
            'vectorizer': self.vectorizer,
            'classifier': self.classifier,
            'categories': self.categories,
            'use_enriched_descriptions': self.use_enriched_descriptions
        }
        
        with open(file_path, 'wb') as f:
            pickle.dump(model_data, f)
        
        print(f"✅ Modèle sauvegardé: {file_path}")
    
    def load_model(self, file_path="data/Affid/modele/enhanced_ticket_classifier.pkl"):
        """Charge un modèle entraîné"""
        with open(file_path, 'rb') as f:
            model_data = pickle.load(f)
        
        self.vectorizer = model_data['vectorizer']
        self.classifier = model_data['classifier']
        self.categories = model_data['categories']
        self.use_enriched_descriptions = model_data.get('use_enriched_descriptions', True)
        
        print(f"✅ Modèle chargé: {file_path}")
        print(f"📊 {len(self.categories)} catégories principales disponibles")

def compare_models():
    """Compare les performances avec et sans définitions enrichies"""
    
    print("🔬 COMPARAISON DES MODÈLES")
    print("=" * 50)
    
    # Test avec descriptions enrichies
    print("\n1️⃣ Test avec descriptions enrichies:")
    classifier_enriched = EnhancedTicketClassifier()
    classifier_enriched.use_enriched_descriptions = True
    accuracy_enriched, cv_enriched = classifier_enriched.train()
    
    # Test avec descriptions originales
    print("\n2️⃣ Test avec descriptions originales:")
    classifier_original = EnhancedTicketClassifier()
    classifier_original.use_enriched_descriptions = False
    accuracy_original, cv_original = classifier_original.train()
    
    # Comparaison
    print("\n📊 COMPARAISON DES RÉSULTATS:")
    print("=" * 30)
    print(f"Descriptions enrichies:")
    print(f"  - Précision test: {accuracy_enriched:.3f}")
    print(f"  - Précision CV: {cv_enriched:.3f}")
    print(f"\nDescriptions originales:")
    print(f"  - Précision test: {accuracy_original:.3f}")
    print(f"  - Précision CV: {cv_original:.3f}")
    
    improvement = ((accuracy_enriched - accuracy_original) / accuracy_original) * 100
    print(f"\n📈 Amélioration: {improvement:+.1f}%")
    
    # Sauvegarder le meilleur modèle
    if accuracy_enriched > accuracy_original:
        classifier_enriched.save_model()
        print("✅ Modèle enrichi sauvegardé (meilleur)")
    else:
        classifier_original.save_model("data/Affid/modele/enhanced_ticket_classifier_original.pkl")
        print("✅ Modèle original sauvegardé (meilleur)")

def test_predictions():
    """Teste le modèle avec quelques exemples"""
    
    print("\n🧪 TEST DE PRÉDICTIONS")
    print("=" * 30)
    
    # Charger le modèle
    classifier = EnhancedTicketClassifier()
    try:
        classifier.load_model()
    except FileNotFoundError:
        print("❌ Modèle non trouvé. Entraînement en cours...")
        classifier.train()
        classifier.save_model()
    
    # Exemples de test
    test_descriptions = [
        "Je n'arrive pas à me connecter à l'application",
        "Problème avec la facturation CCAM",
        "L'interface est très lente à charger",
        "Erreur lors de la sauvegarde des données",
        "Question sur les exonérations ALD"
    ]
    
    print("📝 Exemples de test:")
    for i, desc in enumerate(test_descriptions, 1):
        print(f"  {i}. {desc}")
    
    # Prédictions
    predictions = classifier.predict(test_descriptions)
    
    print("\n🎯 Résultats des prédictions:")
    for i, (desc, pred) in enumerate(zip(test_descriptions, predictions), 1):
        print(f"\n{i}. Description: {desc}")
        print(f"   Catégorie prédite: {pred['categorie_predite']}")
        print(f"   Confiance: {pred['confiance']:.2f}")
        
        # Top 3 catégories
        scores = pred['scores_par_categorie']
        top_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:3]
        print(f"   Top 3 catégories:")
        for cat, score in top_scores:
            print(f"     - {cat}: {score:.3f}")

if __name__ == "__main__":
    print("🚀 ENTRAÎNEMENT DU MODÈLE ENRICHİ (DESCRIPTIONS ORIGINALES)")
    print("=" * 60)
    
    # Entraînement avec descriptions originales
    print("\n🤖 Entraînement du modèle avec descriptions originales...")
    classifier = EnhancedTicketClassifier()
    classifier.use_enriched_descriptions = False  # Utiliser les descriptions originales
    accuracy, cv_score = classifier.train()
    
    # Sauvegarde du modèle
    classifier.save_model()
    
    # Test des prédictions
    print("\n🧪 TEST DE PRÉDICTIONS")
    print("=" * 30)
    test_predictions()
    
    print("\n✅ PROCESSUS TERMINÉ")
    print("\n📁 Fichiers créés:")
    print("  - data/Affid/modele/enhanced_ticket_classifier.pkl (modèle simplifié)")
    print("  - data/Affid/modele/modele_avec_definitions.xlsx (données enrichies)")
    print("\n🎯 Utilisation dans le dashboard:")
    print("  1. Le modèle enrichi sera automatiquement utilisé")
    print("  2. Seules les catégories principales sont prédites")
    print("  3. Les descriptions originales sont utilisées (plus fiables)") 