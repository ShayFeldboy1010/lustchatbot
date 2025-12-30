"""MongoDB Atlas Vector Store Tool for knowledge base search"""

from pymongo import MongoClient
from openai import OpenAI
from typing import List, Optional
import asyncio

from ..config import get_settings

settings = get_settings()

# Initialize OpenAI client for embeddings
openai_client = OpenAI(api_key=settings.openai_api_key)

# MongoDB connection (lazy initialization)
_mongo_client: Optional[MongoClient] = None
_collection = None


def get_mongo_collection():
    """Get or create MongoDB collection connection"""
    global _mongo_client, _collection

    if _collection is None:
        _mongo_client = MongoClient(settings.mongodb_uri)
        db = _mongo_client[settings.mongodb_database]
        _collection = db[settings.mongodb_collection]

    return _collection


def get_embedding(text: str) -> List[float]:
    """Generate embedding using OpenAI text-embedding-ada-002"""
    response = openai_client.embeddings.create(
        model="text-embedding-ada-002",
        input=text
    )
    return response.data[0].embedding


async def search_knowledge_base(query: str, top_k: int = 5) -> List[str]:
    """
    Search MongoDB Atlas vector store for relevant information.

    Args:
        query: The search query
        top_k: Number of results to return

    Returns:
        List of relevant text snippets from the knowledge base
    """
    # Run synchronous operations in thread pool
    loop = asyncio.get_event_loop()

    # Generate query embedding
    query_embedding = await loop.run_in_executor(
        None, get_embedding, query
    )

    collection = get_mongo_collection()

    # Vector search pipeline - get ALL documents since we only have 3
    pipeline = [
        {
            "$vectorSearch": {
                "index": settings.mongodb_vector_index,
                "path": "embedding",
                "queryVector": query_embedding,
                "numCandidates": 100,
                "limit": 10  # Get more results
            }
        },
        {
            "$project": {
                "text": 1,
                "content": 1,
                "title": 1,
                "score": {"$meta": "vectorSearchScore"}
            }
        }
    ]

    # Execute search
    results = await loop.run_in_executor(
        None, lambda: list(collection.aggregate(pipeline))
    )

    # Extract text from results - include all with reasonable score
    texts = []
    for doc in results:
        score = doc.get("score", 0)
        # Include all results with score > 0.3 (lower threshold)
        if score > 0.3:
            text = doc.get("text") or doc.get("content") or doc.get("title")
            if text:
                texts.append(text)

    # If no results, return all documents as fallback
    if not texts:
        all_docs = await loop.run_in_executor(
            None, lambda: list(collection.find({}, {"text": 1}))
        )
        for doc in all_docs:
            text = doc.get("text")
            if text:
                texts.append(text)

    return texts


async def add_document(text: str, metadata: dict = None) -> bool:
    """
    Add a document to the vector store.

    Args:
        text: The text content to add
        metadata: Optional metadata to store with the document

    Returns:
        True if successful, False otherwise
    """
    try:
        loop = asyncio.get_event_loop()

        # Generate embedding
        embedding = await loop.run_in_executor(
            None, get_embedding, text
        )

        collection = get_mongo_collection()

        # Create document
        document = {
            "text": text,
            "embedding": embedding,
            **(metadata or {})
        }

        # Insert document
        await loop.run_in_executor(
            None, collection.insert_one, document
        )

        return True
    except Exception as e:
        print(f"Error adding document: {e}")
        return False


def close_connection():
    """Close MongoDB connection"""
    global _mongo_client
    if _mongo_client:
        _mongo_client.close()
        _mongo_client = None
