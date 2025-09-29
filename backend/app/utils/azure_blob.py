# app/utils/azure_blob.py
from typing import List, Dict, Union
from azure.storage.blob.aio import BlobServiceClient, ContainerClient
from azure.storage.blob import generate_container_sas, ContainerSasPermissions
from azure.core.exceptions import ResourceExistsError
from app.config import config
from datetime import datetime, timedelta

# Config
AZURE_STORAGE_ACCOUNT = config.AZURE_STORAGE_ACCOUNT
AZURE_STORAGE_KEY = config.AZURE_STORAGE_KEY
AZURE_STORAGE_CONTAINER = config.AZURE_STORAGE_CONTAINER or "scopingbot"

if not AZURE_STORAGE_ACCOUNT or not AZURE_STORAGE_KEY:
    raise RuntimeError("Azure Storage credentials missing in config.py/.env")

_blob_service: BlobServiceClient = BlobServiceClient(
    account_url=f"https://{AZURE_STORAGE_ACCOUNT}.blob.core.windows.net",
    credential=AZURE_STORAGE_KEY,
)

container: ContainerClient = _blob_service.get_container_client(AZURE_STORAGE_CONTAINER)

# Ensure container exists
async def init_container():
    try:
        await container.create_container()
    except ResourceExistsError:
        pass


# Helpers
def _normalize_path(blob_name: str, base: str) -> str:
    blob_name = blob_name.strip("/")
    base = base.strip("/")
    if base and blob_name.startswith(base + "/"):
        blob_name = blob_name[len(base) + 1:]
    return f"{base}/{blob_name}" if base else blob_name


# Upload
async def upload_bytes(data: Union[bytes, bytearray], blob_name: str, base: str = "") -> str:
    path = _normalize_path(blob_name, base)
    blob = container.get_blob_client(path)
    await blob.upload_blob(data, overwrite=True)
    return path

async def upload_file(path: str, blob_name: str, base: str = "") -> str:
    with open(path, "rb") as f:
        data = f.read()
    return await upload_bytes(data, blob_name, base=base)


# Download
async def download_bytes(blob_name: str, base: str = "") -> bytes:
    path = _normalize_path(blob_name, base)
    blob = container.get_blob_client(path)
    stream = await blob.download_blob()
    return await stream.readall()

async def download_text(blob_name: str, base: str = "", encoding: str = "utf-8") -> str:
    raw = await download_bytes(blob_name, base)
    return raw.decode(encoding, errors="ignore")


# Listing
async def list_bases() -> List[Dict]:
    return [
        {"name": "projects", "path": "projects", "is_folder": True},
        {"name": "knowledge_base", "path": "knowledge_base", "is_folder": True},
    ]

async def build_tree(base: str, prefix: str = "") -> List[Dict]:
    path = _normalize_path(prefix, base)
    if path and not path.endswith("/"):
        path += "/"

    items: List[Dict] = []
    seen_folders = set()

    async for blob in container.list_blobs(name_starts_with=path):
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
                children = await build_tree(base, (prefix + "/" + folder_name).strip("/"))
                items.append({
                    "name": folder_name,
                    "path": f"{path}{folder_name}",
                    "is_folder": True,
                    "children": children,
                })

    return items

async def explorer(base: str) -> Dict:
    return {"base": base, "children": await build_tree(base)}


# Delete
async def delete_blob(blob_name: str, base: str = "") -> bool:
    path = _normalize_path(blob_name, base)
    blob = container.get_blob_client(path)
    await blob.delete_blob()
    return True

async def delete_folder(prefix: str, base: str = "") -> List[str]:
    path = _normalize_path(prefix, base)
    if path and not path.endswith("/"):
        path += "/"

    deleted: List[str] = []
    async for blob in container.list_blobs(name_starts_with=path):
        await container.delete_blob(blob.name)
        deleted.append(blob.name)
    return deleted


# Existence & URL
async def blob_exists(blob_name: str, base: str = "") -> bool:
    path = _normalize_path(blob_name, base)
    blob = container.get_blob_client(path)
    return await blob.exists()

def get_blob_url(blob_name: str, base: str = "") -> str:
    path = _normalize_path(blob_name, base)
    return (
        f"https://{AZURE_STORAGE_ACCOUNT}.blob.core.windows.net/"
        f"{AZURE_STORAGE_CONTAINER}/{path}"
    )

def generate_sas_url(expiry_hours: int = 1) -> str:
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
