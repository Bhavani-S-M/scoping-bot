#!/usr/bin/env python3
"""
Detailed ETL Pipeline Chunk Verification Script

This script connects directly to Qdrant and PostgreSQL to show you
exactly how documents are chunked and stored.
"""

import sys
import json
from qdrant_client import QdrantClient
import psycopg2
from datetime import datetime

# Configuration - Update these with your settings
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
QDRANT_COLLECTION = "project_kb"  # Update with your collection name

# PostgreSQL connection - Update with your database credentials
DB_CONFIG = {
    "host": "localhost",
    "database": "scoping_bot",  # Update with your database name
    "user": "postgres",          # Update with your username
    "password": "password"       # Update with your password
}

def print_section(title):
    """Print a formatted section header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def check_qdrant_connection():
    """Check if Qdrant is accessible."""
    try:
        client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        collections = client.get_collections()
        print(f"✓ Connected to Qdrant at {QDRANT_HOST}:{QDRANT_PORT}")
        print(f"  Available collections: {[c.name for c in collections.collections]}")
        return client
    except Exception as e:
        print(f"✗ Failed to connect to Qdrant: {e}")
        print(f"  Make sure Qdrant is running: docker ps | grep qdrant")
        return None

def check_database_connection():
    """Check if PostgreSQL is accessible."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print(f"✓ Connected to PostgreSQL database: {DB_CONFIG['database']}")
        return conn
    except Exception as e:
        print(f"✗ Failed to connect to database: {e}")
        print(f"  Update DB_CONFIG in this script with your credentials")
        return None

def show_kb_documents(conn):
    """Show all knowledge base documents from database."""
    print_section("Knowledge Base Documents (PostgreSQL)")

    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                file_name,
                is_vectorized,
                vector_count,
                file_size,
                uploaded_at,
                vectorized_at
            FROM knowledge_base_documents
            ORDER BY uploaded_at DESC
            LIMIT 10
        """)

        rows = cursor.fetchall()

        if not rows:
            print("No documents found in database")
            return

        print(f"\nFound {len(rows)} document(s):\n")

        for row in rows:
            file_name, is_vectorized, vector_count, file_size, uploaded_at, vectorized_at = row
            print(f"📄 {file_name}")
            print(f"   Status: {'✓ Vectorized' if is_vectorized else '✗ Not vectorized'}")
            print(f"   Chunks: {vector_count} vectors created")
            print(f"   Size: {file_size:,} bytes")
            print(f"   Uploaded: {uploaded_at}")
            if vectorized_at:
                print(f"   Vectorized: {vectorized_at}")
            print()

        cursor.close()
    except Exception as e:
        print(f"Error querying database: {e}")

def show_processing_jobs(conn):
    """Show processing job details."""
    print_section("Processing Jobs Status")

    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                j.status,
                j.chunks_processed,
                j.vectors_created,
                j.error_message,
                j.created_at,
                j.completed_at,
                d.file_name
            FROM document_processing_jobs j
            JOIN knowledge_base_documents d ON j.document_id = d.id
            ORDER BY j.created_at DESC
            LIMIT 10
        """)

        rows = cursor.fetchall()

        if not rows:
            print("No processing jobs found")
            return

        print(f"\nFound {len(rows)} job(s):\n")

        for row in rows:
            status, chunks, vectors, error, created, completed, file_name = row

            status_icon = {
                'completed': '✓',
                'failed': '✗',
                'processing': '⏳',
                'pending': '⏸'
            }.get(status, '?')

            print(f"{status_icon} {file_name}")
            print(f"   Status: {status}")
            print(f"   Chunks processed: {chunks}")
            print(f"   Vectors created: {vectors}")
            if error:
                print(f"   Error: {error}")
            print(f"   Started: {created}")
            if completed:
                duration = (completed - created).total_seconds()
                print(f"   Completed: {completed} (took {duration:.1f}s)")
            print()

        cursor.close()
    except Exception as e:
        print(f"Error querying jobs: {e}")

