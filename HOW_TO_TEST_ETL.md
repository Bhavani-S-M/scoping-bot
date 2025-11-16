# How to Test ETL Pipeline and See Document Chunking

This guide shows you exactly how to verify that documents are being chunked and stored in Qdrant.

## Understanding the Problem

Currently, you have **0 documents** in your knowledge base. This is why the ETL stats show everything as empty:
- Total documents: 0
- Vectorized documents: 0
- Chunks created: 0

**You need to upload a test document to trigger the ETL pipeline.**

---

## Quick Test (Recommended)

### Step 1: Make sure backend is running

```bash
cd /home/user/scoping-bot/backend
python -m uvicorn app.main:app --reload
```

Wait for:
```
ETL background scheduler started (runs every 30 minutes).
INFO:     Application startup complete.
```

### Step 2: Run the upload test script (in a new terminal)

```bash
cd /home/user/scoping-bot
python3 upload_test_document.py
```

This script will:
1. ✅ Check if backend is running
2. 🔑 Ask for your auth token
3. 📤 Upload test_kb_document.txt to knowledge_base
4. ⏱️  Wait 5 seconds for processing
5. 📊 Show you the results with chunk counts!

### Step 3: Watch your backend logs

In your backend terminal, you should see:

```
INFO: 📤 KB document uploaded: knowledge_base/test/test_kb_document.txt, triggering ETL scan...
INFO: 🔍 Starting ETL scan for new KB documents...
INFO: 📄 Found 1 files in knowledge_base storage
INFO: 📝 New document added: test_kb_document.txt
INFO: ✅ Vectorized test_kb_document.txt: 3 vectors created  <-- THIS SHOWS CHUNKS!
INFO: ✅ Post-upload ETL scan completed: {'scanned': 1, 'new': 1, 'updated': 0, 'failed': 0, 'pending_approval': 0}
```

The number "3 vectors created" means your document was split into **3 chunks**!

---

## What You'll See

### Success Output from upload_test_document.py:

```
✅ Upload successful!
   Blob path: knowledge_base/test/test_kb_document.txt

🔄 ETL pipeline is processing the document...

📊 ETL Statistics:
   Total documents: 1
   Vectorized: 1
   Pending approval: 0

📄 Recent Documents:

   ✅ test_kb_document.txt
      Status: Vectorized ✅
      Chunks created: 3
      Size: 1234 bytes

============================================================
🎉 SUCCESS! Document was chunked!
============================================================

Your document was split into 3 chunks
and stored in Qdrant as vectors.

Each chunk:
  • Contains ~1000 characters
  • Has 200 characters overlap with neighbors
  • Is stored as a vector embedding
  • Can be retrieved for RAG
```

---

## Understanding the Chunking Process

Your test document (1234 bytes) was processed like this:

```
Original Document (1234 characters)
         ↓
    Text Extraction
         ↓
    Chunking Process
   (1000 chars/chunk, 200 overlap)
         ↓
┌──────────────────────┐
│ Chunk 0: chars 0-1000│  → Vector in Qdrant
└──────────────────────┘
         ↓
┌──────────────────────┐
│ Chunk 1: chars 800-1800│ → Vector in Qdrant
└──────────────────────┘  (overlap: 800-1000)
         ↓
┌──────────────────────┐
│ Chunk 2: chars 1600-2000│ → Vector in Qdrant
└──────────────────────┘  (overlap: 1600-1800)
```

Each chunk becomes a **separate vector** in Qdrant with:
- Vector ID: `{document_id}_0`, `{document_id}_1`, etc.
- Payload: file_name, chunk_index, content, document_id

---

## Viewing Chunks in Qdrant Dashboard

1. Open: http://localhost:6333/dashboard
2. Click on **project_kb** collection
3. Click **Browse Points**
4. You'll see your chunks!

Each point shows:
```json
{
  "id": "uuid_0",
  "payload": {
    "file_name": "test_kb_document.txt",
    "chunk_index": 0,
    "content": "ETL Pipeline Test Document\n\nThis is a test...",
    "document_id": "uuid",
    "created_at": "2025-11-16T..."
  }
}
```

---

## Check Current Status Anytime

```bash
python3 simple_etl_status.py
```

This shows:
- Total documents in KB
- How many are vectorized
- Chunk counts per document
- Processing job status
- Any pending approvals

---

## What If Document is Pending Approval?

If your document is similar (>85%) to an existing KB document, you'll see:

```
⏸️  Document may be pending approval
   (This happens if it's similar to existing docs)
```

**Backend logs will show:**
```
INFO: ⏸️  Pending admin approval for test_kb_document.txt (found 2 similar docs)
```

**To approve:**

1. Check pending approvals:
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:8000/api/etl/pending-updates?status=pending | jq '.'
```

2. Approve the update:
```bash
curl -X POST -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:8000/api/etl/approve/{pending_update_id}
```

---

## Troubleshooting

### No chunks created (vector_count = 0)

**Causes:**
- Text extraction failed (check processing jobs for errors)
- Document too small (<50 chars)
- Processing job failed

**Fix:**
```bash
python3 simple_etl_status.py
# Look for error messages in processing jobs
```

### Still showing 0 documents

**Possible causes:**
1. Backend not running
2. You're not a superuser (need superuser to upload to KB)
3. File uploaded to wrong folder (projects vs knowledge_base)

**Check your user role in PostgreSQL:**
```sql
SELECT email, is_superuser FROM users;
```

**Make yourself superuser:**
```sql
UPDATE users SET is_superuser = true WHERE email = 'your@email.com';
```

### ETL not processing

**Check backend logs for errors:**
- Look for ❌ symbols
- Check for Python exceptions

**Manually trigger ETL scan:**
```bash
curl -X POST -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:8000/api/etl/scan
```

---

## Next Steps After Seeing Chunks

Once you've verified chunking works:

1. **Upload Real KB Documents**
   - PDFs, DOCX, PPTX, etc.
   - They'll be automatically processed

2. **Test RAG Retrieval**
   - Generate a project scope
   - Check backend logs for: "Retrieved X chunks from knowledge base"

3. **Monitor ETL Health**
   ```bash
   python3 simple_etl_status.py
   ```

4. **View Chunks in Action**
   - The chunks appear in scope generation
   - They provide context to the LLM
   - Better scopes with relevant KB info

---

## Summary of Test Scripts

| Script | Purpose | When to Use |
|--------|---------|-------------|
| `upload_test_document.py` | Upload test doc and see chunks | First time testing |
| `simple_etl_status.py` | Check current state | Anytime |
| `direct_etl_test.py` | Direct DB/Qdrant check | Deep debugging |
| `quick_etl_check.sh` | Quick API status | Quick verification |
| `test_etl_pipeline.sh` | Full end-to-end test | Complete workflow test |

---

## Expected Timeline

1. **Upload document**: Instant
2. **ETL scan triggered**: Within 1 second (background task)
3. **Text extraction**: 1-3 seconds
4. **Chunking**: <1 second
5. **Embedding generation**: 2-5 seconds (depends on Ollama)
6. **Qdrant storage**: <1 second

**Total: 5-10 seconds** from upload to vectors in Qdrant

---

## Support

If something isn't working:

1. **Check backend logs** - Look for error messages
2. **Run status check** - `python3 simple_etl_status.py`
3. **Verify services**:
   - Backend: http://localhost:8000/health
   - Qdrant: http://localhost:6333/dashboard
   - Database: Check PostgreSQL is running
4. **Check permissions** - Make sure you're a superuser
