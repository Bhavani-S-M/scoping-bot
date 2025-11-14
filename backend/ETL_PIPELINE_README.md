# Knowledge Base ETL Pipeline

Automated ETL (Extract, Transform, Load) pipeline that monitors Azure Blob Storage for knowledge base documents, converts them to vectors, and stores in Qdrant with admin approval workflow.

## Overview

The ETL pipeline automatically:
1. Monitors `knowledge_base` folder in Azure Blob Storage
2. Extracts text from uploaded documents
3. Generates vector embeddings using Ollama
4. Checks similarity with existing KB documents
5. Requests admin approval if updates detected
6. Stores approved vectors in Qdrant

## Architecture

```
Azure Blob Storage (knowledge_base/)
         ↓
    ETL Scanner
   (every 30 min)
         ↓
   Text Extraction
         ↓
    Chunking (1000 chars, 200 overlap)
         ↓
   Ollama Embeddings
         ↓
  Similarity Check (>85% threshold)
         ↓
   ┌─────────────────┐
   │  Similar docs?  │
   └────┬──────┬─────┘
       Yes    No
        ↓      ↓
   Pending  Direct
   Approval  to Qdrant
        ↓
   Admin Review
        ↓
   Approve/Reject
        ↓
    Qdrant Storage
```

## Database Models

### KnowledgeBaseDocument
Tracks all KB documents and their vector status
- `id` - Unique document ID
- `file_name` - Original filename
- `blob_path` - Path in blob storage
- `file_hash` - SHA256 hash for change detection
- `is_vectorized` - Whether document is in Qdrant
- `vector_count` - Number of vectors created
- `qdrant_point_ids` - IDs of vectors in Qdrant

### DocumentProcessingJob
Tracks ETL processing jobs
- `status` - pending, processing, completed, failed
- `chunks_processed` - Number of chunks created
- `vectors_created` - Number of vectors generated
- `error_message` - Failure reason if failed

### PendingKBUpdate
Tracks pending admin approvals
- `update_type` - new, update, duplicate
- `similarity_score` - Highest similarity with existing docs
- `related_documents` - JSON of similar documents
- `status` - pending, approved, rejected
- `reviewed_by` - Admin user who reviewed
- `admin_comment` - Admin's review comment

## API Endpoints

All endpoints require superuser authentication.

### Trigger Manual Scan
```bash
POST /api/etl/scan

Response:
{
  "status": "success",
  "message": "ETL scan completed",
  "stats": {
    "scanned": 10,
    "new": 2,
    "updated": 1,
    "failed": 0,
    "pending_approval": 1
  }
}
```

### List Pending Approvals
```bash
GET /api/etl/pending-updates?status=pending&limit=50&offset=0

Response:
{
  "status": "success",
  "count": 2,
  "pending_updates": [
    {
      "id": "uuid",
      "document": {
        "id": "uuid",
        "file_name": "updated_policy.pdf",
        "blob_path": "knowledge_base/policies/updated_policy.pdf",
        "file_size": 245678,
        "uploaded_at": "2025-01-15T10:30:00Z"
      },
      "update_type": "update",
      "similarity_score": 0.92,
      "reason": "High similarity (92%) - possible update to existing content",
      "related_documents": [
        {
          "document_id": "uuid",
          "file_name": "old_policy.pdf",
          "similarity_score": 0.92,
          "blob_path": "knowledge_base/policies/old_policy.pdf"
        }
      ],
      "status": "pending",
      "created_at": "2025-01-15T10:31:00Z"
    }
  ]
}
```

### Approve Pending Update
```bash
POST /api/etl/approve/{pending_update_id}
Content-Type: application/json

{
  "admin_comment": "Approved - this is an updated version"
}

Response:
{
  "status": "success",
  "message": "KB update approved and processed",
  "document_id": "uuid",
  "file_name": "updated_policy.pdf",
  "vectors_created": 15
}
```

### Reject Pending Update
```bash
POST /api/etl/reject/{pending_update_id}
Content-Type: application/json

{
  "admin_comment": "Rejected - duplicate content"
}

Response:
{
  "status": "success",
  "message": "KB update rejected",
  "pending_update_id": "uuid"
}
```

### View Processing Jobs
```bash
GET /api/etl/processing-jobs?status=completed&limit=50

Response:
{
  "status": "success",
  "count": 25,
  "jobs": [
    {
      "id": "uuid",
      "document": {
        "id": "uuid",
        "file_name": "report.pdf"
      },
      "status": "completed",
      "chunks_processed": 12,
      "vectors_created": 12,
      "error_message": null,
      "created_at": "2025-01-15T10:00:00Z",
      "started_at": "2025-01-15T10:00:05Z",
      "completed_at": "2025-01-15T10:01:30Z"
    }
  ]
}
```

### List KB Documents
```bash
GET /api/etl/kb-documents?is_vectorized=true&limit=50

Response:
{
  "status": "success",
  "count": 42,
  "documents": [
    {
      "id": "uuid",
      "file_name": "technical_spec.pdf",
      "blob_path": "knowledge_base/specs/technical_spec.pdf",
      "file_size": 1245678,
      "file_hash": "sha256...",
      "is_vectorized": true,
      "vector_count": 28,
      "uploaded_at": "2025-01-10T08:00:00Z",
      "vectorized_at": "2025-01-10T08:02:15Z",
      "last_checked": "2025-01-15T09:00:00Z"
    }
  ]
}
```

