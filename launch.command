#!/bin/bash

# Ce script lance l'application Streamlit en utilisant un environnement virtuel local,
# sans dépendre de conda.

# Récupère le dossier du script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Affiche un message d'erreur et garde le terminal ouvert si on quitte mal
on_error() {
  echo ""
  echo "========================================================"
  echo "  ERREUR : le lancement du dashboard a échoué (code $1)."
  echo "  Consulte les logs : launch_debug.log et app_launch.log"
  echo "========================================================"
  echo ""
  echo "Appuie sur Entrée pour fermer cette fenêtre..."
  read -r _
  exit "$1"
}

# Fichiers de log
LOG_FILE="$DIR/launch_debug.log"
APP_LOG="$DIR/app_launch.log"

# Réinitialise les logs pour ne pas accumuler indéfiniment
: > "$LOG_FILE"
: > "$APP_LOG"

{
  echo "===== Lancement $(date) ====="
  echo "DIR=$DIR"
} >> "$LOG_FILE"

# --- Pré-chargement des fichiers OneDrive critiques ---------------------
# OneDrive peut garder certains fichiers en mode "cloud-only" (non téléchargés).
# Streamlit lit .streamlit/config.toml et .streamlit/secrets.toml au démarrage,
# et plante avec un TimeoutError si ces fichiers ne sont pas disponibles localement.
# On force leur téléchargement en les lisant avant de lancer Streamlit.
echo "Vérification des fichiers de configuration OneDrive..."
for f in ".streamlit/config.toml" ".streamlit/secrets.toml"; do
  if [ -f "$DIR/$f" ]; then
    if ! cat "$DIR/$f" > /dev/null 2>>"$LOG_FILE"; then
      echo "  -> Téléchargement OneDrive de $f en cours..."
      cat "$DIR/$f" > /dev/null 2>>"$LOG_FILE" || true
    fi
  fi
done

# --- Sélection de l'interpréteur Python ---------------------------------
PYTHON=""
if [ -d "$DIR/testenv" ] && [ -f "$DIR/testenv/bin/activate" ]; then
  echo "Activation de l'environnement virtuel testenv..."
  # shellcheck disable=SC1091
  source "$DIR/testenv/bin/activate"
  if [ -x "$DIR/testenv/bin/python" ]; then
    PYTHON="$DIR/testenv/bin/python"
  elif [ -x "$DIR/testenv/bin/python3" ]; then
    PYTHON="$DIR/testenv/bin/python3"
  fi
elif [ -d "$DIR/venv" ] && [ -f "$DIR/venv/bin/activate" ]; then
  echo "Activation de l'environnement virtuel venv..."
  # shellcheck disable=SC1091
  source "$DIR/venv/bin/activate"
  if [ -x "$DIR/venv/bin/python" ]; then
    PYTHON="$DIR/venv/bin/python"
  elif [ -x "$DIR/venv/bin/python3" ]; then
    PYTHON="$DIR/venv/bin/python3"
  fi
else
  echo "ATTENTION : aucun environnement virtuel trouvé (ni testenv ni venv)."
  echo "Le script va utiliser Python système. Assure-toi que les dépendances sont installées."
  if command -v python3 >/dev/null 2>&1; then
    PYTHON="python3"
  elif command -v python >/dev/null 2>&1; then
    PYTHON="python"
  fi
fi

if [ -z "$PYTHON" ] || ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "ERREUR : impossible de trouver un interpréteur Python utilisable."
  on_error 1
fi

# Désactive certains modes interactifs forcés de Python qui peuvent
# provoquer l'apparition d'un prompt >>> après exécution.
unset PYTHONINSPECT
unset PYTHONSTARTUP
# Force Python à envoyer la sortie immédiatement (pour le débogage)
export PYTHONUNBUFFERED=1

{
  echo "PYTHON=$PYTHON"
  echo "VIRTUAL_ENV=$VIRTUAL_ENV"
  "$PYTHON" --version
} >> "$LOG_FILE" 2>&1

# Vérifie que streamlit est bien installé dans l'environnement choisi
if ! "$PYTHON" -c "import streamlit" >/dev/null 2>>"$LOG_FILE"; then
  echo "ERREUR : streamlit n'est pas installé dans l'environnement Python sélectionné."
  echo "  Interpréteur : $PYTHON"
  echo "  Lance ./setup.command (ou pip install -r requirements.txt) pour installer les dépendances."
  on_error 1
fi

# Libère le port 8501 si un ancien processus Streamlit est encore actif.
if command -v lsof >/dev/null 2>&1; then
  OLD_PID=$(lsof -ti tcp:8501 2>/dev/null || true)
  if [ -n "$OLD_PID" ]; then
    echo "Un processus utilise déjà le port 8501 (PID $OLD_PID), arrêt en cours..."
    kill "$OLD_PID" 2>/dev/null || true
    sleep 1
    # Force kill si toujours présent
    if kill -0 "$OLD_PID" 2>/dev/null; then
      kill -9 "$OLD_PID" 2>/dev/null || true
    fi
  fi
fi

# Lancement de l'application Streamlit - affichage dans le terminal ET copie dans le log
echo ""
echo "Lancement de Streamlit..."
echo "Logs : launch_debug.log et app_launch.log"
echo "Patientez 10-30 secondes, puis ouvrez http://localhost:8501"
echo ""

# -u = sortie Python non bufferisée (messages visibles immédiatement)
# `set -o pipefail` pour que le code retour reflète celui de Python
set -o pipefail
"$PYTHON" -u -m streamlit run app.py --logger.level=info 2>&1 | tee -a "$LOG_FILE"
EXIT_CODE=${PIPESTATUS[0]}

if [ "$EXIT_CODE" -ne 0 ]; then
  on_error "$EXIT_CODE"
fi

echo ""
echo "Streamlit s'est arrêté normalement. Appuie sur Entrée pour fermer cette fenêtre..."
read -r _
