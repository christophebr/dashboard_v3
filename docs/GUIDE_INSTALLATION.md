# Guide d'installation - Nouveau PC

## Prérequis

### 1. Installer Python

1. Téléchargez Python depuis : https://www.python.org/downloads/
2. **IMPORTANT** : Lors de l'installation, cochez la case **"Add Python to PATH"**
3. Choisissez "Install Now" ou "Customize installation" (recommandé)
4. Si vous choisissez "Customize", assurez-vous que "pip" est sélectionné

### 2. Vérifier l'installation

Ouvrez un nouveau terminal PowerShell ou CMD et exécutez :
```bash
python --version
```

Vous devriez voir quelque chose comme : `Python 3.x.x`

## Installation de l'environnement du projet

### Option 1 : Utiliser le script automatique (Recommandé)

1. Double-cliquez sur `setup.bat` dans l'explorateur Windows
2. Le script va :
   - Vérifier que Python est installé
   - Créer un environnement virtuel (`venv`)
   - Installer tous les packages nécessaires depuis `requirements.txt`

### Option 2 : Installation manuelle

Si vous préférez installer manuellement :

```bash
# Naviguer vers le dossier du projet
cd "c:\Users\ChristopheBRICHET\OneDrive - OLAQIN\Python\depot_new"

# Créer l'environnement virtuel
python -m venv venv

# Activer l'environnement virtuel
venv\Scripts\activate

# Installer les packages
pip install --upgrade pip
pip install -r requirements.txt
```

## Lancer le projet

Une fois l'installation terminée :

1. Double-cliquez sur `launch.bat`
2. L'application Streamlit devrait s'ouvrir dans votre navigateur

## Dépannage

### Python n'est pas reconnu

- Vérifiez que Python est bien installé : `python --version`
- Si cela ne fonctionne pas, réinstallez Python en cochant "Add Python to PATH"
- Redémarrez votre terminal après l'installation

### Erreurs lors de l'installation des packages

- Assurez-vous d'avoir une connexion Internet stable
- Certains packages peuvent nécessiter des compilateurs C++ (comme `lightgbm`, `xgboost`)
  - Téléchargez "Build Tools for Visual Studio" : https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022
  - Installez "C++ build tools"

### L'environnement virtuel existe déjà

Si vous avez un ancien environnement virtuel (`testenv`), vous pouvez :
- Le supprimer et laisser `setup.bat` créer un nouveau `venv`
- Ou modifier `launch.bat` pour utiliser `testenv` au lieu de `venv`

## Notes

- L'environnement virtuel est créé dans le dossier `venv/`
- Ne supprimez pas ce dossier, il contient tous les packages installés
- Vous devez activer l'environnement virtuel avant d'utiliser le projet (fait automatiquement par `launch.bat`)
