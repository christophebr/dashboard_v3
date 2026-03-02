#!/usr/bin/env python3
"""
Script pour analyser le biais du modèle enrichi vers "Remplacant / Collaborateur"
"""

import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

def analyse_biais():
    """Analyse le biais du modèle enrichi"""
    print("🔍 ANALYSE DU BIAIS DU MODÈLE ENRICHİ")
    print("=" * 50)
    
    # Charger les données
    df = pd.read_excel('data/Affid/modele/modele_avec_definitions.xlsx')
    print(f"📊 Données chargées: {len(df)} exemples")
    
    # Analyser la distribution des catégories
    print("\n📈 DISTRIBUTION DES CATÉGORIES:")
    print("-" * 30)
    categories_dist = df['catégorie'].value_counts()
    print(categories_dist)
    
    # Vérifier "Remplacant / Collaborateur"
    if 'Remplacant / Collaborateur' in categories_dist.index:
        remplacant_count = categories_dist['Remplacant / Collaborateur']
        remplacant_percentage = (remplacant_count / len(df)) * 100
        print(f"\n⚠️ 'Remplacant / Collaborateur': {remplacant_count} exemples ({remplacant_percentage:.1f}%)")
    
    # Analyser les descriptions enrichies
    print("\n🔍 ANALYSE DES DESCRIPTIONS ENRICHIES:")
    print("-" * 30)
    
    # Exemples de descriptions enrichies pour "Remplacant / Collaborateur"
    remplacant_examples = df[df['catégorie'] == 'Remplacant / Collaborateur']
    if len(remplacant_examples) > 0:
        print(f"📋 Exemples de descriptions enrichies pour 'Remplacant / Collaborateur':")
        for i in range(min(3, len(remplacant_examples))):
            print(f"\n{i+1}. Originale: {remplacant_examples.iloc[i]['description'][:100]}...")
            print(f"   Enrichie: {remplacant_examples.iloc[i]['description_enrichie'][:150]}...")
    
    # Analyser les définitions
    print("\n📚 ANALYSE DES DÉFINITIONS:")
    print("-" * 30)
    
    # Vérifier la définition de "Remplacant / Collaborateur"
    if 'Remplacant / Collaborateur' in df['catégorie'].values:
        definition = df[df['catégorie'] == 'Remplacant / Collaborateur']['definition_categorie'].iloc[0]
        print(f"📖 Définition 'Remplacant / Collaborateur':")
        if pd.isna(definition):
            print(f"   ❌ DÉFINITION MANQUANTE (nan)")
        else:
            print(f"   {definition}")
            print(f"   Longueur: {len(definition)} caractères")
    
    # Comparer avec d'autres définitions
    other_categories = ['Lecteur', 'Facturation', 'Fonctionnalités']
    for cat in other_categories:
        if cat in df['catégorie'].values:
            definition = df[df['catégorie'] == cat]['definition_categorie'].iloc[0]
            print(f"\n📖 Définition '{cat}':")
            if pd.isna(definition):
                print(f"   ❌ DÉFINITION MANQUANTE (nan)")
            else:
                print(f"   {definition[:100]}...")
                print(f"   Longueur: {len(definition)} caractères")

