import pandas as pd
import os

# Créer le dictionnaire de données avec des listes de même longueur
categories = []
mots_cles = []

# Connexion/Accès (30 mots-clés)
connexion_mots = [
    'login', 'connexion', 'connect', 'authentification', 'password',
    'mot de passe', 'accès', 'access', 'se connecter', 'se déconnecter',
    'identifier', 'identification', 'session', 'token', 'clé',
    'key', 'mdp', 'utilisateur', 'user', 'compte',
    'account', 'profil', 'profile', 'impossible de se connecter', 'login ne marche pas',
    'mot de passe oublié', 'session expirée', 'accès refusé', 'authentification échoue', 'déconnexion'
]
categories.extend(['Connexion/Accès'] * len(connexion_mots))
mots_cles.extend(connexion_mots)

# Fonctionnalités (25 mots-clés)
fonctionnalites_mots = [
    'erreur', 'error', 'bug', 'problème', 'problem',
    'ne fonctionne', 'doesn\'t work', 'impossible', 'can\'t', 'ne peut pas',
    'ne marche pas', 'bloqué', 'blocked', 'planté', 'crashed',
    'dysfonctionnement', 'anormal', 'strange', 'inattendu', 'comportement',
    'fonction bloquée', 'exception', 'ne répond plus', 'gelé', 'stuck'
]
categories.extend(['Fonctionnalités'] * len(fonctionnalites_mots))
mots_cles.extend(fonctionnalites_mots)

# Données (25 mots-clés)
donnees_mots = [
    'données', 'data', 'fichier', 'file', 'document',
    'information', 'sauvegarder', 'save', 'enregistrer', 'record',
    'perdu', 'lost', 'supprimé', 'deleted', 'corrompu',
    'corrupted', 'synchronisation', 'sync', 'import', 'export',
    'backup', 'sauvegarde', 'restaurer', 'restore', 'perte de données'
]
categories.extend(['Données'] * len(donnees_mots))
mots_cles.extend(donnees_mots)

# Interface (25 mots-clés)
interface_mots = [
    'interface', 'écran', 'screen', 'affichage', 'display',
    'bouton', 'button', 'menu', 'page', 'fenêtre',
    'window', 'cliquer', 'click', 'naviguer', 'navigate',
    'visible', 'invisible', 'caché', 'hidden', 'navigation',
    'responsive', 'mobile', 'design', 'ergonomie', 'usabilité'
]
categories.extend(['Interface'] * len(interface_mots))
mots_cles.extend(interface_mots)

# Performance (20 mots-clés)
performance_mots = [
    'lent', 'slow', 'performance', 'rapidité', 'speed',
    'chargement', 'loading', 'timeout', 'délai', 'delay',
    'gelé', 'frozen', 'stuck', 'mémoire', 'memory',
    'cpu', 'processeur', 'ressources', 'optimisation', 'lenteur'
]
categories.extend(['Performance'] * len(performance_mots))
mots_cles.extend(performance_mots)

# Configuration (20 mots-clés)
configuration_mots = [
    'configuration', 'config', 'paramètre', 'setting', 'option',
    'installer', 'install', 'mise à jour', 'update', 'compte',
    'account', 'profil', 'profile', 'paramètres', 'options',
    'installation', 'configuration', 'setup', 'initialisation', 'démarrage'
]
categories.extend(['Configuration'] * len(configuration_mots))
mots_cles.extend(configuration_mots)

# Facturation (70 mots-clés)
facturation_mots = [
    'tarif', 'prix', 'facture', 'remboursement', 'cotation',
    'honoraires', 'dépassement', 'tiers payant', 'feuille de soins', 'ngap',
    'ccam', 'exonération', 'ald', 'c2s', 'ivg',
    'téléconsultation', 'majoration', 'pav', 'association d\'actes', 'patient étranger',
    'taux de prise en charge', 'maternité', 'mt', 'dmt', 'sncf',
    'dégradé', 'soins anonyme', 'base tarif', 'tarif sécu', 'code 7',
    'fmv', 'grossesse', '6 semaines', 'tcs', '50 euros',
    'md', 'vsp', 'mn', 'mm', 'hors garde',
    'participation forfaitaire', 'patient hospitalisé', '24 euros', '100% amo', 'affection longue durée',
    'kiné', 'orthophoniste', 'conventionné', 'optam', 'sf',
    '16.5', '7.5', 'codes sf', 'sécurité sociale', 'carte vitale',
    'demandeur asile', 'fse', 'grossesse gémellaire', '70%', 'discipline medico tarifaire',
    'cpam', 'agréé', 'feuille soins', 'numéro sécu', 'sans cv',
    'anonyme', 'anonymisé', 'facturation', 'billing', 'payment'
]
categories.extend(['Facturation'] * len(facturation_mots))
mots_cles.extend(facturation_mots)

