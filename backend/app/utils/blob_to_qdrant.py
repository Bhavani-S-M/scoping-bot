# # backend/app/utils/blob_to_qdrant.py
# import io
# import logging
# from qdrant_client import QdrantClient, models
# from azure.storage.blob import BlobServiceClient
# from app.utils.ai_clients import get_embeddings_model
# from app.utils.scope_engine import extract_text_from_file  # assume you already have text extraction logic
# from app.config.config import settings

# logger = logging.getLogger(__name__)

# def process_blob_and_store_vectors(blob_name: str):
#     try:
#         # Initialize Azure Blob client
#         blob_service_client = BlobServiceClient.from_connection_string(settings.AZURE_STORAGE_CONNECTION_STRING)
#         container_client = blob_service_client.get_container_client(settings.AZURE_CONTAINER_NAME)
#         blob_client = container_client.get_blob_client(blob_name)

#         # Download blob content
#         file_bytes = blob_client.download_blob().readall()
#         text = extract_text_from_file(io.BytesIO(file_bytes), blob_name)
#         if not text:
#             logger.warning(f"No text extracted from {blob_name}")
#             return

#         # Generate embeddings
#         embedder = get_embeddings_model()  # returns an embedding model client
#         embeddings = embedder.embed_text(text)

#         # Connect to Qdrant
#         qdrant = QdrantClient(url=f"http://{settings.QDRANT_HOST}:{settings.QDRANT_PORT}")
#         qdrant.upsert(
#             collection_name=settings.QDRANT_COLLECTION,
#             points=[
#                 models.PointStruct(
#                     id=None,
#                     vector=embeddings,
#                     payload={"file_name": blob_name, "content": text[:5000]}
#                 )
#             ]
#         )
#         logger.info(f"✅ Successfully indexed {blob_name} into Qdrant")

#     except Exception as e:
#         logger.error(f"❌ Failed to process blob {blob_name}: {e}")
