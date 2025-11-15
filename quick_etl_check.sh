#!/bin/bash

# Simple ETL Test - No Auth Required
# This checks the ETL endpoints directly

BACKEND_URL="http://localhost:8000"

echo "========================================"
echo "Simple ETL Status Check"
echo "========================================"
echo ""

# Get your token from the browser:
echo "To get your auth token:"
echo "1. Open your browser and login to the app"
echo "2. Open Developer Tools (F12)"
echo "3. Go to Application/Storage > Local Storage"
echo "4. Find 'token' or 'access_token' and copy it"
echo ""
read -p "Paste your auth token here: " TOKEN
echo ""

if [ -z "$TOKEN" ]; then
    echo "No token provided. Cannot continue."
    exit 1
fi

# Check ETL stats
echo "📊 Checking ETL Statistics..."
echo ""
STATS=$(curl -s -H "Authorization: Bearer $TOKEN" "$BACKEND_URL/api/etl/stats")

if echo "$STATS" | grep -q "status"; then
    echo "$STATS" | jq '.'
    echo ""

    # Extract counts
    TOTAL=$(echo $STATS | jq -r '.stats.total_documents // 0')
    VECTORIZED=$(echo $STATS | jq -r '.stats.vectorized_documents // 0')
    PENDING=$(echo $STATS | jq -r '.stats.pending_approvals // 0')

    echo "Summary:"
    echo "  📄 Total documents: $TOTAL"
    echo "  ✅ Vectorized: $VECTORIZED"
    echo "  ⏸️  Pending approval: $PENDING"
    echo ""
else
    echo "❌ Failed to get ETL stats"
    echo "Response: $STATS"
    echo ""
    echo "Note: You must be a SUPERUSER to access ETL endpoints"
    exit 1
fi

# List recent documents
echo "📚 Recent KB Documents:"
echo ""
DOCS=$(curl -s -H "Authorization: Bearer $TOKEN" "$BACKEND_URL/api/etl/kb-documents?limit=5")
echo "$DOCS" | jq '.documents[] | {file_name, is_vectorized, vector_count, uploaded_at}' 2>/dev/null || echo "No documents found or not a superuser"
echo ""

# List recent jobs
echo "⚙️  Recent Processing Jobs:"
echo ""
JOBS=$(curl -s -H "Authorization: Bearer $TOKEN" "$BACKEND_URL/api/etl/processing-jobs?limit=5")
echo "$JOBS" | jq '.jobs[] | {file: .document.file_name, status, chunks: .chunks_processed, vectors: .vectors_created}' 2>/dev/null || echo "No jobs found"
echo ""

# Check for pending approvals
echo "⏸️  Pending Approvals:"
echo ""
PENDING_LIST=$(curl -s -H "Authorization: Bearer $TOKEN" "$BACKEND_URL/api/etl/pending-updates?status=pending")
PENDING_COUNT=$(echo $PENDING_LIST | jq -r '.count // 0')

if [ "$PENDING_COUNT" -gt "0" ]; then
    echo "$PENDING_LIST" | jq '.pending_updates[] | {file: .document.file_name, type: .update_type, similarity: .similarity_score}'
else
    echo "✓ No pending approvals"
fi
echo ""

# Offer to trigger manual scan
echo "========================================"
read -p "Trigger manual ETL scan now? (y/n): " TRIGGER

if [ "$TRIGGER" = "y" ] || [ "$TRIGGER" = "Y" ]; then
    echo ""
    echo "🔄 Triggering ETL scan..."
    SCAN_RESULT=$(curl -s -X POST -H "Authorization: Bearer $TOKEN" "$BACKEND_URL/api/etl/scan")
    echo "$SCAN_RESULT" | jq '.'
    echo ""
    echo "✓ Scan complete! Check the stats above."
fi

echo ""
echo "========================================"
echo "Test Complete!"
echo "========================================"
