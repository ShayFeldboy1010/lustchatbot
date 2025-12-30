#!/usr/bin/env python3
"""
Script to upload knowledge base to MongoDB Atlas Vector Store.

This script:
1. Reads the knowledge base markdown file
2. Chunks the content into sections
3. Generates embeddings using OpenAI
4. Uploads to MongoDB Atlas with vector embeddings
"""

import os
import sys
import re
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from pymongo import MongoClient
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv(Path(__file__).parent.parent.parent / ".env")

# Configuration
MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "ecommerce")
MONGODB_COLLECTION = os.getenv("MONGODB_COLLECTION", "data-for-ai")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Knowledge base path
KNOWLEDGE_BASE_PATH = Path(__file__).parent.parent / "data" / "lust_knowledge_base.md"


def get_embedding(text: str, client: OpenAI) -> list:
    """Generate embedding for text using OpenAI"""
    response = client.embeddings.create(
        model="text-embedding-ada-002",
        input=text
    )
    return response.data[0].embedding


def chunk_markdown(content: str) -> list:
    """
    Split markdown content into chunks based on sections.
    Each section (starting with ##) becomes a separate chunk.
    """
    chunks = []

    # Split by main sections (##)
    sections = re.split(r'\n(?=## )', content)

    for section in sections:
        section = section.strip()
        if not section:
            continue

        # Extract title if exists
        title_match = re.match(r'^## (.+?)$', section, re.MULTILINE)
        title = title_match.group(1) if title_match else "General"

        # If section is too long, split by subsections (###)
        if len(section) > 2000:
            subsections = re.split(r'\n(?=### )', section)
            for subsection in subsections:
                subsection = subsection.strip()
                if subsection and len(subsection) > 100:
                    chunks.append({
                        "title": title,
                        "text": subsection
                    })
        else:
            if len(section) > 100:
                chunks.append({
                    "title": title,
                    "text": section
                })

    return chunks


def upload_knowledge_base():
    """Main function to upload knowledge base to MongoDB"""

    # Validate environment
    if not MONGODB_URI:
        print("❌ MONGODB_URI not set in environment")
        return False

    if not OPENAI_API_KEY:
        print("❌ OPENAI_API_KEY not set in environment")
        return False

    print(f"📄 Reading knowledge base from: {KNOWLEDGE_BASE_PATH}")

    # Read knowledge base
    if not KNOWLEDGE_BASE_PATH.exists():
        print(f"❌ Knowledge base file not found: {KNOWLEDGE_BASE_PATH}")
        return False

    with open(KNOWLEDGE_BASE_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    print(f"📝 Content length: {len(content)} characters")

    # Chunk the content
    chunks = chunk_markdown(content)
    print(f"📦 Created {len(chunks)} chunks")

    # Initialize clients
    openai_client = OpenAI(api_key=OPENAI_API_KEY)
    mongo_client = MongoClient(MONGODB_URI)

    try:
        db = mongo_client[MONGODB_DATABASE]
        collection = db[MONGODB_COLLECTION]

        # Clear existing documents (optional - comment out if you want to keep old data)
        print(f"🗑️  Clearing existing documents from {MONGODB_COLLECTION}...")
        collection.delete_many({})

        # Upload each chunk
        print("📤 Uploading chunks to MongoDB...")
        for i, chunk in enumerate(chunks):
            print(f"  [{i+1}/{len(chunks)}] Processing: {chunk['title'][:50]}...")

            # Generate embedding
            embedding = get_embedding(chunk['text'], openai_client)

            # Create document
            document = {
                "title": chunk['title'],
                "text": chunk['text'],
                "embedding": embedding,
                "source": "knowledge_base"
            }

            # Insert into MongoDB
            collection.insert_one(document)

        print(f"✅ Successfully uploaded {len(chunks)} chunks to MongoDB!")
        print(f"   Database: {MONGODB_DATABASE}")
        print(f"   Collection: {MONGODB_COLLECTION}")

        # Verify upload
        count = collection.count_documents({})
        print(f"   Total documents in collection: {count}")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        mongo_client.close()


if __name__ == "__main__":
    print("=" * 50)
    print("LUST Knowledge Base Uploader")
    print("=" * 50)
    success = upload_knowledge_base()
    sys.exit(0 if success else 1)
