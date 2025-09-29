# app/utils/azure_blob.py
from typing import List, Dict, Union
from azure.storage.blob import (
    BlobServiceClient,
    ContainerClient,
    generate_container_sas,
    ContainerSasPermissions,
)
from azure.core.exceptions import ResourceExistsError
from app.config import config
from datetime import datetime, timedelta

# Blob Storage Configuration
AZURE_STORAGE_ACCOUNT = config.AZURE_STORAGE_ACCOUNT
AZURE_STORAGE_KEY = config.AZURE_STORAGE_KEY
AZURE_STORAGE_CONTAINER = config.AZURE_STORAGE_CONTAINER or "scopingbot"

if not AZURE_STORAGE_ACCOUNT or not AZURE_STORAGE_KEY:
    raise RuntimeError("Azure Storage credentials missing in config.py/.env")

_blob_service = BlobServiceClient(
    account_url=f"https://{AZURE_STORAGE_ACCOUNT}.blob.core.windows.net",
    credential=AZURE_STORAGE_KEY,
)

container: ContainerClient = _blob_service.get_container_client(AZURE_STORAGE_CONTAINER)

try:
    container.create_container()
except ResourceExistsError:
    pass


def get_container() -> ContainerClient:
    return container


# Upload
def upload_bytes(data: Union[bytes, bytearray], blob_name: str, base: str = "") -> str:
    path = _normalize_path(blob_name, base)
    container.get_blob_client(path).upload_blob(data, overwrite=True)
    return path


def upload_file(path: str, blob_name: str, base: str = "") -> str:
    with open(path, "rb") as f:
        return upload_bytes(f.read(), blob_name, base=base)


# Download
def download_bytes(blob_name: str, base: str = "") -> bytes:
    path = _normalize_path(blob_name, base)
    return container.get_blob_client(path).download_blob().readall()


def download_text(blob_name: str, base: str = "", encoding: str = "utf-8") -> str:
    return download_bytes(blob_name, base).decode(encoding, errors="ignore")


# Listing & Explorer
def list_bases() -> List[Dict]:
    return [
        {"name": "projects", "path": "projects", "is_folder": True},
        {"name": "knowledge_base", "path": "knowledge_base", "is_folder": True},
    ]


def build_tree(base: str, prefix: str = "") -> List[Dict]:
    path = _normalize_path(prefix, base)
    if path and not path.endswith("/"):
        path += "/"

    items: List[Dict] = []
    seen_folders = set()

    for blob in container.list_blobs(name_starts_with=path):
        relative = blob.name[len(path):]
        if not relative:
            continue

        parts = relative.split("/", 1)

        if len(parts) == 1:
            items.append({
                "name": parts[0],
                "path": blob.name,
                "is_folder": False,
                "size": blob.size,
            })
        else:
            folder_name = parts[0]
            if folder_name not in seen_folders:
                seen_folders.add(folder_name)
                children = build_tree(base, (prefix + "/" + folder_name).strip("/"))
                items.append({
                    "name": folder_name,
                    "path": f"{path}{folder_name}",
                    "is_folder": True,
                    "children": children,
                })

    return items


def explorer(base: str) -> Dict:
    return {
        "base": base,
        "children": build_tree(base)
    }


# Delete
def delete_blob(blob_name: str, base: str = "") -> bool:
    path = _normalize_path(blob_name, base)
    container.delete_blob(path)
    return True


def delete_folder(prefix: str, base: str = "") -> List[str]:
    path = _normalize_path(prefix, base)
    if path and not path.endswith("/"):
        path += "/"

    deleted: List[str] = []
    for blob in container.list_blobs(name_starts_with=path):
        container.delete_blob(blob.name)
        deleted.append(blob.name)
    return deleted


# Exists & URL
def blob_exists(blob_name: str, base: str = "") -> bool:
    """Check if a blob exists."""
    path = _normalize_path(blob_name, base)
    return container.get_blob_client(path).exists()


def get_blob_url(blob_name: str, base: str = "") -> str:
    """Return the full URL of a blob (direct access)."""
    path = _normalize_path(blob_name, base)
    return (
        f"https://{AZURE_STORAGE_ACCOUNT}.blob.core.windows.net/"
        f"{AZURE_STORAGE_CONTAINER}/{path}"
    )


def generate_sas_url(expiry_hours: int = 1) -> str:
    """Generate a container-scoped SAS URL (read/write/list/delete)."""
    sas_token = generate_container_sas(
        account_name=AZURE_STORAGE_ACCOUNT,
        container_name=AZURE_STORAGE_CONTAINER,
        account_key=AZURE_STORAGE_KEY,
        permission=ContainerSasPermissions(
            read=True, list=True, delete=True, write=True, add=True, create=True
        ),
        expiry=datetime.utcnow() + timedelta(hours=expiry_hours),
    )
    return f"https://{AZURE_STORAGE_ACCOUNT}.blob.core.windows.net/{AZURE_STORAGE_CONTAINER}?{sas_token}"


# Helpers
def _normalize_path(blob_name: str, base: str) -> str:
    """Ensure blob paths don't duplicate base (fix 404 on delete)."""
    blob_name = blob_name.strip("/")
    base = base.strip("/")

    if base and blob_name.startswith(base + "/"):
        blob_name = blob_name[len(base) + 1:]

    return f"{base}/{blob_name}" if base else blob_name
