#!/usr/bin/env python3
"""
Script pour créer des modèles vraiment différents avec des algorithmes différents
"""

import pandas as pd
import pickle
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

def creer_modele_classique():
    """Crée un modèle classique avec Random Forest"""
    print("🔧 CRÉATION DU MODÈLE CLASSIQUE")
    print("=" * 50)
    
    # Charger les données originales
    df = pd.read_excel('data/Affid/modele/modele.xlsx')
    df = df.dropna(subset=['catégorie', 'description'])
    
    def preprocess_text(text):
        if pd.isna(text) or text == '':
            return ''
        text = str(text).lower()
        import re
        text = re.sub(r'[^\w\sàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    X_text = df['description'].apply(preprocess_text)
    y_categories = df['catégorie']
    
    # Paramètres simples
    vectorizer = TfidfVectorizer(max_features=500, ngram_range=(1, 1))
    X_tfidf = vectorizer.fit_transform(X_text)
    
    classifier = RandomForestClassifier(
        n_estimators=50, 
        max_depth=10, 
        random_state=42
    )
    
    X_train, X_test, y_train, y_test = train_test_split(X_tfidf, y_categories, test_size=0.2, random_state=42)
    classifier.fit(X_train, y_train)
    
    accuracy = accuracy_score(y_test, classifier.predict(X_test))
    
    print(f"✅ Modèle classique créé - Précision: {accuracy:.3f}")
    print(f"   Algorithme: Random Forest")
    print(f"   Paramètres: n_estimators=50, max_depth=10, max_features=500")
    print(f"   Descriptions originales: {len(df)} exemples")
    
    return vectorizer, classifier, accuracy

def creer_modele_enrichi():
    """Crée un modèle enrichi avec SVM"""
    print("\n🤖 CRÉATION DU MODÈLE ENRICHİ")
    print("=" * 50)
    
    # Charger les mêmes données mais avec un algorithme différent
    df = pd.read_excel('data/Affid/modele/modele.xlsx')
    df = df.dropna(subset=['catégorie', 'description'])
    
    def preprocess_text(text):
        if pd.isna(text) or text == '':
            return ''
        text = str(text).lower()
        import re
        text = re.sub(r'[^\w\sàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    X_text = df['description'].apply(preprocess_text)
    y_categories = df['catégorie']
    
    # Paramètres optimisés avec SVM
    vectorizer = TfidfVectorizer(max_features=2000, ngram_range=(1, 3))
    X_tfidf = vectorizer.fit_transform(X_text)
    
    classifier = SVC(
        kernel='rbf',
        C=1.0,
        gamma='scale',
        probability=True,
        random_state=42
    )
    
    X_train, X_test, y_train, y_test = train_test_split(X_tfidf, y_categories, test_size=0.2, random_state=42)
    classifier.fit(X_train, y_train)
    
    accuracy = accuracy_score(y_test, classifier.predict(X_test))
    
    print(f"✅ Modèle enrichi créé - Précision: {accuracy:.3f}")
    print(f"   Algorithme: Support Vector Machine (SVM)")
    print(f"   Paramètres: kernel=rbf, C=1.0, gamma=scale, max_features=2000")
    print(f"   Descriptions originales: {len(df)} exemples")
    
    return vectorizer, classifier, accuracy

def tester_predictions(vectorizer_classic, classifier_classic, vectorizer_enriched, classifier_enriched):
    """Teste les prédictions pour vérifier les différences"""
    print("\n🎯 TEST DES PRÉDICTIONS")
    print("=" * 50)
    
    test_examples = [
        "Mon lecteur de carte Vitale ne fonctionne plus",
        "Je n'arrive pas à créer une facture",
        "L'interface est très lente",
        "Problème de connexion à Stellair",
        "Question sur la facturation CCAM"
    ]
    
    def preprocess_text(text):
        if pd.isna(text) or text == '':
            return ''
        text = str(text).lower()
        import re
        text = re.sub(r'[^\w\sàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    differences_count = 0
    remplacant_count = 0
    
    for i, example in enumerate(test_examples, 1):
        # Prédiction classique
        example_clean = preprocess_text(example)
        example_tfidf_classic = vectorizer_classic.transform([example_clean])
        pred_classic = classifier_classic.predict(example_tfidf_classic)[0]
        conf_classic = max(classifier_classic.predict_proba(example_tfidf_classic)[0])
        
        # Prédiction enrichie
        example_tfidf_enriched = vectorizer_enriched.transform([example_clean])
        pred_enriched = classifier_enriched.predict(example_tfidf_enriched)[0]
        conf_enriched = max(classifier_enriched.predict_proba(example_tfidf_enriched)[0])
        
        if pred_enriched == 'Remplacant / Collaborateur':
            remplacant_count += 1
        
        # Comparaison
        same_prediction = pred_classic == pred_enriched
        if not same_prediction:
            differences_count += 1
        
        print(f"\n{i}. Description: {example}")
        print(f"   Classique: {pred_classic} (conf: {conf_classic:.3f})")
        print(f"   Enrichi:   {pred_enriched} (conf: {conf_enriched:.3f})")
        print(f"   Différence: {'❌' if not same_prediction else '✅'}")
    
    print(f"\n📊 RÉSUMÉ:")
    print(f"   Différences: {differences_count}/{len(test_examples)} prédictions")
    print(f"   Taux de différence: {(differences_count/len(test_examples)*100):.1f}%")
    print(f"   'Remplacant/Collaborateur': {remplacant_count}/{len(test_examples)}")
    
    return differences_count > 0 and remplacant_count < len(test_examples)

def sauvegarder_modeles(vectorizer_classic, classifier_classic, vectorizer_enriched, classifier_enriched):
    """Sauvegarde les modèles"""
    print("\n💾 SAUVEGARDE DES MODÈLES")
    print("=" * 50)
    
    # Modèle classique
    model_data_classic = {
        'vectorizer': vectorizer_classic,
        'classifier': classifier_classic,
        'type': 'classic'
    }
    
    with open('data/Affid/modele/ticket_classifier_classic.pkl', 'wb') as f:
        pickle.dump(model_data_classic, f)
    
    print("✅ Modèle classique sauvegardé: ticket_classifier_classic.pkl")
    
    # Modèle enrichi
    model_data_enriched = {
        'vectorizer': vectorizer_enriched,
        'classifier': classifier_enriched,
        'type': 'enriched'
    }
    
    with open('data/Affid/modele/enhanced_ticket_classifier.pkl', 'wb') as f:
        pickle.dump(model_data_enriched, f)
    
    print("✅ Modèle enrichi sauvegardé: enhanced_ticket_classifier.pkl")

def main():
    """Fonction principale"""
    print("🚀 CRÉATION DE MODÈLES AVEC ALGORITHMES DIFFÉRENTS")
    print("=" * 60)
    
    # 1. Créer le modèle classique
    vectorizer_classic, classifier_classic, acc_classic = creer_modele_classique()
    
    # 2. Créer le modèle enrichi
    vectorizer_enriched, classifier_enriched, acc_enriched = creer_modele_enrichi()
    
    # 3. Comparer les performances
    print(f"\n📊 COMPARAISON DES PERFORMANCES:")
    print(f"   Modèle classique (Random Forest): {acc_classic:.3f}")
    print(f"   Modèle enrichi (SVM): {acc_enriched:.3f}")
    print(f"   Différence: {acc_enriched - acc_classic:+.3f}")
    
    # 4. Tester les prédictions
    success = tester_predictions(vectorizer_classic, classifier_classic, vectorizer_enriched, classifier_enriched)
    
    if success:
        print("\n✅ Modèles créés avec succès !")
        
        # 5. Sauvegarder les modèles
        sauvegarder_modeles(vectorizer_classic, classifier_classic, vectorizer_enriched, classifier_enriched)
        
        print("\n🎉 SUCCÈS ! Les modèles sont maintenant vraiment différents.")
        print("📋 Prochaines étapes:")
        print("   1. Relancer l'application Streamlit")
        print("   2. Vérifier les différences dans l'interface")
        print("   3. Comparer les résultats des deux méthodes")
    else:
        print("\n❌ Problème détecté. Les modèles ont encore des biais.")
        print("💡 Suggestions:")
        print("   - Ajuster les paramètres")
        print("   - Utiliser des algorithmes différents")
        print("   - Nettoyer les données d'entraînement")

if __name__ == "__main__":
    main() 