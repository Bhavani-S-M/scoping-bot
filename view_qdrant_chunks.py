#!/usr/bin/env python3
"""
View Chunks in Qdrant
Shows all document chunks stored in the Qdrant vector database
"""

from qdrant_client import QdrantClient
import json

# Qdrant configuration
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
COLLECTION_NAME = "project_kb"

def view_chunks():
    """View all chunks in Qdrant."""
    try:
        client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

        print("\n" + "="*80)
        print("Qdrant Vector Database - Document Chunks")
        print("="*80)

        # Get collection info
        try:
            collection_info = client.get_collection(COLLECTION_NAME)
            print(f"\n📊 Collection: {COLLECTION_NAME}")
            print(f"   Total vectors: {collection_info.points_count}")
            print(f"   Vector dimension: {collection_info.config.params.vectors.size}")
            print()
        except Exception as e:
            print(f"\n❌ Collection '{COLLECTION_NAME}' does not exist or is empty")
            print(f"   Error: {e}")
            print("\nMake sure you've uploaded documents to knowledge_base first!")
            return

        if collection_info.points_count == 0:
            print("⚠️  No chunks found in Qdrant!")
            print("\nTo add chunks:")
            print("1. Upload documents to knowledge_base folder")
            print("2. Wait for ETL processing")
            print("3. Run this script again")
            return

        # Scroll through all points
        print("="*80)
        print("Document Chunks")
        print("="*80)

        offset = None
        chunk_num = 0
        documents = {}

        while True:
            # Scroll through points
            points, next_offset = client.scroll(
                collection_name=COLLECTION_NAME,
                limit=100,
                offset=offset,
                with_payload=True,
                with_vectors=False  # Don't retrieve vectors (too large)
            )

            if not points:
                break

            for point in points:
                chunk_num += 1
                payload = point.payload

                file_name = payload.get("file_name", "Unknown")
                chunk_index = payload.get("chunk_index", 0)
                content = payload.get("content", "")
                doc_id = payload.get("document_id", "Unknown")

                # Group by document
                if file_name not in documents:
                    documents[file_name] = []

                documents[file_name].append({
                    "chunk_index": chunk_index,
                    "content": content,
                    "point_id": point.id
                })

            offset = next_offset
            if offset is None:
                break

        # Display by document
        for doc_name, chunks in documents.items():
            print(f"\n📄 {doc_name}")
            print(f"   Total chunks: {len(chunks)}")
            print()

            # Sort by chunk index
            chunks.sort(key=lambda x: x["chunk_index"])

            for chunk in chunks:
                print(f"   Chunk {chunk['chunk_index']}:")
                print(f"   ID: {chunk['point_id']}")

                # Show first 200 chars of content
                content_preview = chunk['content'][:200]
                if len(chunk['content']) > 200:
                    content_preview += "..."

                print(f"   Content: {content_preview}")
                print(f"   Length: {len(chunk['content'])} chars")
                print()

        print("="*80)
        print(f"Total: {chunk_num} chunks from {len(documents)} documents")
        print("="*80)
        print()

        print("💡 To view in Qdrant Dashboard:")
        print(f"   1. Open: http://localhost:6333/dashboard")
        print(f"   2. Click on '{COLLECTION_NAME}' collection")
        print(f"   3. Click 'Browse Points' to see all vectors")
        print(f"   4. Click on any point to see its payload (metadata)")
        print()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nTroubleshooting:")
        print("  • Make sure Qdrant is running: docker ps | grep qdrant")
        print("  • Check Qdrant is accessible: curl http://localhost:6333")
        print("  • Verify collection exists in dashboard: http://localhost:6333/dashboard")

if __name__ == "__main__":
    try:
        view_chunks()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
