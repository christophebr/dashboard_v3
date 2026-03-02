@echo off
echo ========================================
echo Installation de l'environnement Python
echo ========================================
echo.

cd /d "%~dp0"

echo Verification de l'installation de Python 3.11...
py -3.11 --version >nul 2>&1
if errorlevel 1 (
    echo ERREUR: Python 3.11 n'est pas installe.
    echo.
    echo Veuillez installer Python 3.11 depuis https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

echo Python 3.11 detecte!
py -3.11 --version
echo.

if exist "venv\Scripts\activate.bat" (
    echo L'environnement virtuel Windows existe deja.
    goto activate
)

if exist "venv" (
    echo Suppression de l'ancien dossier venv...
    rmdir /S /Q "venv"
)

echo Creation d'un nouvel environnement virtuel Windows (Python 3.11)...
py -3.11 -m venv venv
if errorlevel 1 (
    echo ERREUR: Impossible de creer l'environnement virtuel.
    pause
    exit /b 1
)
echo Environnement virtuel cree avec succes!
echo.

:activate
echo Activation de l'environnement virtuel...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERREUR: Impossible d'activer l'environnement virtuel.
    pause
    exit /b 1
)
echo.

echo Mise a jour de pip...
python -m pip install --upgrade pip
echo.

echo Installation des packages depuis requirements.txt...
echo Cela peut prendre plusieurs minutes...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo ATTENTION: Certains packages n'ont peut-etre pas ete installes correctement.
    echo Verifiez les messages d'erreur ci-dessus.
    echo.
) else (
    echo.
    echo ========================================
    echo Installation terminee avec succes!
    echo ========================================
    echo.
    echo Vous pouvez maintenant lancer le projet avec launch.bat
    echo.
)

pause
