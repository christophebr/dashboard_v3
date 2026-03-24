#!/bin/bash

# Ce script lance l'application Streamlit en utilisant un environnement virtuel local,
# sans dépendre de conda.

# Récupère le dossier du script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Choisir l'interpréteur Python (priorité au venv, avec python3 si python n'existe pas)
if [ -d "$DIR/testenv" ] && [ -f "$DIR/testenv/bin/activate" ]; then
  echo "Activation de l'environnement virtuel testenv..."
  source "$DIR/testenv/bin/activate"
  if [ -x "$DIR/testenv/bin/python" ]; then
    PYTHON="$DIR/testenv/bin/python"
  else
    PYTHON="$DIR/testenv/bin/python3"
  fi
elif [ -d "$DIR/venv" ] && [ -f "$DIR/venv/bin/activate" ]; then
  echo "Activation de l'environnement virtuel venv..."
  source "$DIR/venv/bin/activate"
  if [ -x "$DIR/venv/bin/python" ]; then
    PYTHON="$DIR/venv/bin/python"
  else
    PYTHON="$DIR/venv/bin/python3"
  fi
else
  echo "ATTENTION : aucun environnement virtuel trouvé (ni testenv ni venv)."
  echo "Le script va utiliser Python système. Assure-toi que les dépendances sont installées."
  if command -v python3 &>/dev/null; then
    PYTHON="python3"
  else
    PYTHON="python"
  fi
fi

# Désactive certains modes interactifs forcés de Python qui peuvent
# provoquer l'apparition d'un prompt >>> après exécution.
unset PYTHONINSPECT
unset PYTHONSTARTUP
# Force Python à envoyer la sortie immédiatement (pour le débogage)
export PYTHONUNBUFFERED=1

# Fichiers de log pour diagnostiquer un éventuel problème de lancement
LOG_FILE="$DIR/launch_debug.log"
APP_LOG="$DIR/app_launch.log"
{
  echo "===== Lancement $(date) ====="
  echo "DIR=$DIR"
  echo "PYTHON=$PYTHON"
  echo "VIRTUAL_ENV=$VIRTUAL_ENV"
} >> "$LOG_FILE" 2>&1

# Lancement de l'application Streamlit - affichage dans le terminal ET copie dans le log
echo ""
echo "Lancement de Streamlit..."
echo "Logs : launch_debug.log et app_launch.log"
echo "Patientez 10-30 secondes, puis ouvrez http://localhost:8501"
echo ""
# -u = sortie Python non bufferisée (messages visibles immédiatement)
"$PYTHON" -u -m streamlit run app.py --logger.level=debug 2>&1 | tee -a "$LOG_FILE"