import pandas as pd

df = pd.read_excel('data/Affid/modele/Mots_cles.xlsx')

print('Codes CCAM dans Facturation - CCAM:')
ccam_codes = df[df['Categorie'] == 'Facturation - CCAM']['Mots'].head(5).tolist()
print(ccam_codes)

print('\nCodes NGAP dans Facturation - NGAP:')
ngap_codes = df[df['Categorie'] == 'Facturation - NGAP']['Mots'].head(10).tolist()
print(ngap_codes)

print('\nVérification si les codes CCAM sont aussi dans NGAP:')
for code in ccam_codes:
    in_ngap = code in df[df['Categorie'] == 'Facturation - NGAP']['Mots'].tolist()
    print(f'{code}: {in_ngap}')

print('\nVérification inverse - codes NGAP dans CCAM:')
for code in ngap_codes[:5]:  # Vérifier les 5 premiers codes NGAP
    in_ccam = code in df[df['Categorie'] == 'Facturation - CCAM']['Mots'].tolist()
    print(f'{code}: {in_ccam}')

print('\nNombre total de codes par catégorie:')
print(df.groupby('Categorie')['Mots'].count())

print('\nOrdre des catégories dans le fichier:')
print(df['Categorie'].unique().tolist()) 