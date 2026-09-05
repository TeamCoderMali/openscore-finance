#!/bin/bash
# OpenScore Finance Mobile — Démarrage rapide
# Usage: ./start.sh [ios|android]

PLATFORM=${1:-ios}

echo "🚀 OpenScore Finance Mobile — Démarrage..."
echo ""

# 1. Démarrer le backend si pas encore démarré
echo "📡 Vérification du backend FastAPI..."
if ! curl -s http://localhost:8000/docs > /dev/null 2>&1; then
  echo "⚠️  Backend non détecté sur :8000"
  echo "   Démarrez le backend d'abord avec:"
  echo "   cd backend && source venv/bin/activate && uvicorn app.main:app --reload"
  echo ""
fi

# 2. Lancer l'app Flutter
echo "📱 Lancement sur $PLATFORM..."
cd mobile

if [ "$PLATFORM" = "android" ]; then
  # Android emulator uses 10.0.2.2 to reach host machine
  echo "   (Pour Android: l'app contacte 10.0.2.2:8000 — assurez-vous que l'émulateur est démarré)"
  flutter run -d android
else
  # iOS simulator uses localhost
  echo "   (Pour iOS: l'app contacte localhost:8000)"
  flutter run -d ios
fi
