@echo off

:: Change to the script directory
cd /d "%~dp0"

:: Vérifier si l'environnement virtuel existe
if not exist "venv\Scripts\activate.bat" (
    echo ERREUR: L'environnement virtuel n'existe pas.
    echo.
    echo Veuillez d'abord executer setup.bat pour installer l'environnement.
    echo.
    pause
    exit /b 1
)

:: Activate virtual environment
call venv\Scripts\activate.bat

:: Run the app with streamlit
streamlit run app.py

pause 