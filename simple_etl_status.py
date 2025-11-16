#!/usr/bin/env python3
"""
Simple ETL Status Checker
Shows current state and guides you through testing
"""

import requests
import json
import sys

BACKEND_URL = "http://localhost:8000"

def check_backend():
    """Check if backend is running."""
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Backend is running")
            return True
        else:
            print("❌ Backend returned unexpected status")
            return False
    except:
        print("❌ Backend is not running!")
        print("\nPlease start the backend:")
        print("  cd backend")
        print("  python -m uvicorn app.main:app --reload")
        return False

def get_auth_token():
    """Get auth token from user."""
    print("\n" + "="*60)
    print("Authentication Required")
    print("="*60)
    print("\nTo get your auth token:")
    print("1. Login to the app in your browser")
    print("2. Open Developer Tools (F12)")
    print("3. Go to Application/Storage > Local Storage")
    print("4. Find 'token' or 'access_token' and copy it")
    print()

    token = input("Paste your auth token here: ").strip()

    if not token:
        print("❌ No token provided")
        return None

    return token

def check_etl_status(token):
    """Check ETL status with token."""
    print("\n" + "="*60)
    print("ETL Pipeline Status")
    print("="*60)

    headers = {"Authorization": f"Bearer {token}"}

    try:
        # Get ETL stats
        response = requests.get(f"{BACKEND_URL}/api/etl/stats", headers=headers)

        if response.status_code == 401:
            print("❌ Authentication failed - token may be invalid or expired")
            return False
        elif response.status_code == 403:
            print("❌ Access denied - you need SUPERUSER permissions")
            print("\nTo make your user a superuser:")
            print("1. Connect to PostgreSQL")
            print("2. Run: UPDATE users SET is_superuser = true WHERE email = 'your@email.com';")
            return False
        elif response.status_code != 200:
            print(f"❌ Failed to get ETL stats: {response.status_code}")
            print(f"Response: {response.text}")
            return False

        stats = response.json()
        print("\n📊 Current Statistics:")
        print(f"   Total documents: {stats['stats']['total_documents']}")
        print(f"   Vectorized: {stats['stats']['vectorized_documents']}")
        print(f"   Pending approval: {stats['stats']['pending_approvals']}")
        print(f"   Failed processing: {stats['stats']['failed_documents']}")

        if stats['stats']['total_documents'] == 0:
            print("\n⚠️  No documents found in knowledge base!")
            print("\n" + "="*60)
            print("Next Steps: Upload a Test Document")
            print("="*60)
            print("\nTo see chunking in action:")
            print("1. Start your backend (if not already running)")
            print("2. Open your app in the browser")
            print("3. Navigate to the file upload section")
            print("4. Upload a file to the 'knowledge_base' folder")
            print("   (You can use test_kb_document.txt)")
            print("5. Watch the backend logs for ETL processing:")
            print("   - Look for: 📤 KB document uploaded")
            print("   - Look for: ✅ Vectorized filename: X vectors created")
            print("6. Run this script again to see the results")
            print("\nAlternatively, use the API to upload:")
            print(f"   curl -X POST -H 'Authorization: Bearer YOUR_TOKEN' \\")
            print(f"        -F 'file=@test_kb_document.txt' \\")
            print(f"        -F 'base=knowledge_base' \\")
            print(f"        -F 'folder=test' \\")
            print(f"        {BACKEND_URL}/api/blobs/upload/file")
        else:
            print("\n✅ Documents found! Let's check details...")

            # Get document details
            response = requests.get(f"{BACKEND_URL}/api/etl/kb-documents?limit=5", headers=headers)
            if response.status_code == 200:
                docs_data = response.json()
                print("\n" + "="*60)
                print("Recent Documents")
                print("="*60)
                for doc in docs_data.get('documents', []):
                    print(f"\n📄 {doc['file_name']}")
                    print(f"   Status: {'✅ Vectorized' if doc['is_vectorized'] else '⏸️  Pending'}")
                    print(f"   Chunks created: {doc['vector_count']}")
                    print(f"   Uploaded: {doc['uploaded_at']}")

            # Get processing jobs
            response = requests.get(f"{BACKEND_URL}/api/etl/processing-jobs?limit=5", headers=headers)
            if response.status_code == 200:
                jobs_data = response.json()
                if jobs_data.get('jobs'):
                    print("\n" + "="*60)
                    print("Recent Processing Jobs")
                    print("="*60)
                    for job in jobs_data['jobs']:
                        status_icon = {
                            'completed': '✅',
                            'failed': '❌',
                            'processing': '⏳',
                            'pending': '⏸️'
                        }.get(job['status'], '?')

                        print(f"\n{status_icon} {job.get('document', {}).get('file_name', 'Unknown')}")
                        print(f"   Status: {job['status']}")
                        print(f"   Chunks processed: {job['chunks_processed']}")
                        print(f"   Vectors created: {job['vectors_created']}")
                        if job.get('error_message'):
                            print(f"   Error: {job['error_message']}")

        return True

    except Exception as e:
        print(f"❌ Error checking ETL status: {e}")
        return False

def main():
    print("\n" + "="*60)
    print("Simple ETL Status Checker")
    print("="*60)

    # Check backend
    if not check_backend():
        sys.exit(1)

    # Get token
    token = get_auth_token()
    if not token:
        sys.exit(1)

    # Check status
    check_etl_status(token)

    print("\n" + "="*60)
    print("Status Check Complete")
    print("="*60)
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)
