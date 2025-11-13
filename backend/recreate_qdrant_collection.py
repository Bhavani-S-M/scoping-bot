#!/usr/bin/env python3
"""
Script to recreate the Qdrant collection with the correct vector dimensions.
Run this script when you change the embedding model or VECTOR_DIM configuration.

Usage:
    python recreate_qdrant_collection.py
"""
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from qdrant_client import QdrantClient
from qdrant_client.http import models
from app.config.config import QDRANT_HOST, QDRANT_PORT, QDRANT_COLLECTION, VECTOR_DIM

def recreate_collection():
    """Delete and recreate the Qdrant collection with updated dimensions."""
    try:
        client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

        # Check if collection exists
        collections = client.get_collections().collections
        existing = [c.name for c in collections]

        if QDRANT_COLLECTION in existing:
            print(f"⚠️  Deleting existing collection '{QDRANT_COLLECTION}'...")
            client.delete_collection(collection_name=QDRANT_COLLECTION)
            print(f"✅ Collection '{QDRANT_COLLECTION}' deleted")
        else:
            print(f"ℹ️  Collection '{QDRANT_COLLECTION}' does not exist")

        # Create new collection with correct dimensions
        print(f"📝 Creating collection '{QDRANT_COLLECTION}' with {VECTOR_DIM} dimensions...")
        client.create_collection(
            collection_name=QDRANT_COLLECTION,
            vectors_config=models.VectorParams(
                size=VECTOR_DIM,
                distance=models.Distance.COSINE,
            ),
        )
        print(f"✅ Collection '{QDRANT_COLLECTION}' created successfully with {VECTOR_DIM} dimensions")
        print(f"\n🔄 You may need to re-upload your knowledge base documents to populate the collection.")

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("=" * 60)
    print("Qdrant Collection Recreation Script")
    print("=" * 60)
    print(f"Host: {QDRANT_HOST}")
    print(f"Port: {QDRANT_PORT}")
    print(f"Collection: {QDRANT_COLLECTION}")
    print(f"Vector Dimensions: {VECTOR_DIM}")
    print("=" * 60)

    response = input("\nThis will delete ALL data in the collection. Continue? (yes/no): ")
    if response.lower() in ['yes', 'y']:
        recreate_collection()
    else:
        print("❌ Operation cancelled")
        sys.exit(0)
