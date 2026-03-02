import pandas as pd
from collections import Counter
import re
from sklearn.feature_extraction.text import CountVectorizer, ENGLISH_STOP_WORDS

# Liste de stopwords français (extrait de sklearn + compléments)
FRENCH_STOPWORDS = set([
    'a', 'au', 'aux', 'avec', 'ce', 'ces', 'dans', 'de', 'des', 'du', 'elle', 'en', 'et', 'eux', 'il', 'je', 'la',
    'le', 'leur', 'lui', 'ma', 'mais', 'me', 'même', 'mes', 'moi', 'mon', 'ne', 'nos', 'notre', 'nous', 'on', 'ou',
    'par', 'pas', 'pour', 'qu', 'que', 'qui', 'sa', 'se', 'ses', 'son', 'sur', 'ta', 'te', 'tes', 'toi', 'ton',
    'tu', 'un', 'une', 'vos', 'votre', 'vous', 'c', 'd', 'j', 'l', 'à', 'm', 'n', 's', 't', 'y', 'été', 'étée',
    'étées', 'étés', 'étant', 'suis', 'es', 'est', 'sommes', 'êtes', 'sont', 'serai', 'seras', 'sera', 'serons',
    'serez', 'seront', 'serais', 'serait', 'serions', 'seriez', 'seraient', 'étais', 'était', 'étions', 'étiez',
    'étaient', 'fus', 'fut', 'fûmes', 'fûtes', 'furent', 'sois', 'soit', 'soyons', 'soyez', 'soient', 'fusse',
    'fusses', 'fût', 'fussions', 'fussiez', 'fussent', 'ayant', 'eu', 'eue', 'eues', 'eus', 'ai', 'as', 'avons',
    'avez', 'ont', 'aurai', 'auras', 'aura', 'aurons', 'aurez', 'auront', 'aurais', 'aurait', 'aurions', 'auriez',
    'auraient', 'avais', 'avait', 'avions', 'aviez', 'avaient', 'eut', 'eûmes', 'eûtes', 'eurent', 'aie', 'aies',
    'ait', 'ayons', 'ayez', 'aient', 'eusse', 'eusses', 'eût', 'eussions', 'eussiez', 'eussent', 'ceci', 'cela',
    'celà', 'cet', 'cette', 'ici', 'ils', 'les', 'leurs', 'quel', 'quels', 'quelle', 'quelles', 'sans', 'soi'
])
ALL_STOPWORDS = set(ENGLISH_STOP_WORDS) | FRENCH_STOPWORDS

def clean_text(text):
    text = str(text).lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return text

# Charger le fichier Excel
df = pd.read_excel("data/Affid/modele/modele.xlsx")

rows = []

for cat in df['catégorie'].dropna().unique():
    # descriptions est une Series pandas, donc dropna() est valide
    descriptions = pd.Series(df[df['catégorie'] == cat]['description']).dropna().apply(clean_text)
    # Unigrammes
    mots = " ".join(descriptions).split()
    mots = [mot for mot in mots if mot not in ALL_STOPWORDS and len(mot) > 1]
    compteur_uni = Counter(mots)
    for mot, freq in compteur_uni.most_common(20):
        rows.append({
            'catégorie': cat,
            'expression': mot,
            'type': 'unigramme',
            'fréquence': freq
        })
    # Bigrams et trigrams
    for n, ngram_type in [(2, 'bigramme'), (3, 'trigramme')]:
        vectorizer = CountVectorizer(ngram_range=(n, n), min_df=1, stop_words=list(ALL_STOPWORDS))
        if not descriptions.empty:
            X = vectorizer.fit_transform(descriptions)
            sum_words = X.sum(axis=0)
            words_freq = [(word, sum_words[0, idx]) for word, idx in vectorizer.vocabulary_.items()]
            words_freq = sorted(words_freq, key=lambda x: x[1], reverse=True)
            for phrase, freq in words_freq[:20]:
                rows.append({
                    'catégorie': cat,
                    'expression': phrase,
                    'type': ngram_type,
                    'fréquence': freq
                })

# Exporter en CSV
result_df = pd.DataFrame(rows)
result_df.to_csv("data/Affid/modele/frequences_expressions_categories.csv", index=False, encoding="utf-8-sig")

print("Fichier CSV généré : data/Affid/modele/frequences_expressions_categories.csv") 