### Get ETL Statistics
```bash
GET /api/etl/stats

Response:
{
  "status": "success",
  "stats": {
    "total_documents": 50,
    "vectorized_documents": 42,
    "unvectorized_documents": 8,
    "pending_approvals": 3,
    "processing_jobs": {
      "pending": 2,
      "processing": 1,
      "completed": 45,
      "failed": 2
    }
  }
}
```

## Usage

### Automatic Processing

The ETL pipeline runs automatically:
1. **On Upload**: Triggers immediately when KB documents uploaded
2. **Scheduled**: Runs every 30 minutes to check for new/changed documents

### Manual Trigger

Superusers can manually trigger ETL scans:
```python
import requests

response = requests.post(
    "http://localhost:8000/api/etl/scan",
    headers={"Authorization": "Bearer <superuser_token>"}
)
print(response.json())
```

### Admin Approval Workflow

1. **Check Pending Approvals**:
   ```bash
   curl -H "Authorization: Bearer <token>" \
        http://localhost:8000/api/etl/pending-updates?status=pending
   ```

2. **Review Similar Documents**:
   - Check `related_documents` field
   - Review `similarity_score` and `reason`
   - Download original files if needed

3. **Approve or Reject**:
   ```bash
   # Approve
   curl -X POST \
        -H "Authorization: Bearer <token>" \
        -H "Content-Type: application/json" \
        -d '{"admin_comment": "Approved"}' \
        http://localhost:8000/api/etl/approve/{id}

   # Reject
   curl -X POST \
        -H "Authorization: Bearer <token>" \
        -H "Content-Type: application/json" \
        -d '{"admin_comment": "Duplicate"}' \
        http://localhost:8000/api/etl/reject/{id}
   ```

## Configuration

### Similarity Threshold
Adjust in `backend/app/services/etl_pipeline.py`:
```python
self.similarity_threshold = 0.85  # 85% similarity
```

### Chunk Size
Adjust in `backend/app/services/etl_pipeline.py`:
```python
self.chunk_size = 1000  # Characters per chunk
self.overlap = 200      # Overlap between chunks
```

### Scan Frequency
Adjust in `backend/app/main.py`:
```python
await asyncio.sleep(30 * 60)  # 30 minutes
```

## Troubleshooting

### Documents Not Processing

1. Check ETL stats:
   ```bash
   curl -H "Authorization: Bearer <token>" \
        http://localhost:8000/api/etl/stats
   ```

2. View failed jobs:
   ```bash
   curl -H "Authorization: Bearer <token>" \
        http://localhost:8000/api/etl/processing-jobs?status=failed
   ```

3. Check backend logs for errors:
   ```
   ❌ Failed to process {filename}: {error}
   ```

### Vectors Not in Qdrant

1. Check if document is vectorized:
   ```bash
   curl -H "Authorization: Bearer <token>" \
        http://localhost:8000/api/etl/kb-documents?is_vectorized=false
   ```

2. Check for pending approvals:
   ```bash
   curl -H "Authorization: Bearer <token>" \
        http://localhost:8000/api/etl/pending-updates?status=pending
   ```

3. Manually trigger scan:
   ```bash
   curl -X POST -H "Authorization: Bearer <token>" \
        http://localhost:8000/api/etl/scan
   ```

### High Similarity False Positives

If documents are incorrectly flagged as similar:
1. Adjust `similarity_threshold` in `etl_pipeline.py`
2. Lower threshold = fewer false positives, more auto-processing
3. Higher threshold = more false positives, more manual review

## Database Migration

After deploying, run Alembic migration to create new tables:

```bash
cd backend
alembic revision --autogenerate -m "Add ETL pipeline tables"
alembic upgrade head
```

Or the tables will be auto-created on next server startup.

## Monitoring

### Log Messages

- `🔍 Starting ETL scan...` - Scan initiated
- `📄 Found N files in knowledge_base storage` - Files discovered
- `📝 New document added: {filename}` - New document tracked
- `🔄 Document changed: {filename}` - Document updated
- `⏸️  Pending admin approval for {filename}` - Awaiting review
- `✅ Document vectorized: {filename}` - Successfully processed
- `❌ Failed to process {filename}: {error}` - Processing failed

### Health Checks

Monitor ETL pipeline health:
```python
stats = requests.get("/api/etl/stats").json()

if stats["stats"]["pending_approvals"] > 10:
    alert("Many pending approvals!")

if stats["stats"]["processing_jobs"]["failed"] > 5:
    alert("Multiple processing failures!")
```

## Security

- All ETL endpoints require superuser authentication
- Only superusers can approve/reject updates
- File hashes prevent tampering detection
- Admin comments tracked for audit trail

## Performance

- Background processing doesn't block uploads
- Chunking handles large documents efficiently
- Vector generation batched for speed
- Qdrant upsert handles duplicates gracefully
- Similarity search cached in Qdrant

## Future Enhancements

- [ ] Email notifications for pending approvals
- [ ] Webhook support for external integrations
- [ ] Batch approval UI
- [ ] Auto-approval rules based on patterns
- [ ] Version control for KB documents
- [ ] A/B testing for similarity thresholds
