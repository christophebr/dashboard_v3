import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
import re
import pickle
import os

class FacturationClassifier:
    """
    Classifieur spécialisé pour les sous-catégories de facturation médicale
    """
    
    def __init__(self, model_path="data/Affid/modele/facturation_classifier.pkl"):
        self.model_path = model_path
        self.pipeline = None
        self.sous_categories = None
        self.is_trained = False
        self.mots_cles_dict = {}
        
        # Mots-clés spécifiques par sous-catégorie (fallback)
        self.mots_cles_specifiques = {
            'Facturation-Cotation CCAM': [
                'ccam', 'qzm', 'qama', 'base tarif', 'tarif sécu', 'codes ccam',
                'qzm001', 'qama002', 'classification ccam'
            ],
            'Facturation-Exoneration (EXO, ALD, C2S)': [
                'exo', 'ald', 'c2s', 'exonération', 'exoneration', 'code 7',
                '100% ald', 'exemption', 'prise en charge'
            ],
            'Facturation-Cotation IVG': [
                'ivg', 'fmv', 'grossesse', '6 semaines', 'interruption',
                'volontaire', 'médicamenteuse', 'montant ivg'
            ],
            'Facturation-Teleconsultation': [
                'téléconsultation', 'teleconsultation', 'tcs', 'télé expertise',
                'rdv', 'consultation distance', '50 euros'
            ],
            'Facturation-Majoration': [
                'majoration', 'md', 'vsp', 'mn', 'mm', 'hors garde',
                '20h', 'minuit', '6h', '8h', 'créneau'
            ],
            'Facturation-PAV': [
                'pav', 'participation forfaitaire', 'patient hospitalisé',
                '120 euros', '24 euros', 'hospitalisation'
            ],
            'Facturation-ALD': [
                'ald', '100% amo', 'affection longue durée', 'forcer',
                'paramètre ald'
            ],
            'Facturation-Association d\'actes': [
                'association', 'actes série', 'kiné', 'orthophoniste',
                'orthoptiste', 'deux actes', 'codage multiple'
            ],
            'Facturation-Dépassement': [
                'dépassement', 'depassement', 'honoraires', 'conventionné',
                'optam', '32 euros', '23 euros', 'mutuelle'
            ],
            'Facturation-Cotation SF': [
                'sf', '16.5', '7.5', 'codes sf', 'cotation sf'
            ],
            'Facturation-Patient etranger': [
                'étranger', 'etranger', 'sécurité sociale', 'carte vitale',
                'demandeur asile', 'css', 'fsp', 'tiers payant'
            ],
            'Facturation-Taux de prise en charge': [
                'taux', 'prise en charge', 'remboursement', 'carte vitale',
                'fse', 'pourcentage'
            ],
            'Facturation-Cotation maternité': [
                'maternité', 'maternite', 'grossesse gémellaire', 'gemellaire',
                '70%', 'score'
            ],
            'Facturation-MT/DMT': [
                'mt', 'dmt', 'discipline medico tarifaire', 'mode traitement',
                'cpam', 'rejet', 'hospitalisé'
            ],
            'Facturation-SNCF': [
                'sncf', 'agréé', 'agreement'
            ],
            'Facturation-Dégradé': [
                'dégradé', 'degrade', 'feuille soins', 'numéro sécu',
                'sans cv', 'compta'
            ],
            'Facturation-Soins Anonyme': [
                'anonyme', 'anonymisé', 'anonymise', 'feuille soin'
            ]
        }
    
    def load_mots_cles(self, mots_cles_path="data/Affid/modele/Mots_cles.xlsx"):
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
                # Utiliser les mots-clés spécifiques comme fallback
                self.mots_cles_dict = self.mots_cles_specifiques
        except Exception as e:
            print(f"⚠️ Erreur lors du chargement des mots-clés: {e}")
            # Utiliser les mots-clés spécifiques comme fallback
            self.mots_cles_dict = self.mots_cles_specifiques
    
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
            
            # Features générales
            row_features['length'] = len(desc_lower)
            row_features['has_euros'] = 1 if 'euros' in desc_lower or '€' in desc else 0
            row_features['has_percent'] = 1 if '%' in desc else 0
            row_features['has_numbers'] = 1 if re.search(r'\d+', desc) else 0
            
            features.append(row_features)
        
        return pd.DataFrame(features)
    
    def preprocess_text(self, text):
        """
        Prétraitement spécialisé pour la facturation
        """
        if pd.isna(text) or text == '':
            return ''
        
        # Conversion en string et minuscules
        text = str(text).lower()
        
        # Normalisation des accents et caractères spéciaux
        text = re.sub(r'[^\w\sàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ]', ' ', text)
        
        # Suppression des espaces multiples
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def load_data(self, file_path):
        """
        Charge et prépare les données de facturation
        """
        print("📊 Chargement des données de facturation...")
        df = pd.read_excel(file_path)
        
        # Filtrer uniquement la catégorie Facturation
        df_facturation = df[df['catégorie'] == 'Facturation'].copy()
        
        if df_facturation.empty:
            raise ValueError("Aucune donnée de facturation trouvée")
        
        # Nettoyage
        df_facturation = df_facturation.dropna(subset=['description', 'sous-catégorie'])
        df_facturation['description_clean'] = df_facturation['description'].apply(self.preprocess_text)
        df_facturation = df_facturation[df_facturation['description_clean'] != '']
        
        print(f"✅ {len(df_facturation)} descriptions de facturation chargées")
        print(f"📈 Répartition des sous-catégories:")
        print(df_facturation['sous-catégorie'].value_counts())
        
        return df_facturation
    
    def train(self, file_path="data/Affid/modele/modele.xlsx"):
        """
        Entraîne le modèle spécialisé facturation avec mots-clés
        """
        # Chargement des mots-clés
        self.load_mots_cles()
        
        # Chargement des données
        df_facturation = self.load_data(file_path)
        
        # Préparation des données
        X_text = df_facturation['description_clean']
        y = df_facturation['sous-catégorie']
        
        # Sauvegarde des sous-catégories (après filtrage)
        self.sous_categories = sorted(y.unique())
        
        print(f"📊 Après filtrage: {len(self.sous_categories)} sous-catégories avec ≥2 exemples")
        print(f"📈 Répartition finale:")
        print(y.value_counts())
        
        print(f"🎯 {len(self.sous_categories)} sous-catégories de facturation")
        
        # Filtrer les sous-catégories avec au moins 2 exemples pour l'entraînement
        sous_categories_valides = y.value_counts()
        sous_categories_valides = sous_categories_valides[sous_categories_valides >= 2].index.tolist()
        
        df_facturation_filtre = df_facturation[df_facturation['sous-catégorie'].isin(sous_categories_valides)].copy()
        
        if len(df_facturation_filtre) < 10:
            raise ValueError("Pas assez de données pour l'entraînement (minimum 10 exemples)")
        
        X_text = df_facturation_filtre['description_clean']
        y = df_facturation_filtre['sous-catégorie']
        
        # Extraction des features de mots-clés
        X_keywords = self.extract_keyword_features(X_text)
        
        # Division train/test
        X_train_text, X_test_text, y_train, y_test = train_test_split(
            X_text, y, test_size=0.2, random_state=42, stratify=y
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
                max_features=2000,
                ngram_range=(1, 3),
                min_df=1,
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
                max_depth=15,
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
                    max_features=2000,
                    ngram_range=(1, 3),
                    min_df=1,
                    max_df=0.95,
                    stop_words=None
                )),
                ('classifier', RandomForestClassifier(
                    n_estimators=100,
                    max_depth=15,
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
        
        self.is_trained = True
        
        # Sauvegarde du modèle
        self.save_model()
        
        return accuracy
    
    def predict(self, descriptions):
        """
        Prédit les sous-catégories pour une ou plusieurs descriptions
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
                'sous_categorie_predite': pred,
                'confiance': max_prob,
                'probabilites': dict(zip(self.sous_categories, prob))
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
        self.sous_categories = model_data['sous_categories']
        self.is_trained = model_data['is_trained']
        self.mots_cles_dict = model_data.get('mots_cles_dict', {})
        
        print(f"📂 Modèle chargé: {self.model_path}")
        print(f"🎯 {len(self.sous_categories)} sous-catégories disponibles")
        if self.mots_cles_dict:
            print(f"🔑 {len(self.mots_cles_dict)} catégories de mots-clés chargées")

def train_facturation_classifier():
    """
    Fonction utilitaire pour entraîner le modèle
    """
    classifier = FacturationClassifier()
    accuracy = classifier.train()
    return classifier, accuracy

def load_facturation_classifier():
    """
    Fonction utilitaire pour charger le modèle
    """
    classifier = FacturationClassifier()
    classifier.load_model()
    return classifier

if __name__ == "__main__":
    # Test d'entraînement
    print("🚀 Test d'entraînement du modèle de classification de facturation")
    classifier, accuracy = train_facturation_classifier()
    
    # Test de prédiction
    test_descriptions = [
        "Problème avec la cotation CCAM QZM001",
        "Exonération ALD pour le patient",
        "Téléconsultation à 50 euros"
    ]
    
    print("\n🧪 Test de prédiction:")
    for desc in test_descriptions:
        result = classifier.predict(desc)
        print(f"📝 Description: {result['description']}")
        print(f"🎯 Sous-catégorie prédite: {result['sous_categorie_predite']}")
        print(f"📊 Confiance: {result['confiance']:.3f}")
        print("-" * 50) 