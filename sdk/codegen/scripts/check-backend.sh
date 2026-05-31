#!/bin/bash
# Check if Django backend is running and accessible

ENDPOINT="${GRAPHQL_ENDPOINT:-http://localhost:8000/graphql/}"

echo "🔍 Checking backend at $ENDPOINT..."

# Try to reach the endpoint
if curl -f -s -o /dev/null "$ENDPOINT"; then
    echo "✅ Backend is running and accessible"
    exit 0
else
    echo "❌ Backend is not accessible at $ENDPOINT"
    echo ""
    echo "To start the backend:"
    echo "  cd django-backend"
    echo "  python manage.py runserver"
    echo ""
    echo "Or set GRAPHQL_ENDPOINT to a different URL:"
    echo "  export GRAPHQL_ENDPOINT=https://api.soroscan.io/graphql/"
    exit 1
fi
