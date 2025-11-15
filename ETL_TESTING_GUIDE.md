# ETL Pipeline Testing Guide

This guide will walk you through testing the ETL pipeline step-by-step to see how documents are chunked and stored in Qdrant.

## Quick Start - Automated Test

The easiest way to test the complete ETL pipeline:

### Step 1: Start Your Backend
```bash
cd /home/user/scoping-bot/backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Wait for:
```
ETL background scheduler started (runs every 30 minutes).
INFO:     Application startup complete.
```

### Step 2: Run the Automated Test (in a new terminal)
```bash
cd /home/user/scoping-bot
./test_etl_pipeline.sh
```

This script will:
1. ✓ Check if backend is running
2. ✓ Login and get your auth token
3. ✓ Show initial ETL statistics
4. ✓ Upload the test document
5. ✓ Wait for processing (15 seconds)
6. ✓ Show updated statistics
7. ✓ Display document details
8. ✓ Show processing jobs
9. ✓ Check for pending approvals
10. ✓ Verify vectors in Qdrant

**You'll see exactly how many chunks were created!**

---

## Detailed Verification - Python Script

For deeper inspection of chunks:

### Step 1: Update Database Configuration

Edit `verify_etl_chunks.py` and update these lines:

```python
# Line 17-22
DB_CONFIG = {
    "host": "localhost",
    "database": "YOUR_DATABASE_NAME",  # <-- Update this
    "user": "YOUR_USERNAME",           # <-- Update this
    "password": "YOUR_PASSWORD"        # <-- Update this
}

# Line 14
QDRANT_COLLECTION = "YOUR_COLLECTION_NAME"  # <-- Update this
```

### Step 2: Install Required Python Packages
```bash
pip install qdrant-client psycopg2-binary
```

### Step 3: Run the Verification Script
```bash
cd /home/user/scoping-bot
python3 verify_etl_chunks.py
```

This will show you:
- All KB documents in database
- Processing job status
- All vectors in Qdrant grouped by document
- **Detailed chunk content for any document you choose**

---

## Manual Step-by-Step Test

If you prefer to test manually:

### 1. Check Backend Logs

Keep your backend terminal visible. After uploading a document, you'll see:

```
INFO: 📤 KB document uploaded: knowledge_base/test.pdf, triggering ETL scan...
INFO: 🔍 Starting ETL scan for new KB documents...
INFO: 📄 Found 5 files in knowledge_base storage
INFO: 📝 New document added: test.pdf
INFO: ✅ Vectorized test.pdf: 12 vectors created  👈 THIS SHOWS CHUNKS!
INFO: ✅ Post-upload ETL scan completed: {'scanned': 5, 'new': 1, ...}
```

### 2. Check ETL Stats API

```bash
# Get your auth token first
TOKEN="your_superuser_token_here"

# Check stats
curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/api/etl/stats | jq '.'
```

Look for:
- `total_documents` - How many KB docs exist
- `vectorized_documents` - How many are in Qdrant
- `unvectorized_documents` - How many pending

### 3. List KB Documents

```bash
curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/api/etl/kb-documents | jq '.documents[] | {file_name, is_vectorized, vector_count}'
```

The `vector_count` field shows how many chunks!

### 4. Check Processing Jobs

```bash
curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/api/etl/processing-jobs | jq '.jobs[] | {file: .document.file_name, status, chunks: .chunks_processed, vectors: .vectors_created}'
```

Shows:
- `chunks_processed` - How many chunks created
- `vectors_created` - How many vectors in Qdrant

### 5. View in Qdrant Web UI

1. Open: http://localhost:6333/dashboard
2. Click on your collection name
3. Click "Browse Points"
4. You'll see all vectors with:
   - `file_name` - Which document
   - `chunk_index` - Chunk number (0, 1, 2, ...)
   - `content` - First 1000 chars of chunk

### 6. Query Qdrant Directly

```bash
# Get collection info
curl http://localhost:6333/collections/your_collection_name | jq '.'

# Scroll through vectors
curl -X POST http://localhost:6333/collections/your_collection_name/points/scroll \
  -H "Content-Type: application/json" \
  -d '{
    "limit": 10,
    "with_payload": true,
    "with_vector": false
  }' | jq '.'
