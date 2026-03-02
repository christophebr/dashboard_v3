#!/bin/bash
# Script pour initialiser le dépôt Git et préparer le premier push

set -e
cd "$(dirname "$0")/.."

echo "🔧 Initialisation du dépôt Git..."
git init
git add .
git status

echo ""
echo "📝 Création du premier commit..."
git commit -m "Initial commit - Dashboard Support Olaqin"

echo ""
echo "✅ Dépôt initialisé."
echo ""
echo "📤 Pour pousser vers GitHub :"
echo "   1. Créez un dépôt vide sur github.com (ex: dashboard-support-olaqin)"
echo "   2. Puis exécutez :"
echo ""
echo "      git remote add origin https://github.com/VOTRE_USERNAME/dashboard-support-olaqin.git"
echo "      git branch -M main"
echo "      git push -u origin main"
echo ""
