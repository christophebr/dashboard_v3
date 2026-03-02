#!/usr/bin/env python3
"""
Script de diagnostic pour analyser les causes du faible taux de catégorisation IA
"""

import pandas as pd
import numpy as np
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def diagnostic_categorisation():
    """
    Diagnostic complet de la catégorisation IA
    """
    print("🔍 DIAGNOSTIC DE LA CATÉGORISATION IA")
    print("=" * 50)
    
    # 1. Vérifier le fichier de catégories
    print("\n1. ANALYSE DU FICHIER DE CATÉGORIES")
    print("-" * 30)
    
    categories_path = 'data/Affid/modele/Categories_Mots_Cles_Personnalisees.xlsx'
    if not os.path.exists(categories_path):
        print(f"❌ Fichier non trouvé: {categories_path}")
        return
    
    try:
        df_categories = pd.read_excel(categories_path)
        print(f"✅ Fichier trouvé: {len(df_categories)} lignes")
        print(f"📊 Colonnes: {list(df_categories.columns)}")
        
        # Analyser les catégories
        if 'Categorie' in df_categories.columns and 'Mots_cles' in df_categories.columns:
            categories_dict = {}
            for _, row in df_categories.iterrows():
                categorie = row['Categorie']
                mot_cle = str(row['Mots_cles']).lower().strip()
                if categorie not in categories_dict:
                    categories_dict[categorie] = []
                categories_dict[categorie].append(mot_cle)
            
            print(f"\n📋 Catégories disponibles ({len(categories_dict)}):")
            for categorie, mots_cles in categories_dict.items():
                print(f"  • {categorie}: {len(mots_cles)} mots-clés")
                if len(mots_cles) <= 5:  # Afficher les mots-clés si peu nombreux
                    print(f"    Mots-clés: {', '.join(mots_cles[:5])}")
            
            # Analyser la qualité des mots-clés
            total_mots_cles = sum(len(mots) for mots in categories_dict.values())
            print(f"\n📈 Statistiques des mots-clés:")
            print(f"  • Total mots-clés: {total_mots_cles}")
            print(f"  • Moyenne par catégorie: {total_mots_cles/len(categories_dict):.1f}")
            
            # Identifier les catégories avec peu de mots-clés
            categories_faibles = {cat: mots for cat, mots in categories_dict.items() if len(mots) < 3}
            if categories_faibles:
                print(f"\n⚠️ Catégories avec peu de mots-clés (< 3):")
                for cat, mots in categories_faibles.items():
                    print(f"  • {cat}: {len(mots)} mots-clés")
        
        else:
            print("❌ Colonnes 'Categorie' ou 'Mots_cles' manquantes")
            print(f"Colonnes disponibles: {list(df_categories.columns)}")
            
    except Exception as e:
        print(f"❌ Erreur lors de la lecture du fichier: {str(e)}")
        return
    
    # 2. Analyser un échantillon de tickets
    print("\n\n2. ANALYSE D'UN ÉCHANTILLON DE TICKETS")
    print("-" * 35)
    
    # Simuler un échantillon de tickets SSI/Chat
    tickets_exemple = [
        "Problème de connexion à l'application",
        "Demande de réinitialisation de mot de passe",
        "Erreur lors de la saisie des données",
        "Question sur l'utilisation du logiciel",
        "Bug dans l'interface utilisateur",
        "Demande d'assistance technique",
        "Problème de synchronisation",
        "Erreur 404 page non trouvée",
        "Demande de formation",
        "Question sur les fonctionnalités"
    ]
    
    print(f"📝 Échantillon de tickets SSI/Chat ({len(tickets_exemple)}):")
    for i, ticket in enumerate(tickets_exemple, 1):
        print(f"  {i}. {ticket}")
    
    # 3. Test de similarité avec TF-IDF
    print("\n\n3. TEST DE SIMILARITÉ TF-IDF")
    print("-" * 30)
    
    try:
        # Préparer les textes des catégories
        categories_texts = []
        categories_names = []
        
        for categorie, mots_cles in categories_dict.items():
            texte_categorie = ' '.join(mots_cles)
            categories_texts.append(texte_categorie)
            categories_names.append(categorie)
        
        # Ajouter les descriptions des tickets
        all_texts = categories_texts + tickets_exemple
        
        # Vectorisation TF-IDF
        vectorizer = TfidfVectorizer(
            max_features=1000,
            ngram_range=(1, 2),
            stop_words='english',
            min_df=1
        )
        
        tfidf_matrix = vectorizer.fit_transform(all_texts)
        
        # Séparer les vecteurs des catégories et des tickets
        categories_vectors = tfidf_matrix[:len(categories_texts)]
        tickets_vectors = tfidf_matrix[len(categories_texts):]
        
        # Calculer les similarités
        similarities = cosine_similarity(tickets_vectors, categories_vectors)
        
        print(f"📊 Scores de similarité (seuil recommandé: 0.3):")
        for i, sim_scores in enumerate(similarities):
            best_idx = np.argmax(sim_scores)
            best_score = sim_scores[best_idx]
            best_category = categories_names[best_idx]
            
            print(f"\n  Ticket {i+1}: '{tickets_exemple[i]}'")
            print(f"    Meilleure catégorie: {best_category} (score: {best_score:.3f})")
            
            # Afficher les top 3
            top_indices = np.argsort(sim_scores)[::-1][:3]
            for j, idx in enumerate(top_indices):
                print(f"    {j+1}. {categories_names[idx]}: {sim_scores[idx]:.3f}")
        
        # Analyser les scores moyens
        scores_max = np.max(similarities, axis=1)
        print(f"\n📈 Statistiques des scores:")
        print(f"  • Score moyen max: {np.mean(scores_max):.3f}")
        print(f"  • Score médian max: {np.median(scores_max):.3f}")
        print(f"  • Score min max: {np.min(scores_max):.3f}")
        print(f"  • Score max max: {np.max(scores_max):.3f}")
        
        # Compter les tickets au-dessus du seuil
        seuil_test = 0.3
        tickets_au_dessus = np.sum(scores_max >= seuil_test)
        print(f"  • Tickets au-dessus du seuil {seuil_test}: {tickets_au_dessus}/{len(tickets_exemple)} ({tickets_au_dessus/len(tickets_exemple)*100:.1f}%)")
        
    except Exception as e:
        print(f"❌ Erreur lors du test TF-IDF: {str(e)}")
    
    # 4. Recommandations
    print("\n\n4. RECOMMANDATIONS POUR AMÉLIORER LE TAUX")
    print("-" * 45)
    
    print("🔧 Actions recommandées:")
    print("  1. Réduire le seuil de confiance (actuellement 0.3)")
    print("     • Essayer 0.2 ou 0.1 pour plus de sensibilité")
    print("     • Attention: risque de catégorisations incorrectes")
    
    print("\n  2. Améliorer les mots-clés:")
    print("     • Ajouter plus de mots-clés par catégorie")
    print("     • Inclure des variations (singulier/pluriel, synonymes)")
    print("     • Ajouter des expressions courantes")
    
    print("\n  3. Vérifier la qualité des descriptions:")
    print("     • S'assurer que les tickets ont des descriptions détaillées")
    print("     • Vérifier la colonne de description utilisée")
    
    print("\n  4. Tester avec Sentence Transformers:")
    print("     • Plus précis que TF-IDF pour la sémantique")
    print("     • Peut mieux comprendre le contexte")
    
    print("\n  5. Analyser les tickets non catégorisés:")
    print("     • Examiner les descriptions des tickets 'Non catégorisé'")
    print("     • Identifier les patterns manquants")
    
    # 5. Test avec différents seuils
    print("\n\n5. TEST AVEC DIFFÉRENTS SEUILS")
    print("-" * 35)
    
    seuils_test = [0.1, 0.2, 0.3, 0.4, 0.5]
    for seuil in seuils_test:
        tickets_au_dessus = np.sum(scores_max >= seuil)
        taux = tickets_au_dessus/len(tickets_exemple)*100
        print(f"  Seuil {seuil}: {tickets_au_dessus}/{len(tickets_exemple)} tickets ({taux:.1f}%)")

if __name__ == "__main__":
    diagnostic_categorisation() 