def test_solutions():
    """Teste différentes solutions pour corriger le biais"""
    print("\n🛠️ TEST DES SOLUTIONS")
    print("=" * 50)
    
    # Charger les données
    df = pd.read_excel('data/Affid/modele/modele_avec_definitions.xlsx')
    df = df.dropna(subset=['catégorie', 'description'])
    
    # Prétraitement
    def preprocess_text(text):
        if pd.isna(text) or text == '':
            return ''
        text = str(text).lower()
        import re
        text = re.sub(r'[^\w\sàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    # Solution 1: Modèle avec descriptions originales uniquement
    print("\n🔧 SOLUTION 1: Descriptions originales uniquement")
    print("-" * 40)
    
    X_original = df['description'].apply(preprocess_text)
    y = df['catégorie']
    
    vectorizer_original = TfidfVectorizer(max_features=1000, ngram_range=(1, 2))
    X_original_tfidf = vectorizer_original.fit_transform(X_original)
    
    classifier_original = RandomForestClassifier(n_estimators=50, random_state=42)
    X_train, X_test, y_train, y_test = train_test_split(X_original_tfidf, y, test_size=0.2, random_state=42)
    classifier_original.fit(X_train, y_train)
    
    y_pred_original = classifier_original.predict(X_test)
    accuracy_original = accuracy_score(y_test, y_pred_original)
    print(f"✅ Précision: {accuracy_original:.3f}")
    
    # Solution 2: Modèle avec descriptions enrichies mais paramètres différents
    print("\n🔧 SOLUTION 2: Descriptions enrichies avec paramètres différents")
    print("-" * 40)
    
    X_enriched = df['description_enrichie'].apply(preprocess_text)
    
    vectorizer_enriched = TfidfVectorizer(max_features=2000, ngram_range=(1, 3))
    X_enriched_tfidf = vectorizer_enriched.fit_transform(X_enriched)
    
    classifier_enriched = RandomForestClassifier(
        n_estimators=100, 
        max_depth=15, 
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42
    )
    X_train_e, X_test_e, y_train_e, y_test_e = train_test_split(X_enriched_tfidf, y, test_size=0.2, random_state=42)
    classifier_enriched.fit(X_train_e, y_train_e)
    
    y_pred_enriched = classifier_enriched.predict(X_test_e)
    accuracy_enriched = accuracy_score(y_test_e, y_pred_enriched)
    print(f"✅ Précision: {accuracy_enriched:.3f}")
    
    # Solution 3: Modèle hybride (descriptions + définitions séparées)
    print("\n🔧 SOLUTION 3: Modèle hybride")
    print("-" * 40)
    
    # Créer des features hybrides
    df['text_hybrid'] = df['description'] + " " + df['definition_categorie'].fillna('').str[:200]
    X_hybrid = df['text_hybrid'].apply(preprocess_text)
    
    vectorizer_hybrid = TfidfVectorizer(max_features=1500, ngram_range=(1, 2))
    X_hybrid_tfidf = vectorizer_hybrid.fit_transform(X_hybrid)
    
    classifier_hybrid = RandomForestClassifier(n_estimators=75, max_depth=12, random_state=42)
    X_train_h, X_test_h, y_train_h, y_test_h = train_test_split(X_hybrid_tfidf, y, test_size=0.2, random_state=42)
    classifier_hybrid.fit(X_train_h, y_train_h)
    
    y_pred_hybrid = classifier_hybrid.predict(X_test_h)
    accuracy_hybrid = accuracy_score(y_test_h, y_pred_hybrid)
    print(f"✅ Précision: {accuracy_hybrid:.3f}")
    
    # Comparer les prédictions
    print("\n🎯 COMPARAISON DES PRÉDICTIONS:")
    print("-" * 30)
    
    test_examples = [
        "Mon lecteur de carte Vitale ne fonctionne plus",
        "Je n'arrive pas à créer une facture",
        "L'interface est très lente"
    ]
    
    for i, example in enumerate(test_examples, 1):
        print(f"\n{i}. Description: {example}")
        
        # Prédiction originale
        example_clean = preprocess_text(example)
        example_tfidf_original = vectorizer_original.transform([example_clean])
        pred_original = classifier_original.predict(example_tfidf_original)[0]
        conf_original = max(classifier_original.predict_proba(example_tfidf_original)[0])
        print(f"   Originale: {pred_original} (conf: {conf_original:.3f})")
        
        # Prédiction enrichie
        example_tfidf_enriched = vectorizer_enriched.transform([example_clean])
        pred_enriched = classifier_enriched.predict(example_tfidf_enriched)[0]
        conf_enriched = max(classifier_enriched.predict_proba(example_tfidf_enriched)[0])
        print(f"   Enrichie: {pred_enriched} (conf: {conf_enriched:.3f})")
        
        # Prédiction hybride
        example_tfidf_hybrid = vectorizer_hybrid.transform([example_clean])
        pred_hybrid = classifier_hybrid.predict(example_tfidf_hybrid)[0]
        conf_hybrid = max(classifier_hybrid.predict_proba(example_tfidf_hybrid)[0])
        print(f"   Hybride: {pred_hybrid} (conf: {conf_hybrid:.3f})")
    
    # Recommandation
    print(f"\n📊 RÉSUMÉ DES PERFORMANCES:")
    print(f"   Originale: {accuracy_original:.3f}")
    print(f"   Enrichie: {accuracy_enriched:.3f}")
    print(f"   Hybride: {accuracy_hybrid:.3f}")
    
    best_method = max([(accuracy_original, "Originale"), (accuracy_enriched, "Enrichie"), (accuracy_hybrid, "Hybride")])
    print(f"\n🏆 Meilleure méthode: {best_method[1]} ({best_method[0]:.3f})")

def proposer_corrections():
    """Propose des corrections pour le biais"""
    print("\n💡 PROPOSITIONS DE CORRECTIONS")
    print("=" * 50)
    
    print("1️⃣ **Solution immédiate - Revenir aux descriptions originales:**")
    print("   - Modifier train_model_with_definitions.py")
    print("   - Changer use_enriched_descriptions = False")
    print("   - Garder les définitions pour l'interface utilisateur")
    print("   - Avantage: Pas de biais, prédictions diversifiées")
    
    print("\n2️⃣ **Solution hybride - Combiner descriptions et définitions:**")
    print("   - Utiliser: description + début de définition")
    print("   - Limiter la longueur des définitions")
    print("   - Ajuster les paramètres du modèle")
    print("   - Avantage: Contexte sans biais excessif")
    
    print("\n3️⃣ **Solution paramétrique - Ajuster le modèle:**")
    print("   - Augmenter min_samples_split et min_samples_leaf")
    print("   - Réduire max_depth")
    print("   - Utiliser class_weight='balanced'")
    print("   - Avantage: Réduction du surapprentissage")
    
    print("\n4️⃣ **Solution définitions - Réviser les définitions YAML:**")
    print("   - Raccourcir les définitions trop longues")
    print("   - Équilibrer la longueur entre catégories")
    print("   - Rendre les définitions plus spécifiques")
    print("   - Avantage: Contexte plus équilibré")

if __name__ == "__main__":
    analyse_biais()
    test_solutions()
    proposer_corrections()
    
    print("\n🎯 RECOMMANDATION FINALE:")
    print("=" * 30)
    print("Le modèle enrichi a un biais vers 'Remplacant / Collaborateur'")
    print("Solutions recommandées:")
    print("1. Revenir aux descriptions originales (solution immédiate)")
    print("2. Implémenter le modèle hybride (solution optimale)")
    print("3. Réviser les définitions YAML (solution long terme)") 