```

---

## What to Look For

### Successful Processing

✅ **Backend Logs:**
```
✅ Vectorized filename.pdf: 15 vectors created
```

✅ **ETL Stats:**
```json
{
  "vectorized_documents": 5,
  "unvectorized_documents": 0
}
```

✅ **Document Details:**
```json
{
  "file_name": "test.pdf",
  "is_vectorized": true,
  "vector_count": 15  👈 Number of chunks
}
```

✅ **Processing Job:**
```json
{
  "status": "completed",
  "chunks_processed": 15,
  "vectors_created": 15
}
```

✅ **Qdrant:**
```
Points count: 156 (increased after upload)
```

### Pending Approval (Similar Document Found)

⏸️ **Backend Logs:**
```
⏸️  Pending admin approval for filename.pdf (found 2 similar docs)
```

⏸️ **Document Details:**
```json
{
  "is_vectorized": false  👈 Not in Qdrant yet
}
```

⏸️ **Pending Approvals:**
```bash
curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/api/etl/pending-updates?status=pending
```

Shows documents waiting for your approval.

**To approve:**
```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/api/etl/approve/{pending_update_id}
```

### Processing Failed

❌ **Backend Logs:**
```
❌ Failed to process filename.pdf: {error message}
```

❌ **Processing Job:**
```json
{
  "status": "failed",
  "error_message": "Text extraction failed"
}
```

---

## Understanding Chunks

### How Documents are Chunked:

```
Original Document (2500 chars)
         ↓
    Chunking Process
   (1000 chars/chunk, 200 overlap)
         ↓
  ┌──────────────────┐
  │ Chunk 0: 0-1000  │ Vector ID: doc_uuid_0
  └──────────────────┘
         ↓
  ┌──────────────────┐
  │ Chunk 1: 800-1800│ Vector ID: doc_uuid_1
  └──────────────────┘ (overlap: 800-1000)
         ↓
  ┌──────────────────┐
  │ Chunk 2: 1600-2500│ Vector ID: doc_uuid_2
  └──────────────────┘ (overlap: 1600-1800)
```

### Viewing Chunks in Qdrant:

Each chunk appears as a separate vector with:
- **Vector ID**: `{document_id}_{chunk_index}`
- **Payload**:
  - `document_id` - Links back to KB document
  - `file_name` - Original filename
  - `chunk_index` - Position (0, 1, 2, ...)
  - `content` - Text content (first 1000 chars stored)
  - `created_at` - When it was created

---

## Common Issues

### No chunks created (vector_count = 0)

**Causes:**
1. Text extraction failed (unsupported file format)
2. Document too small (<50 chars)
3. Processing job failed

**Fix:**
Check processing jobs for error messages

### Document pending approval

**Cause:**
Document is >85% similar to existing KB document

**Fix:**
Approve via: `POST /api/etl/approve/{id}`

### Qdrant shows no points

**Causes:**
1. Qdrant not running: `docker ps | grep qdrant`
2. Wrong collection name
3. Documents pending approval

**Fix:**
Check ETL stats and pending approvals

---

## Next Steps

After verifying chunks are created:

1. **Test RAG Retrieval**: Generate a project scope and check backend logs for:
   ```
   Retrieved 5 chunks from knowledge base
   ```

2. **View Chunks in Use**: The chunks will appear in:
   - Scope generation context
   - Question generation
   - Architecture diagram creation

3. **Monitor Performance**: Check ETL stats regularly:
   ```bash
   curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/etl/stats
   ```

---

## Support

If you encounter issues:

1. Check backend logs: Look for ❌ symbols
2. Check processing jobs: `GET /api/etl/processing-jobs?status=failed`
3. Verify Qdrant is running: `curl http://localhost:6333/collections`
4. Review database: Use `verify_etl_chunks.py` script

For detailed logs, look for these emojis in backend:
- 📤 Upload detected
- 🔍 ETL scan started
- 📄 Files found
- 📝 New document
- ✅ Success
- ⏸️  Pending approval
- ❌ Error
