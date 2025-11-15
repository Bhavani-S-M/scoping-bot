#!/usr/bin/env python3
"""
Direct ETL Test - Bypasses auth to show exactly what's happening

This script directly calls the ETL pipeline to show you the chunking process.
"""

import sys
import os
import asyncio
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

async def test_etl_directly():
    """Test ETL pipeline directly without going through HTTP."""

    print("=" * 60)
    print("  Direct ETL Pipeline Test")
    print("=" * 60)
    print()

    # Import after adding to path
    from app.services.etl_pipeline import get_etl_pipeline
    from app.config.database import get_async_session

    print("✓ Imports successful")
    print()

    # Get database session
    print("📊 Getting database session...")
    async for db in get_async_session():
        try:
            print("✓ Database connected")
            print()

            # Get ETL pipeline
            print("🔧 Initializing ETL pipeline...")
            etl = get_etl_pipeline()
            print("✓ ETL pipeline ready")
            print()

            # Run scan
            print("🔍 Scanning knowledge base for documents...")
            print("   (This may take 10-30 seconds)")
            print()

            stats = await etl.scan_and_process_new_documents(db)

            print("=" * 60)
            print("  ETL Scan Results")
            print("=" * 60)
            print()
            print(f"📄 Files scanned: {stats.get('scanned', 0)}")
            print(f"🆕 New documents: {stats.get('new', 0)}")
            print(f"🔄 Updated documents: {stats.get('updated', 0)}")
            print(f"❌ Failed: {stats.get('failed', 0)}")
            print(f"⏸️  Pending approval: {stats.get('pending_approval', 0)}")
            print()

            # Now check what's in the database
            print("=" * 60)
            print("  Database Status")
            print("=" * 60)
            print()

            from sqlalchemy import select, func
            from app import models

            # Count total documents
            result = await db.execute(select(func.count()).select_from(models.KnowledgeBaseDocument))
            total_docs = result.scalar()

            # Count vectorized
            result = await db.execute(
                select(func.count()).select_from(models.KnowledgeBaseDocument).where(
                    models.KnowledgeBaseDocument.is_vectorized == True
                )
            )
            vectorized_docs = result.scalar()

            # Count pending approvals
            result = await db.execute(
                select(func.count()).select_from(models.PendingKBUpdate).where(
                    models.PendingKBUpdate.status == "pending"
                )
            )
            pending_approvals = result.scalar()

            print(f"📚 Total KB documents: {total_docs}")
            print(f"✅ Vectorized: {vectorized_docs}")
            print(f"⏸️  Pending approval: {pending_approvals}")
            print()

            # Show recent documents
            if total_docs > 0:
                print("=" * 60)
                print("  Recent Documents")
                print("=" * 60)
                print()

                result = await db.execute(
                    select(models.KnowledgeBaseDocument).order_by(
                        models.KnowledgeBaseDocument.uploaded_at.desc()
                    ).limit(5)
                )
                docs = result.scalars().all()

                for doc in docs:
                    status = "✅ Vectorized" if doc.is_vectorized else "⏸️  Waiting"
                    print(f"{status} | {doc.file_name}")
                    print(f"         Chunks: {doc.vector_count}")
                    print(f"         Size: {doc.file_size:,} bytes")
                    print(f"         Uploaded: {doc.uploaded_at}")
                    if doc.vectorized_at:
                        print(f"         Vectorized: {doc.vectorized_at}")
                    print()

            # Show processing jobs
            result = await db.execute(
                select(models.DocumentProcessingJob).order_by(
                    models.DocumentProcessingJob.created_at.desc()
                ).limit(5)
            )
            jobs = result.scalars().all()

            if jobs:
                print("=" * 60)
                print("  Recent Processing Jobs")
                print("=" * 60)
                print()

                for job in jobs:
                    # Get document name
                    doc_result = await db.execute(
                        select(models.KnowledgeBaseDocument).where(
                            models.KnowledgeBaseDocument.id == job.document_id
                        )
                    )
                    doc = doc_result.scalar_one_or_none()
                    file_name = doc.file_name if doc else "Unknown"

                    status_icon = {
                        'completed': '✅',
                        'failed': '❌',
                        'processing': '⏳',
                        'pending': '⏸️'
                    }.get(job.status, '?')

                    print(f"{status_icon} {file_name}")
                    print(f"   Status: {job.status}")
                    print(f"   Chunks: {job.chunks_processed}")
                    print(f"   Vectors: {job.vectors_created}")
                    if job.error_message:
                        print(f"   Error: {job.error_message}")
                    print()

            # Check Qdrant
            print("=" * 60)
            print("  Qdrant Status")
            print("=" * 60)
            print()

            try:
                from app.utils.ai_clients import get_qdrant_client
                from app.config.config import QDRANT_COLLECTION

                qdrant = get_qdrant_client()
                collection_info = qdrant.get_collection(QDRANT_COLLECTION)

                print(f"✅ Qdrant connected")
                print(f"   Collection: {QDRANT_COLLECTION}")
                print(f"   Total vectors: {collection_info.points_count}")
                print()

            except Exception as e:
                print(f"⚠️  Could not connect to Qdrant: {e}")
                print()

            await db.close()
            break  # Only use first session

        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            await db.close()
            break

    print("=" * 60)
    print("  Test Complete!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. If documents are 'Waiting', check for pending approvals")
    print("2. Use quick_etl_check.sh to approve pending updates")
    print("3. Upload a new document to see it get processed")
    print()

if __name__ == "__main__":
    try:
        asyncio.run(test_etl_directly())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
