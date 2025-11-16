#!/usr/bin/env python3
"""
Upload Test Document to Knowledge Base
This will trigger the ETL pipeline and show you chunking in action
"""

import requests
import sys
import time

BACKEND_URL = "http://localhost:8000"
TEST_FILE = "test_kb_document.txt"

def upload_document(token):
    """Upload test document to knowledge base."""
    print("\n" + "="*60)
    print("Uploading Test Document to Knowledge Base")
    print("="*60)
    print()

    # Check if test file exists
    try:
        with open(TEST_FILE, 'rb') as f:
            file_content = f.read()
    except FileNotFoundError:
        print(f"❌ Test file not found: {TEST_FILE}")
        print("\nMake sure you're in the scoping-bot directory")
        return False

    print(f"✅ Found test file: {TEST_FILE} ({len(file_content)} bytes)")
    print()

    # Upload
    print("📤 Uploading to knowledge_base folder...")
    print("   (This will trigger the ETL pipeline)")
    print()

    headers = {"Authorization": f"Bearer {token}"}
    files = {"file": (TEST_FILE, file_content, "text/plain")}
    data = {
        "base": "knowledge_base",
        "folder": "test"
    }

    try:
        response = requests.post(
            f"{BACKEND_URL}/api/blobs/upload/file",
            headers=headers,
            files=files,
            data=data,
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            print("✅ Upload successful!")
            print(f"   Blob path: {result.get('blob', 'N/A')}")
            print()
            print("🔄 ETL pipeline is processing the document...")
            print("   (This happens in the background)")
            print()
            print("📋 Check your backend logs for:")
            print("   - 📤 KB document uploaded: knowledge_base/test/test_kb_document.txt")
            print("   - 🔍 Starting ETL scan for new KB documents...")
            print("   - ✅ Vectorized test_kb_document.txt: X vectors created")
            print()
            print("⏱️  Waiting 5 seconds for processing...")

            time.sleep(5)

            print()
            print("="*60)
            print("Now let's check the results!")
            print("="*60)
            print()

            # Check stats
            stats_response = requests.get(
                f"{BACKEND_URL}/api/etl/stats",
                headers=headers
            )

            if stats_response.status_code == 200:
                stats = stats_response.json()
                print("📊 ETL Statistics:")
                print(f"   Total documents: {stats['stats']['total_documents']}")
                print(f"   Vectorized: {stats['stats']['vectorized_documents']}")
                print(f"   Pending approval: {stats['stats']['pending_approvals']}")
                print()

            # Get document details
            docs_response = requests.get(
                f"{BACKEND_URL}/api/etl/kb-documents?limit=5",
                headers=headers
            )

            if docs_response.status_code == 200:
                docs_data = docs_response.json()
                docs = docs_data.get('documents', [])

                if docs:
                    print("📄 Recent Documents:")
                    for doc in docs:
                        if 'test_kb_document' in doc['file_name']:
                            print(f"\n   ✅ {doc['file_name']}")
                            print(f"      Status: {'Vectorized ✅' if doc['is_vectorized'] else 'Pending ⏸️'}")
                            print(f"      Chunks created: {doc['vector_count']}")
                            print(f"      Size: {doc['file_size']} bytes")
                            print()

                            if doc['is_vectorized'] and doc['vector_count'] > 0:
                                print("="*60)
                                print("🎉 SUCCESS! Document was chunked!")
                                print("="*60)
                                print(f"\nYour document was split into {doc['vector_count']} chunks")
                                print("and stored in Qdrant as vectors.")
                                print()
                                print("Each chunk:")
                                print("  • Contains ~1000 characters")
                                print("  • Has 200 characters overlap with neighbors")
                                print("  • Is stored as a vector embedding")
                                print("  • Can be retrieved for RAG")
                                print()
                                print("To view the chunks in Qdrant:")
                                print("  1. Open http://localhost:6333/dashboard")
                                print("  2. Click on 'project_kb' collection")
                                print("  3. Click 'Browse Points'")
                                print(f"  4. Look for file_name: {doc['file_name']}")
                                print()
                            else:
                                print("⏸️  Document may be pending approval")
                                print("   (This happens if it's similar to existing docs)")
                                print()
                                print("Check pending approvals:")
                                print(f"  python3 simple_etl_status.py")

            # Get processing jobs
            jobs_response = requests.get(
                f"{BACKEND_URL}/api/etl/processing-jobs?limit=5",
                headers=headers
            )

            if jobs_response.status_code == 200:
                jobs_data = jobs_response.json()
                jobs = jobs_data.get('jobs', [])

                if jobs:
                    print("\n⚙️  Processing Jobs:")
                    for job in jobs:
                        doc_name = job.get('document', {}).get('file_name', 'Unknown')
                        if 'test_kb_document' in doc_name:
                            status_icon = {
                                'completed': '✅',
                                'failed': '❌',
                                'processing': '⏳',
                                'pending': '⏸️'
                            }.get(job['status'], '?')

                            print(f"\n   {status_icon} {doc_name}")
                            print(f"      Status: {job['status']}")
                            print(f"      Chunks processed: {job['chunks_processed']}")
                            print(f"      Vectors created: {job['vectors_created']}")

                            if job.get('error_message'):
                                print(f"      Error: {job['error_message']}")

            return True

        else:
            print(f"❌ Upload failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Error uploading: {e}")
        return False

def main():
    print("\n" + "="*60)
    print("ETL Pipeline Test - Upload Test Document")
    print("="*60)

    # Check backend
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        if response.status_code != 200:
            print("\n❌ Backend is not responding correctly")
            sys.exit(1)
        print("\n✅ Backend is running")
    except:
        print("\n❌ Backend is not running!")
        print("\nPlease start the backend first:")
        print("  cd backend")
        print("  python -m uvicorn app.main:app --reload")
        sys.exit(1)

    # Get token
    print()
    print("To get your auth token:")
    print("1. Login to the app in your browser")
    print("2. Open Developer Tools (F12)")
    print("3. Go to Application/Storage > Local Storage")
    print("4. Find 'token' or 'access_token' and copy it")
    print()

    token = input("Paste your auth token here: ").strip()

    if not token:
        print("❌ No token provided")
        sys.exit(1)

    # Upload
    success = upload_document(token)

    print("\n" + "="*60)
    print("Test Complete!")
    print("="*60)

    if success:
        print("\nNext steps:")
        print("  • Check backend logs for detailed processing info")
        print("  • View vectors in Qdrant: http://localhost:6333/dashboard")
        print("  • Run: python3 simple_etl_status.py (to see current state)")
        print("  • Try generating a project scope (to see RAG retrieval)")
    else:
        print("\nTroubleshooting:")
        print("  • Make sure you're a SUPERUSER")
        print("  • Check backend logs for errors")
        print("  • Verify Qdrant is running: docker ps | grep qdrant")

    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)
