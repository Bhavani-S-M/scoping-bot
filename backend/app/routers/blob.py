from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query
from fastapi.responses import StreamingResponse
from typing import List, Literal
from app.utils import azure_blob
from app.auth.router import fastapi_users
import io, mimetypes

get_current_superuser = fastapi_users.current_user(active=True, superuser=True)

router = APIRouter(prefix="/api/blobs", tags=["Azure Blobs"])

VALID_BASES = ("projects", "knowledge_base")


def _validate_base(base: str) -> str:
    if base not in VALID_BASES:
        raise HTTPException(400, f"Invalid base '{base}'. Must be one of {VALID_BASES}")
    return base


# Uploads
@router.post("/upload/file")
async def upload_file(
    file: UploadFile = File(...),
    folder: str = Form(""),
    base: Literal["projects", "knowledge_base"] = Form("knowledge_base"),
):
    try:
        base = _validate_base(base)
        folder = folder.strip().rstrip("/")
        safe_name = file.filename.replace(" ", "_")
        blob_name = f"{folder}/{safe_name}" if folder else safe_name
        blob_name = blob_name.strip("/")

        data = await file.read()
        path = await azure_blob.upload_bytes(data, blob_name, base)

        return {"status": "success", "blob": path}
    except Exception as e:
        raise HTTPException(500, f"Upload failed: {e}")


@router.post("/upload/folder")
async def upload_folder(
    files: List[UploadFile] = File(...),
    folder: str = Form(""),
    base: Literal["projects", "knowledge_base"] = Form("knowledge_base"),
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
