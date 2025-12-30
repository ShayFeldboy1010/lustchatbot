"""Test MongoDB Connection"""
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from pymongo import MongoClient
from dotenv import load_dotenv

# Force reload environment variables
load_dotenv(override=True)

mongodb_uri = os.getenv('MONGODB_URI')
print(f"URI: {mongodb_uri[:50]}...") # Print partial URI to verify
mongodb_database = os.getenv('MONGODB_DATABASE', 'ecommerce')
mongodb_collection = os.getenv('MONGODB_COLLECTION', 'data-for-ai')

print(f"Testing MongoDB connection...")
print(f"Database: {mongodb_database}")
print(f"Collection: {mongodb_collection}")
print("-" * 50)

try:
    # Connect to MongoDB
    client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)

    # Test connection
    server_info = client.server_info()
    print(f"✅ Connected to MongoDB!")
    print(f"   Server version: {server_info.get('version', 'unknown')}")

    # List databases
    dbs = client.list_database_names()
    print(f"\n📁 Available databases: {dbs}")

    # Check if our database exists
    if mongodb_database in dbs:
        print(f"\n✅ Database '{mongodb_database}' exists")
    else:
        print(f"\n⚠️  Database '{mongodb_database}' not found in list (may be created on first write)")

    # Get the database and collection
    db = client[mongodb_database]
    collections = db.list_collection_names()
    print(f"\n📁 Collections in '{mongodb_database}': {collections}")

    # Check our collection
    if mongodb_collection in collections:
        print(f"\n✅ Collection '{mongodb_collection}' exists")

        # Count documents
        collection = db[mongodb_collection]
        count = collection.count_documents({})
        print(f"   Documents in collection: {count}")

        # Sample a document
        if count > 0:
            sample = collection.find_one()
            print(f"\n📄 Sample document fields: {list(sample.keys())}")

            # Check if embedding field exists
            if 'embedding' in sample:
                print(f"   ✅ Has 'embedding' field (vector search ready)")
                print(f"   Embedding dimension: {len(sample['embedding'])}")
            else:
                print(f"   ⚠️  No 'embedding' field found - vector search may not work")
    else:
        print(f"\n⚠️  Collection '{mongodb_collection}' not found")
        print(f"   Available collections: {collections}")

    # Check vector search index
    print(f"\n🔍 Checking vector search indexes...")
    try:
        indexes = list(collection.list_search_indexes())
        if indexes:
            print(f"   Found {len(indexes)} search index(es):")
            for idx in indexes:
                print(f"   - {idx.get('name', 'unnamed')}: {idx.get('type', 'unknown')}")
        else:
            print(f"   ⚠️  No search indexes found")
    except Exception as e:
        print(f"   ⚠️  Could not list search indexes: {e}")

    client.close()
    print(f"\n✅ MongoDB test completed successfully!")

except Exception as e:
    print(f"\n❌ MongoDB connection failed!")
    print(f"   Error: {e}")
    import traceback
    traceback.print_exc()
