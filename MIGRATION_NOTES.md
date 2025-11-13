# Migration Notes - Bug Fixes and Enhancements

## Issues Fixed

This update fixes nine critical issues and adds one new feature in the scoping-bot application:

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

### 4. Import Shadowing Error

**Problem:**
- Function `_build_scope_prompt()` was importing `datetime` module
- This shadowed the `datetime` class imported at file level
- Caused `AttributeError: module 'datetime' has no attribute 'today'`

**Fix:**
- Removed redundant `datetime` import from line 274

**Files Changed:**
- `backend/app/utils/scope_engine.py:274`

### 5. Empty Scope Regeneration

**Problem:**
- After user modifications, scope preview showed empty `activities` and `resourcing_plan`
- LLM (deepseek-r1) was inconsistently generating complete responses
- Only returned `overview` section without activities

**Fix:**
- Added safety check to preserve original activities if LLM returns empty array
- Enhanced logging to track LLM response structure
- Prevents data loss during regeneration

**Files Changed:**
- `backend/app/utils/scope_engine.py:1478-1530`

### 6. Role Management Not Working

**Problem:**
- Instructions like "remove Business Analyst" or "add Backend Developer" were not reflected
- LLM was not properly following role addition/removal instructions
- Roles remained in activities and resourcing_plan after removal requests

**Fix:**
- Added comprehensive "Role Management Rules" section to regeneration prompt
- Implemented post-processing fallback that automatically removes roles if LLM fails
- Enhanced validation and logging for role operations
- Lowered temperature from 0.5 to 0.2 for more consistent instruction-following
- Improved regex pattern to handle multi-word role names

**Features:**
- Automatic role removal with intelligent activity reassignment
- Detailed logging of role changes
- Validation that removal/addition instructions were followed
- Works even if LLM completely ignores instructions

**Files Changed:**
- `backend/app/utils/scope_engine.py:1433-1580`

### 7. PDF Export Error - Image Too Large

**Problem:**
- Architecture diagram images were too large for PDF page
- Only width constraint was applied, not height
- Large/tall images caused `LayoutError: Flowable too large on page`
- Error: Image 780 x 1248 points exceeds frame 857 x 1122 points

**Fix:**
- Added max_height constraint (1000 points) in addition to max_width (780 points)
- Calculate both width_scale and height_scale
- Use minimum scale factor to fit within BOTH dimensions
- Maintains aspect ratio while preventing page overflow
- Updated table column widths to match scaled image width

**Files Changed:**
- `backend/app/utils/export.py:332-353`

### 8. "Add 1 More" Replacing Entire Scope

**Problem:**
- User instruction "add 1 more Backend Developer" was removing ALL activities
- LLM was replacing entire scope instead of incrementally adding
- All existing activities and roles were lost
- "Add" was interpreted as "replace" instead of "increase"

**Fix:**
- Enhanced prompt with **CRITICAL** markers for incremental changes
- Explicit instructions: "Keep ALL existing activities and roles"
- Detailed examples of what "add 1 more" means (increase allocation, not replace)
- Added activity count validation to detect unexpected losses
- Automatic fallback: if >30% of activities lost without remove/delete, restore original
- Clear distinction: ADD = increase, REMOVE = decrease

**Features:**
- Real-time validation of activity count changes
- Auto-restore if LLM accidentally deletes activities
- Comprehensive logging to track what LLM is doing
- Prevents data loss from ambiguous instructions

**Files Changed:**
- `backend/app/utils/scope_engine.py:1433-1571`

### 9. Missing Discount Feature (NEW FEATURE)

**Problem:**
- Users requested percentage discounts (5%, 10%, etc.)
- No way to apply discounts and recalculate costs

**Fix:**
- Added discount parsing from user instructions
- Supports multiple formats: "5% discount", "apply 10%", "give 15% discount"
- Discount applied to all costs in resourcing_plan
- Shows discount percentage in overview
- Shows total cost after discount
- Preserves activities and efforts - only adjusts final costs

**Features:**
- Pattern matching for discount requests
- Automatic cost recalculation with discount multiplier
- Discount shown in overview: "Discount: 10%"
- Detailed logging of cost adjustments per role
- Maintains discount_percentage in scope for reference

**Example Usage:**
```
User: "apply 10% discount"
Result:
- All role costs reduced by 10%
- Overview shows: "Discount: 10%"
- Overview shows: "Total Cost (After Discount): $95,400"
- Activities and efforts unchanged
```

**Files Changed:**
- `backend/app/utils/scope_engine.py:1133-1144, 1166-1177, 1626-1651`

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
6. Test scope regeneration with modifications:
   - Try "remove [role name]" - verify role is removed from activities and resourcing_plan
   - Try "add 1 more [role name]" - verify role is added to more activities, existing ones preserved
   - Try "apply 10% discount" - verify costs reduced by 10%, discount shown in overview
   - Check application logs for detailed role tracking and discount information

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