# Sécurité (25 mots-clés)
securite_mots = [
    'sécurité', 'security', 'virus', 'malware', 'spam',
    'phishing', 'hack', 'piratage', 'breach', 'fuite',
    'vol', 'theft', 'permission', 'autorisation', 'accès non autorisé',
    'unauthorized access', 'chiffrement', 'encryption', 'cryptage', 'firewall',
    'antivirus', 'protection', 'backup', 'sauvegarde', 'récupération'
]
categories.extend(['Sécurité'] * len(securite_mots))
mots_cles.extend(securite_mots)

# Réseau (25 mots-clés)
reseau_mots = [
    'réseau', 'network', 'internet', 'connexion internet', 'wi-fi',
    'wifi', 'lan', 'wan', 'serveur', 'server',
    'client', 'proxy', 'vpn', 'routeur', 'router',
    'switch', 'modem', 'bande passante', 'bandwidth', 'latence',
    'latency', 'timeout', 'connexion lente', 'slow connection', 'déconnexion'
]
categories.extend(['Réseau'] * len(reseau_mots))
mots_cles.extend(reseau_mots)

# Formation (25 mots-clés)
formation_mots = [
    'formation', 'training', 'apprentissage', 'learning', 'tutoriel',
    'tutorial', 'guide', 'manuel', 'manual', 'documentation',
    'help', 'aide', 'support', 'question', 'comment faire',
    'how to', 'procédure', 'procedure', 'processus', 'process',
    'workflow', 'étape', 'step', 'instruction', 'explication'
]
categories.extend(['Formation'] * len(formation_mots))
mots_cles.extend(formation_mots)

# Maintenance (25 mots-clés)
maintenance_mots = [
    'maintenance', 'maintenu', 'maintained', 'update', 'mise à jour',
    'upgrade', 'version', 'release', 'patch', 'correctif',
    'fix', 'correction', 'amélioration', 'improvement', 'optimisation',
    'optimization', 'performance', 'refactoring', 'refactorisation', 'cleanup',
    'nettoyage', 'clean', 'organiser', 'organize', 'structure'
]
categories.extend(['Maintenance'] * len(maintenance_mots))
mots_cles.extend(maintenance_mots)

# Intégration (25 mots-clés)
integration_mots = [
    'intégration', 'integration', 'api', 'webservice', 'web service',
    'soap', 'rest', 'json', 'xml', 'connecteur',
    'connector', 'plugin', 'extension', 'module', 'composant',
    'component', 'interface', 'liaison', 'link', 'synchronisation',
    'sync', 'import', 'export', 'échange', 'exchange'
]
categories.extend(['Intégration'] * len(integration_mots))
mots_cles.extend(integration_mots)

# Reporting (25 mots-clés)
reporting_mots = [
    'reporting', 'rapport', 'report', 'statistique', 'statistic',
    'analyse', 'analysis', 'dashboard', 'tableau de bord', 'graphique',
    'chart', 'graph', 'visualisation', 'visualization', 'export',
    'données', 'data', 'métrique', 'metric', 'kpi',
    'indicateur', 'indicator', 'mesure', 'measure', 'suivi'
]
categories.extend(['Reporting'] * len(reporting_mots))
mots_cles.extend(reporting_mots)

# Vérifier que les listes ont la même longueur
print(f"Longueur de la liste 'categories': {len(categories)}")
print(f"Longueur de la liste 'mots_cles': {len(mots_cles)}")

if len(categories) != len(mots_cles):
    print("❌ ERREUR: Les listes n'ont pas la même longueur!")
    exit(1)

# Créer le DataFrame
df = pd.DataFrame({
    'Categorie': categories,
    'Mots_cles': mots_cles
})

# Créer le dossier s'il n'existe pas
os.makedirs('data/Affid/modele', exist_ok=True)

# Sauvegarder en Excel
output_path = 'data/Affid/modele/Categories_Mots_Cles_Personnalisees.xlsx'
df.to_excel(output_path, index=False)

print('✅ Fichier Excel créé avec succès !')
print(f'📁 Chemin: {output_path}')
print(f'📊 Nombre de catégories: {df["Categorie"].nunique()}')
print(f'🔤 Nombre total de mots-clés: {len(df)}')

print('\n📋 Catégories disponibles:')
for cat in df['Categorie'].unique():
    count = len(df[df['Categorie'] == cat])
    print(f'  - {cat}: {count} mots-clés')

# Vérifier que le fichier peut être lu
try:
    test_df = pd.read_excel(output_path)
    print(f'\n✅ Test de lecture réussi!')
    print(f'📋 Aperçu des données:')
    print(test_df.head())
except Exception as e:
    print(f'\n❌ Erreur lors du test de lecture: {e}') 