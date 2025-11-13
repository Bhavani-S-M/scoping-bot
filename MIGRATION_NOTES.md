# Migration Notes - Embedding Dimension Fix

## Issues Fixed

This update fixes three critical issues in the scoping-bot application:

### 1. Embedding Dimension Mismatch (CRITICAL)

**Problem:**
- The `qwen3-embedding` model produces 4096-dimensional vectors
- The configuration had `VECTOR_DIM=1536` (default)
- Qdrant was rejecting vectors with error: "expected dim: 1024, got 4096"

**Fix:**
- Updated `backend/app/config/config.py` to set `VECTOR_DIM=4096`
- Added comment explaining the dimension size

**Files Changed:**
- `backend/app/config/config.py:50`

### 2. Datetime Comparison Error

**Problem:**
- Mixing timezone-aware and timezone-naive datetime objects
- Error: "can't compare offset-naive and offset-aware datetimes"
- Occurred in `generate_project_scope()` function

**Fix:**
- Modified `clean_scope()` function to use timezone-naive datetime
- Added `tzinfo=None` parameter when creating the `today` variable

**Files Changed:**
- `backend/app/utils/scope_engine.py:979`

### 3. Datetime Syntax Error

**Problem:**
- Incorrect usage: `datetime.date.today()` (should be `datetime.today().date()`)

**Fix:**
- Corrected syntax in `_build_scope_prompt()` function

**Files Changed:**
- `backend/app/utils/scope_engine.py:322`

## Required Actions

### ⚠️ IMPORTANT: Recreate Qdrant Collection

Since the vector dimensions have changed from 1536/1024 to 4096, you **MUST** recreate the Qdrant collection:

#### Option 1: Using the Recreation Script (Recommended)

```bash
cd backend
python recreate_qdrant_collection.py
```

The script will:
1. Delete the existing `knowledge_chunks` collection
2. Create a new collection with 4096 dimensions
3. Preserve your configuration settings

#### Option 2: Manual Recreation

```bash
# Connect to Qdrant and delete the old collection
# Then restart your application - it will auto-create with new dimensions
```

#### Option 3: Using Qdrant UI/API

1. Access Qdrant at `http://localhost:6333/dashboard`
2. Delete the `knowledge_chunks` collection
3. Restart the application

### 📤 Re-upload Knowledge Base

After recreating the collection, you need to:
1. Re-upload all knowledge base documents through the application
2. The documents will be re-embedded using the correct 4096 dimensions

## Environment Variables (Optional)

If you want to use a different embedding model or dimensions in the future:

```bash
# In your .env file
VECTOR_DIM=4096  # Set to match your embedding model's output dimension
OLLAMA_EMBED_MODEL=qwen3-embedding  # Your embedding model
```

## Testing

After applying these changes and recreating the collection:

1. Start your application
2. Upload a knowledge base document
3. Generate a project scope
4. Verify no dimension mismatch warnings appear
5. Verify no datetime comparison errors occur

## Rollback (if needed)

If you need to rollback:

1. Revert the code changes:
   ```bash
   git revert <commit-hash>
   ```

2. Update `VECTOR_DIM` back to your previous value

3. Recreate the Qdrant collection with the old dimensions

## Questions?

If you encounter any issues:
1. Check the Qdrant logs
2. Verify the Ollama embedding model is running
3. Ensure `VECTOR_DIM` matches your embedding model's output