def show_qdrant_vectors(client, document_name=None):
    """Show vectors stored in Qdrant."""
    print_section("Vectors in Qdrant")

    try:
        # Get collection info
        collection_info = client.get_collection(QDRANT_COLLECTION)
        points_count = collection_info.points_count

        print(f"\nCollection: {QDRANT_COLLECTION}")
        print(f"Total vectors: {points_count}\n")

        if points_count == 0:
            print("No vectors found in collection")
            return

        # Scroll through points
        scroll_result = client.scroll(
            collection_name=QDRANT_COLLECTION,
            limit=20,
            with_payload=True,
            with_vectors=False
        )

        points = scroll_result[0]

        # Group by document
        docs = {}
        for point in points:
            payload = point.payload or {}
            file_name = payload.get('file_name', 'Unknown')

            if file_name not in docs:
                docs[file_name] = []

            docs[file_name].append({
                'id': point.id,
                'chunk_index': payload.get('chunk_index', 0),
                'content_preview': payload.get('content', '')[:100]
            })

        # Display
        print(f"Showing vectors from {len(docs)} document(s):\n")

        for file_name, chunks in sorted(docs.items()):
            if document_name and document_name not in file_name:
                continue

            print(f"📄 {file_name}")
            print(f"   Total chunks: {len(chunks)}")

            # Show first 3 chunks as example
            for chunk in sorted(chunks, key=lambda x: x['chunk_index'])[:3]:
                print(f"\n   Chunk {chunk['chunk_index']}:")
                print(f"   Vector ID: {chunk['id']}")
                print(f"   Content: {chunk['content_preview']}...")

            if len(chunks) > 3:
                print(f"\n   ... and {len(chunks) - 3} more chunks")
            print()

    except Exception as e:
        print(f"Error querying Qdrant: {e}")

def show_chunk_details(client, conn, file_name):
    """Show detailed chunk breakdown for a specific file."""
    print_section(f"Detailed Chunk Analysis: {file_name}")

    try:
        # Get all vectors for this document
        scroll_result = client.scroll(
            collection_name=QDRANT_COLLECTION,
            scroll_filter={
                "must": [
                    {
                        "key": "file_name",
                        "match": {"value": file_name}
                    }
                ]
            },
            limit=100,
            with_payload=True
        )

        chunks = scroll_result[0]

        if not chunks:
            print(f"No chunks found for {file_name}")
            return

        print(f"\nFound {len(chunks)} chunks for {file_name}\n")

        # Show each chunk
        for point in sorted(chunks, key=lambda x: x.payload.get('chunk_index', 0)):
            payload = point.payload
            chunk_idx = payload.get('chunk_index', 0)
            content = payload.get('content', '')

            print(f"{'─' * 60}")
            print(f"Chunk #{chunk_idx}")
            print(f"Vector ID: {point.id}")
            print(f"Length: {len(content)} characters")
            print(f"\nContent:")
            print(content)
            print()

    except Exception as e:
        print(f"Error getting chunk details: {e}")

def main():
    """Main function."""
    print("\n" + "=" * 60)
    print("  ETL Pipeline Chunk Verification Tool")
    print("=" * 60)

    # Connect to services
    qdrant_client = check_qdrant_connection()
    db_conn = check_database_connection()

    if not qdrant_client or not db_conn:
        print("\n✗ Cannot proceed without connections")
        sys.exit(1)

    # Show database info
    show_kb_documents(db_conn)
    show_processing_jobs(db_conn)

    # Show Qdrant info
    show_qdrant_vectors(qdrant_client)

    # Ask if user wants detailed chunk view
    print("\n" + "=" * 60)
    print("  Detailed Chunk Analysis")
    print("=" * 60)
    print("\nDo you want to see detailed chunks for a specific document?")
    print("Enter the filename (or press Enter to skip): ", end='')

    try:
        file_name = input().strip()
        if file_name:
            show_chunk_details(qdrant_client, db_conn, file_name)
    except (KeyboardInterrupt, EOFError):
        print("\nSkipping detailed analysis")

    # Cleanup
    db_conn.close()

    print("\n" + "=" * 60)
    print("  Verification Complete!")
    print("=" * 60)
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)
