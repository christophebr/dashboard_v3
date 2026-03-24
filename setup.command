#!/bin/bash

# Script d'installation pour macOS - crée l'environnement virtuel et installe les dépendances

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "========================================"
echo "  Installation - Environnement Python"
echo "========================================"
echo ""

# Vérifier Python
if ! command -v python3 &>/dev/null; then
    echo "ERREUR : Python 3 n'est pas installé."
    echo "Installez Python depuis https://www.python.org/downloads/"
    echo ""
    read -p "Appuyez sur Entrée pour fermer..."
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1)
echo "Python détecté : $PYTHON_VERSION"
echo ""

# Priorité : testenv (existant) ou venv
VENV_DIR=""
if [ -d "$DIR/testenv" ] && [ -f "$DIR/testenv/bin/activate" ]; then
    echo "L'environnement virtuel 'testenv' existe déjà."
    VENV_DIR="$DIR/testenv"
elif [ -d "$DIR/venv" ] && [ -f "$DIR/venv/bin/activate" ]; then
    echo "L'environnement virtuel 'venv' existe déjà."
    VENV_DIR="$DIR/venv"
else
    echo "Création de l'environnement virtuel (testenv)..."
    echo ""
    echo "NOTE : Le projet est dans OneDrive. La création peut prendre 2-5 minutes."
    echo "       Si le script semble bloqué, patientez - ne fermez pas la fenêtre."
    echo ""
    
    if python3 -m venv "$DIR/testenv"; then
        echo "Environnement virtuel créé avec succès."
        VENV_DIR="$DIR/testenv"
    else
        echo "ERREUR : Impossible de créer l'environnement virtuel."
        echo "Essayez de lancer depuis le Terminal : python3 -m venv testenv"
        echo ""
        read -p "Appuyez sur Entrée pour fermer..."
        exit 1
    fi
fi

echo ""
echo "Activation de l'environnement virtuel..."
source "$VENV_DIR/bin/activate"

echo "Mise à jour de pip..."
python -m pip install --upgrade pip -q

echo "Installation des packages (peut prendre quelques minutes)..."
if python -m pip install -r requirements.txt; then
    echo ""
    echo "========================================"
    echo "  Installation terminée avec succès !"
    echo "========================================"
    echo ""
    echo "Lancez l'application avec : launch.command"
    echo ""
else
    echo ""
    echo "ATTENTION : Certains packages n'ont peut-être pas été installés."
    echo "Vérifiez les messages d'erreur ci-dessus."
fi

echo ""
read -p "Appuyez sur Entrée pour fermer..."
