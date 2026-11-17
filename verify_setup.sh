#!/bin/bash
echo "=========================================="
echo "Interview App - Setup Verification"
echo "=========================================="
echo ""

# Check Docker running
echo "🐳 Docker Status:"
docker compose ps 2>/dev/null | tail -3

echo ""
echo "📁 Project Files:"
ls -1 *.md app/*.py test_api.py 2>/dev/null | wc -l | xargs echo "  Files: "

echo ""
echo "🧪 Quick API Test:"
AUTH=$(echo -n "interviewer:super-segura" | base64)
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/api/auth/login \
  -H "Authorization: Basic $AUTH" 2>/dev/null)
if [ "$RESPONSE" = "200" ]; then
  echo "  ✅ API responding (HTTP $RESPONSE)"
else
  echo "  ⚠️  API not responding (HTTP $RESPONSE)"
fi

echo ""
echo "📊 Sessions:"
curl -s http://127.0.0.1:8000/api/sessions \
  -H "Authorization: Basic $AUTH" 2>/dev/null | grep -o '"interview_id"' | wc -l | xargs echo "  Sessions stored: "

echo ""
echo "📖 Documentation:"
ls -1 *.md 2>/dev/null | xargs -I {} echo "  ✅ {}"

echo ""
echo "=========================================="
echo "Status: Ready for model download"
echo "=========================================="
echo ""
echo "Next: docker compose --profile init run --rm ollama-init"
