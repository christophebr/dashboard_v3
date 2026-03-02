import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler
import pickle
import re
import os

class TicketClassifier:
    """
    Modèle de classification automatique des tickets de support
    Utilise TF-IDF + Random Forest + Mots-clés pour catégoriser les descriptions
    """
    
    def __init__(self, model_path="data/Affid/modele/ticket_classifier.pkl"):
        self.model_path = model_path
        self.pipeline = None
        self.categories = None
        self.sous_categories = None
        self.is_trained = False
        self.mots_cles_dict = {}
        
    def load_mots_cles(self, mots_cles_path="data/Affid/modele/Mots_cles_ssi.xlsx"):
        """
        Charge les mots-clés depuis le fichier Excel
        """
        try:
            if os.path.exists(mots_cles_path):
                mots_cles_df = pd.read_excel(mots_cles_path)
                mots_cles_df['Mots'] = mots_cles_df['Mots'].astype(str).str.strip().str.lower()
                
                # Créer le dictionnaire des mots-clés
                for cat in mots_cles_df['Categorie'].unique():
                    self.mots_cles_dict[cat] = set(mots_cles_df[mots_cles_df['Categorie'] == cat]['Mots'].tolist())
                
                print(f"✅ {len(self.mots_cles_dict)} catégories de mots-clés chargées")
                for cat, mots in self.mots_cles_dict.items():
                    print(f"  {cat}: {len(mots)} mots-clés")
            else:
                print(f"⚠️ Fichier de mots-clés non trouvé: {mots_cles_path}")
        except Exception as e:
            print(f"⚠️ Erreur lors du chargement des mots-clés: {e}")
    
    def extract_keyword_features(self, descriptions):
        """
        Extrait les features basées sur la présence des mots-clés
        """
        if not self.mots_cles_dict:
            return pd.DataFrame()
        
        features = []
        for desc in descriptions:
            desc_lower = str(desc).lower()
            row_features = {}
            
            for categorie, mots_set in self.mots_cles_dict.items():
                # Compter le nombre de mots-clés présents pour cette catégorie
                count = sum(1 for mot in mots_set if mot and mot in desc_lower)
                row_features[f'kw_{categorie}'] = count
            
            features.append(row_features)
        
        return pd.DataFrame(features)
    
    def preprocess_text(self, text):
        """
        Prétraitement du texte : nettoyage et normalisation
        """
        if pd.isna(text) or text == '':
            return ''
        
        # Conversion en string
        text = str(text).lower()
        
        # Suppression des caractères spéciaux mais garder les accents
        text = re.sub(r'[^\w\sàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ]', ' ', text)
        
        # Suppression des espaces multiples
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def load_data(self, file_path):
        """
        Charge et prépare les données d'entraînement
        """
        print("📊 Chargement des données...")
        df = pd.read_excel(file_path)
        
        # Vérification des colonnes
        required_columns = ['sous-catégorie', 'catégorie', 'description']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Colonnes manquantes: {missing_columns}")
        
        # Nettoyage des données
        df = df.dropna(subset=['description', 'catégorie'])
        df['description_clean'] = df['description'].apply(self.preprocess_text)
        
        # Filtrage des descriptions vides
        df = df[df['description_clean'] != '']
        
        print(f"✅ {len(df)} descriptions valides chargées")
        print(f"📈 Répartition des catégories:")
        print(df['catégorie'].value_counts())
        
        return df
    
    def train(self, file_path="data/Affid/modele/modele.xlsx"):
        """
        Entraîne le modèle de classification avec mots-clés
        """
        # Chargement des mots-clés
        self.load_mots_cles()
        
        # Chargement des données
        df = self.load_data(file_path)
        
        # Préparation des données
        X_text = df['description_clean']
        y_categories = df['catégorie']
        y_sous_categories = df['sous-catégorie']
        
        # Sauvegarde des catégories uniques
        self.categories = sorted(y_categories.unique())
        self.sous_categories = sorted(y_sous_categories.unique())
        
        print(f"🎯 {len(self.categories)} catégories principales")
        print(f"📋 {len(self.sous_categories)} sous-catégories")
        
        # Extraction des features de mots-clés
        X_keywords = self.extract_keyword_features(X_text)
        
        # Division train/test
        X_train_text, X_test_text, y_train, y_test = train_test_split(
            X_text, y_categories, test_size=0.2, random_state=42, stratify=y_categories
        )
        
        # Extraction des features de mots-clés pour train/test
        X_train_keywords = self.extract_keyword_features(X_train_text)
        X_test_keywords = self.extract_keyword_features(X_test_text)
        
        # Création du pipeline avec features multiples
        if not X_keywords.empty:
            # Pipeline avec TF-IDF + mots-clés
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.ensemble import RandomForestClassifier
            from sklearn.pipeline import Pipeline
            from sklearn.preprocessing import StandardScaler
            import numpy as np
            
            # Créer le vectorizer TF-IDF
            tfidf_vectorizer = TfidfVectorizer(
                max_features=5000,
                ngram_range=(1, 2),
                min_df=2,
                max_df=0.95,
                stop_words=None
            )
            
            # Transformer les textes
            X_train_tfidf = tfidf_vectorizer.fit_transform(X_train_text)
            X_test_tfidf = tfidf_vectorizer.transform(X_test_text)
            
            # Standardiser les features de mots-clés
            scaler = StandardScaler()
            X_train_keywords_scaled = scaler.fit_transform(X_train_keywords)
            X_test_keywords_scaled = scaler.transform(X_test_keywords)
            
            # Combiner les features
            X_train_combined = np.hstack([X_train_tfidf.toarray(), X_train_keywords_scaled])
            X_test_combined = np.hstack([X_test_tfidf.toarray(), X_test_keywords_scaled])
            
            # Créer le classifieur
            classifier = RandomForestClassifier(
                n_estimators=100,
                max_depth=20,
                random_state=42,
                n_jobs=-1
            )
            
            # Entraînement
            print("🤖 Entraînement du modèle avec mots-clés...")
            classifier.fit(X_train_combined, y_train)
            
            # Évaluation
            y_pred = classifier.predict(X_test_combined)
            accuracy = accuracy_score(y_test, y_pred)
            
            # Sauvegarder les composants
            self.pipeline = {
                'tfidf_vectorizer': tfidf_vectorizer,
                'scaler': scaler,
                'classifier': classifier,
                'has_keywords': True
            }
            
        else:
            # Pipeline classique sans mots-clés
            self.pipeline = Pipeline([
                ('tfidf', TfidfVectorizer(
                    max_features=5000,
                    ngram_range=(1, 2),
                    min_df=2,
                    max_df=0.95,
                    stop_words=None
                )),
                ('classifier', RandomForestClassifier(
                    n_estimators=100,
                    max_depth=20,
                    random_state=42,
                    n_jobs=-1
                ))
            ])
            
            # Entraînement
            print("🤖 Entraînement du modèle classique...")
            self.pipeline.fit(X_train_text, y_train)
            
            # Évaluation
            y_pred = self.pipeline.predict(X_test_text)
            accuracy = accuracy_score(y_test, y_pred)
        
        print(f"✅ Modèle entraîné avec succès!")
        print(f"📊 Précision globale: {accuracy:.3f}")
        print("\n📈 Rapport de classification:")
        print(classification_report(y_test, y_pred))
        
        # Validation croisée (désactivée pour les modèles avec mots-clés)
        if not isinstance(self.pipeline, dict):
            cv_scores = cross_val_score(self.pipeline, X_text, y_categories, cv=5)
            print(f"🔄 Validation croisée (5-fold): {cv_scores.mean():.3f} (+/- {cv_scores.std() * 2:.3f})")
        else:
            print("🔄 Validation croisée désactivée pour le modèle avec mots-clés")
        
        self.is_trained = True
        
        # Sauvegarde du modèle
        self.save_model()
        
        return accuracy
    
    def predict(self, descriptions):
        """
        Prédit les catégories pour une ou plusieurs descriptions
        """
        if not self.is_trained:
            raise ValueError("Le modèle n'est pas entraîné. Utilisez train() d'abord.")
        
        # Prétraitement
        if isinstance(descriptions, str):
            descriptions = [descriptions]
        
        descriptions_clean = [self.preprocess_text(desc) for desc in descriptions]
        
        # Extraction des features de mots-clés
        X_keywords = self.extract_keyword_features(descriptions_clean)
        
        # Prédiction selon le type de pipeline
        if isinstance(self.pipeline, dict) and self.pipeline.get('has_keywords', False):
            # Pipeline avec mots-clés
            X_tfidf = self.pipeline['tfidf_vectorizer'].transform(descriptions_clean)
            X_keywords_scaled = self.pipeline['scaler'].transform(X_keywords)
            X_combined = np.hstack([X_tfidf.toarray(), X_keywords_scaled])
            predictions = self.pipeline['classifier'].predict(X_combined)
            probabilities = self.pipeline['classifier'].predict_proba(X_combined)
        else:
            # Pipeline classique
            predictions = self.pipeline.predict(descriptions_clean)
            probabilities = self.pipeline.predict_proba(descriptions_clean)
        
        # Formatage des résultats
        results = []
        for i, (pred, prob) in enumerate(zip(predictions, probabilities)):
            max_prob = max(prob)
            results.append({
                'description': descriptions[i],
                'categorie_predite': pred,
                'confiance': max_prob,
                'probabilites': dict(zip(self.categories, prob))
            })
        
        return results if len(results) > 1 else results[0]
    
    def save_model(self):
        """
        Sauvegarde le modèle entraîné
        """
        if not self.is_trained:
            raise ValueError("Le modèle n'est pas entraîné")
        
        # Créer le dossier si nécessaire
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        
        # Sauvegarde
        with open(self.model_path, 'wb') as f:
            pickle.dump({
                'pipeline': self.pipeline,
                'categories': self.categories,
                'sous_categories': self.sous_categories,
                'is_trained': self.is_trained,
                'mots_cles_dict': self.mots_cles_dict
            }, f)
        
        print(f"💾 Modèle sauvegardé: {self.model_path}")
    
    def load_model(self):
        """
        Charge un modèle pré-entraîné
        """
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Modèle non trouvé: {self.model_path}")
        
        with open(self.model_path, 'rb') as f:
            model_data = pickle.load(f)
        
        self.pipeline = model_data['pipeline']
        self.categories = model_data['categories']
        self.sous_categories = model_data['sous_categories']
        self.is_trained = model_data['is_trained']
        self.mots_cles_dict = model_data.get('mots_cles_dict', {})
        
        print(f"📂 Modèle chargé: {self.model_path}")
        print(f"🎯 {len(self.categories)} catégories disponibles")
        if self.mots_cles_dict:
            print(f"🔑 {len(self.mots_cles_dict)} catégories de mots-clés chargées")
    
    def get_feature_importance(self, top_n=20):
        """
        Retourne les mots les plus importants pour chaque catégorie
        """
        if not self.is_trained:
            raise ValueError("Le modèle n'est pas entraîné")
        
        # Pipeline avec mots-clés
        if isinstance(self.pipeline, dict) and self.pipeline.get('has_keywords', False):
            vectorizer = self.pipeline['tfidf_vectorizer']
            classifier = self.pipeline['classifier']
            # Récupérer les noms des features TF-IDF
            feature_names = list(vectorizer.get_feature_names_out())
            # Ajouter les noms des colonnes mots-clés
            if self.mots_cles_dict:
                feature_names += [f"kw_{cat}" for cat in self.mots_cles_dict.keys()]
            # Vérifier la taille
            importances = classifier.feature_importances_
            if len(importances) != len(feature_names):
                # Si on a aussi des features générales (longueur, has_euros, etc.), ajouter leurs noms
                nb_extra = len(importances) - len(feature_names)
                feature_names += [f"extra_{i}" for i in range(nb_extra)]
            importance_df = pd.DataFrame({
                'feature': feature_names,
                'importance': importances
            }).sort_values('importance', ascending=False)
            return importance_df.head(top_n)
        else:
            # Pipeline classique
            vectorizer = self.pipeline.named_steps['tfidf']
            classifier = self.pipeline.named_steps['classifier']
            feature_names = vectorizer.get_feature_names_out()
            importances = classifier.feature_importances_
            importance_df = pd.DataFrame({
                'feature': feature_names,
                'importance': importances
            }).sort_values('importance', ascending=False)
            return importance_df.head(top_n)
    
    def evaluate_sample(self, description):
        """
        Évalue une description avec détails
        """
        result = self.predict(description)
        
        print(f"📝 Description: {result['description']}")
        print(f"🎯 Catégorie prédite: {result['categorie_predite']}")
        print(f"📊 Confiance: {result['confiance']:.3f}")
        print("\n📈 Probabilités par catégorie:")
        
        for categorie, prob in sorted(result['probabilites'].items(), key=lambda x: x[1], reverse=True):
            print(f"  {categorie}: {prob:.3f}")

def train_ticket_classifier():
    """
    Fonction utilitaire pour entraîner le modèle
    """
    classifier = TicketClassifier()
    accuracy = classifier.train()
    return classifier, accuracy

def load_ticket_classifier():
    """
    Fonction utilitaire pour charger le modèle
    """
    classifier = TicketClassifier()
    classifier.load_model()
    return classifier

if __name__ == "__main__":
    # Test d'entraînement
    print("🚀 Test d'entraînement du modèle de classification des tickets")
    classifier, accuracy = train_ticket_classifier()
    
    # Test de prédiction
    test_descriptions = [
        "Je n'arrive pas à me connecter avec ma carte CPS",
        "L'application est très lente lors de la saisie des actes",
        "Erreur lors de la télétransmission des feuilles de soins"
    ]
    
    print("\n🧪 Test de prédiction:")
    for desc in test_descriptions:
        classifier.evaluate_sample(desc)
        print("-" * 50) 