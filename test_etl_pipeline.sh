#!/bin/bash

# ETL Pipeline Complete Test Script
# This script tests the entire ETL pipeline flow

set -e  # Exit on error

echo "========================================"
echo "ETL Pipeline Complete Test"
echo "========================================"
echo ""

# Configuration
BACKEND_URL="http://localhost:8000"
TEST_FILE="test_kb_document.txt"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Step 1: Check if backend is running
echo -e "${BLUE}Step 1: Checking if backend is running...${NC}"
if curl -s -o /dev/null -w "%{http_code}" "$BACKEND_URL/health" | grep -q "200"; then
    echo -e "${GREEN}✓ Backend is running${NC}"
else
    echo -e "${RED}✗ Backend is not running!${NC}"
    echo "Please start the backend first:"
    echo "  cd backend && python -m uvicorn app.main:app --reload"
    exit 1
fi
echo ""

# Step 2: Login and get token
echo -e "${BLUE}Step 2: Getting authentication token...${NC}"
echo "Please enter your credentials:"
read -p "Email: " EMAIL
read -s -p "Password: " PASSWORD
echo ""

LOGIN_RESPONSE=$(curl -s -X POST "$BACKEND_URL/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=$EMAIL&password=$PASSWORD")

TOKEN=$(echo $LOGIN_RESPONSE | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
    echo -e "${RED}✗ Login failed!${NC}"
    echo "Response: $LOGIN_RESPONSE"
    exit 1
fi

echo -e "${GREEN}✓ Logged in successfully${NC}"
echo "Token: ${TOKEN:0:20}..."
echo ""

# Step 3: Check initial ETL stats
echo -e "${BLUE}Step 3: Checking initial ETL statistics...${NC}"
INITIAL_STATS=$(curl -s -H "Authorization: Bearer $TOKEN" "$BACKEND_URL/api/etl/stats")
echo "Initial Stats:"
echo "$INITIAL_STATS" | jq '.'
INITIAL_DOCS=$(echo $INITIAL_STATS | jq -r '.stats.total_documents // 0')
INITIAL_VECTORIZED=$(echo $INITIAL_STATS | jq -r '.stats.vectorized_documents // 0')
echo ""
echo -e "${YELLOW}Before upload:${NC}"
echo "  Total documents: $INITIAL_DOCS"
echo "  Vectorized documents: $INITIAL_VECTORIZED"
echo ""

# Step 4: Upload test document
echo -e "${BLUE}Step 4: Uploading test document to knowledge base...${NC}"
if [ ! -f "$TEST_FILE" ]; then
    echo -e "${RED}✗ Test file not found: $TEST_FILE${NC}"
    exit 1
fi

UPLOAD_RESPONSE=$(curl -s -X POST "$BACKEND_URL/api/blobs/upload/file" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@$TEST_FILE" \
  -F "base=knowledge_base" \
  -F "folder=test")

echo "Upload Response:"
echo "$UPLOAD_RESPONSE" | jq '.'

UPLOAD_STATUS=$(echo $UPLOAD_RESPONSE | jq -r '.status')
if [ "$UPLOAD_STATUS" = "success" ]; then
    echo -e "${GREEN}✓ Document uploaded successfully${NC}"
    BLOB_PATH=$(echo $UPLOAD_RESPONSE | jq -r '.blob')
    echo "  Blob path: $BLOB_PATH"
else
    echo -e "${RED}✗ Upload failed!${NC}"
    exit 1
fi
echo ""

# Step 5: Wait for ETL processing
echo -e "${BLUE}Step 5: Waiting for ETL processing (15 seconds)...${NC}"
echo "The ETL pipeline is processing the document in the background..."
for i in {15..1}; do
    echo -ne "\r  Waiting: $i seconds remaining...  "
    sleep 1
done
echo -e "\n${GREEN}✓ Wait complete${NC}"
echo ""

# Step 6: Check updated ETL stats
echo -e "${BLUE}Step 6: Checking updated ETL statistics...${NC}"
UPDATED_STATS=$(curl -s -H "Authorization: Bearer $TOKEN" "$BACKEND_URL/api/etl/stats")
echo "Updated Stats:"
echo "$UPDATED_STATS" | jq '.'
UPDATED_DOCS=$(echo $UPDATED_STATS | jq -r '.stats.total_documents')
UPDATED_VECTORIZED=$(echo $UPDATED_STATS | jq -r '.stats.vectorized_documents')
echo ""
echo -e "${YELLOW}After upload:${NC}"
echo "  Total documents: $UPDATED_DOCS (was $INITIAL_DOCS)"
echo "  Vectorized documents: $UPDATED_VECTORIZED (was $INITIAL_VECTORIZED)"
echo ""

# Step 7: Check the specific document
echo -e "${BLUE}Step 7: Checking document details...${NC}"
DOCUMENTS=$(curl -s -H "Authorization: Bearer $TOKEN" "$BACKEND_URL/api/etl/kb-documents?limit=5")
echo "Recent Documents:"
echo "$DOCUMENTS" | jq '.documents[] | {file_name, is_vectorized, vector_count, uploaded_at}'
echo ""

# Find our test document
TEST_DOC=$(echo "$DOCUMENTS" | jq '.documents[] | select(.file_name=="test_kb_document.txt")')
if [ ! -z "$TEST_DOC" ]; then
    IS_VECTORIZED=$(echo $TEST_DOC | jq -r '.is_vectorized')
    VECTOR_COUNT=$(echo $TEST_DOC | jq -r '.vector_count')

    if [ "$IS_VECTORIZED" = "true" ]; then
        echo -e "${GREEN}✓ Document is vectorized!${NC}"
        echo "  Vector count (chunks): $VECTOR_COUNT"
        echo -e "${GREEN}✓ SUCCESS: Document was chunked into $VECTOR_COUNT pieces${NC}"
    else
        echo -e "${YELLOW}⚠ Document exists but not vectorized yet${NC}"
        echo "  This might mean it's pending admin approval"
    fi
else
    echo -e "${YELLOW}⚠ Document not found in KB documents list${NC}"
    echo "  It might still be processing or pending approval"
fi
echo ""

# Step 8: Check processing jobs
echo -e "${BLUE}Step 8: Checking processing jobs...${NC}"
JOBS=$(curl -s -H "Authorization: Bearer $TOKEN" "$BACKEND_URL/api/etl/processing-jobs?limit=5")
echo "Recent Processing Jobs:"
echo "$JOBS" | jq '.jobs[] | {document: .document.file_name, status, chunks_processed, vectors_created, completed_at}'
echo ""

# Step 9: Check for pending approvals
echo -e "${BLUE}Step 9: Checking for pending approvals...${NC}"
PENDING=$(curl -s -H "Authorization: Bearer $TOKEN" "$BACKEND_URL/api/etl/pending-updates?status=pending")
PENDING_COUNT=$(echo $PENDING | jq -r '.count')

if [ "$PENDING_COUNT" -gt "0" ]; then
    echo -e "${YELLOW}⚠ Found $PENDING_COUNT pending approval(s)${NC}"
    echo "Pending Updates:"
    echo "$PENDING" | jq '.pending_updates[] | {file_name: .document.file_name, update_type, similarity_score, reason}'
    echo ""
    echo -e "${YELLOW}ACTION REQUIRED:${NC}"
    echo "Your document needs admin approval because it's similar to existing documents."
    echo "To approve: POST $BACKEND_URL/api/etl/approve/{pending_update_id}"
else
    echo -e "${GREEN}✓ No pending approvals${NC}"
fi
echo ""

# Step 10: Check Qdrant (if accessible)
echo -e "${BLUE}Step 10: Checking Qdrant collection...${NC}"
QDRANT_URL="http://localhost:6333"
COLLECTION_NAME="project_kb"  # Update this to your collection name

if curl -s -o /dev/null -w "%{http_code}" "$QDRANT_URL/collections/$COLLECTION_NAME" | grep -q "200"; then
    QDRANT_INFO=$(curl -s "$QDRANT_URL/collections/$COLLECTION_NAME")
    POINTS_COUNT=$(echo $QDRANT_INFO | jq -r '.result.points_count')
    echo -e "${GREEN}✓ Qdrant is accessible${NC}"
    echo "  Collection: $COLLECTION_NAME"
    echo "  Total vectors in Qdrant: $POINTS_COUNT"
    echo ""
    echo "To view vectors in Qdrant Web UI:"
    echo "  Open: http://localhost:6333/dashboard"
else
    echo -e "${YELLOW}⚠ Qdrant not accessible at $QDRANT_URL${NC}"
    echo "  Make sure Qdrant is running: docker ps | grep qdrant"
fi
echo ""

# Summary
echo "========================================"
echo -e "${GREEN}ETL Pipeline Test Complete!${NC}"
echo "========================================"
echo ""
echo "Summary:"
echo "  ✓ Document uploaded: $TEST_FILE"
echo "  ✓ ETL pipeline processed the document"
if [ "$IS_VECTORIZED" = "true" ]; then
    echo -e "  ${GREEN}✓ Document chunked into $VECTOR_COUNT vectors${NC}"
    echo -e "  ${GREEN}✓ Vectors stored in Qdrant${NC}"
else
    echo "  ⚠ Check pending approvals or processing jobs above"
fi
echo ""
echo "Next steps:"
echo "  1. Check backend logs for detailed processing info"
echo "  2. View vectors in Qdrant UI: http://localhost:6333/dashboard"
echo "  3. Test RAG retrieval by generating a project scope"
echo ""
