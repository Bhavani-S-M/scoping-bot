from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
from typing import List, Literal
from app.utils import azure_blob
from app.auth.router import fastapi_users
from app.config.database import get_async_session
from sqlalchemy.ext.asyncio import AsyncSession
import io, mimetypes, logging

logger = logging.getLogger(__name__)

get_current_superuser = fastapi_users.current_user(active=True, superuser=True)

router = APIRouter(prefix="/api/blobs", tags=["Azure Blobs"])

VALID_BASES = ("projects", "knowledge_base")


def _validate_base(base: str) -> str:
    if base not in VALID_BASES:
        raise HTTPException(400, f"Invalid base '{base}'. Must be one of {VALID_BASES}")
    return base


async def _trigger_etl_scan(db: AsyncSession):
    """Background task to trigger ETL scan after KB document upload."""
    try:
        from app.services.etl_pipeline import get_etl_pipeline
        etl = get_etl_pipeline()
        stats = await etl.scan_and_process_new_documents(db)
        logger.info(f"✅ Post-upload ETL scan completed: {stats}")
    except Exception as e:
        logger.error(f"❌ Post-upload ETL scan failed: {e}")


# Uploads
@router.post("/upload/file")
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    folder: str = Form(""),
    base: Literal["projects", "knowledge_base"] = Form("knowledge_base"),
    db: AsyncSession = Depends(get_async_session)
):
    try:
        base = _validate_base(base)
        folder = folder.strip().rstrip("/")
        safe_name = file.filename.replace(" ", "_")
        blob_name = f"{folder}/{safe_name}" if folder else safe_name
        blob_name = blob_name.strip("/")

        data = await file.read()
        path = await azure_blob.upload_bytes(data, blob_name, base)

        # If uploading to knowledge_base, trigger ETL scan in background
        if base == "knowledge_base":
            logger.info(f"📤 KB document uploaded: {path}, triggering ETL scan...")
            background_tasks.add_task(_trigger_etl_scan, db)

        return {"status": "success", "blob": path}
    except Exception as e:
        raise HTTPException(500, f"Upload failed: {e}")


@router.post("/upload/folder")
async def upload_folder(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    folder: str = Form(""),
    base: Literal["projects", "knowledge_base"] = Form("knowledge_base"),
    db: AsyncSession = Depends(get_async_session)
):
    try:
        base = _validate_base(base)
        folder = folder.strip().rstrip("/")
        uploaded = []

        for file in files:
            relative_path = file.filename.replace(" ", "_")
            blob_name = f"{folder}/{relative_path}" if folder else relative_path
            blob_name = blob_name.strip("/")

            data = await file.read()
            path = await azure_blob.upload_bytes(data, blob_name, base)
            uploaded.append(path)

        # If uploading to knowledge_base, trigger ETL scan in background
        if base == "knowledge_base":
            logger.info(f"📤 {len(uploaded)} KB documents uploaded, triggering ETL scan...")
            background_tasks.add_task(_trigger_etl_scan, db)

        return {"status": "success", "files": uploaded}
    except Exception as e:
        raise HTTPException(500, f"Upload failed: {e}")

# Explorer-Style Listing
@router.get("/explorer/{base}")
async def explorer_tree(base: Literal["projects", "knowledge_base"]):
    try:
        base = _validate_base(base)
        tree = await azure_blob.explorer(base)
        return {
            "status": "success",
            "base": base,
            "children": tree["children"],
        }
    except Exception as e:
        raise HTTPException(500, f"Explorer listing failed: {e}")


# Download
@router.get("/download/{blob_name:path}")
async def download_blob(blob_name: str, base: Literal["projects", "knowledge_base"] = Query(...)):
    try:
        base = _validate_base(base)
        blob_bytes = await azure_blob.download_bytes(blob_name, base)
        file_like = io.BytesIO(blob_bytes)
        filename = blob_name.split("/")[-1]
        content_type, _ = mimetypes.guess_type(filename)
        content_type = content_type or "application/octet-stream"

        return StreamingResponse(
            file_like,
            media_type=content_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as e:
        raise HTTPException(404, f"Blob not found: {e}")

# Preview
@router.get("/preview/{blob_name:path}")
async def preview_blob(blob_name: str, base: Literal["projects", "knowledge_base"] = Query(...)):
    try:
        base = _validate_base(base)
        blob_bytes = await azure_blob.download_bytes(blob_name, base)
        file_like = io.BytesIO(blob_bytes)
        filename = blob_name.split("/")[-1]
        content_type, _ = mimetypes.guess_type(filename)
        content_type = content_type or "application/octet-stream"

        return StreamingResponse(
            file_like,
            media_type=content_type,
            headers={"Content-Disposition": f'inline; filename="{filename}"'},
        )
    except Exception as e:
        raise HTTPException(404, f"Blob not found: {e}")


# Delete
@router.delete("/delete/file/{blob_name:path}")
async def delete_file(blob_name: str, base: Literal["projects", "knowledge_base"] = Query(...)):
    try:
        base = _validate_base(base)
        await azure_blob.delete_blob(blob_name, base)
        return {"status": "success", "deleted": f"{base}/{blob_name}"}
    except Exception as e:
        raise HTTPException(404, f"File not found: {e}")


@router.delete("/delete/folder/{folder_name:path}")
async def delete_folder(folder_name: str, base: Literal["projects", "knowledge_base"] = Query(...)):
    try:
        base = _validate_base(base)
        deleted = await azure_blob.delete_folder(folder_name, base)
        if not deleted:
            raise HTTPException(404, "Folder is empty or not found")
        return {"status": "success", "deleted": deleted}
    except Exception as e:
        raise HTTPException(404, f"Folder not found: {e}")


# SAS Token
@router.get("/sas-token")
async def get_sas_token(hours: int = 1):
    try:
        url = azure_blob.generate_sas_url(hours)
        return {"status": "success", "sas_url": url}
    except Exception as e:
        raise HTTPException(500, f"SAS generation failed: {e}")
