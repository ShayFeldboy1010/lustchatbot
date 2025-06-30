import pandas as pd
from pinecone import Pinecone, ServerlessSpec
from agno.embedder.openai import OpenAIEmbedder
from typing import List, Optional, Dict, Any
import os
from .settings import settings
import logging
import uuid

logger = logging.getLogger(__name__)


class Document:
    """Simple document class compatible with Agno"""
    
    def __init__(self, page_content: str, metadata: Dict[str, Any] = None):
        self.page_content = page_content
        self.metadata = metadata or {}


class LustVectorStore:
    """Vector store for Lust products using Pinecone and Agno"""
    
    def __init__(self):
        self.embedder = OpenAIEmbedder(
            id="text-embedding-3-small",
            api_key=settings.openai_api_key
        )
        self.index_name = settings.pinecone_index_name
        self.pinecone_client: Optional[Pinecone] = None
        self.index = None
        self.vectorstore = None
        self._initialize_pinecone()
    
    def _initialize_pinecone(self):
        """Initialize Pinecone connection"""
        try:
            self.pinecone_client = Pinecone(api_key=settings.pinecone_api_key)
            
            # Check if index exists, if not create it
            existing_indexes = [index.name for index in self.pinecone_client.list_indexes()]
            
            if self.index_name not in existing_indexes:
                logger.info(f"Creating new Pinecone index: {self.index_name}")
                self.pinecone_client.create_index(
                    name=self.index_name,
                    dimension=1536,  # OpenAI text-embedding-3-small dimension
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud="aws",
                        region="us-east-1"
                    )
                )
            
            self.index = self.pinecone_client.Index(self.index_name)
            logger.info(f"Connected to Pinecone index: {self.index_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Pinecone: {e}")
            # Don't raise to allow app to start even if Pinecone is not configured
    
    def load_products_from_csv(self, csv_path: str = "data/lust_products.csv") -> bool:
        """Load products from CSV file into vector store"""
        try:
            if not os.path.exists(csv_path):
                logger.warning(f"CSV file not found: {csv_path}")
                return False
            
            if not self.index:
                logger.error("Pinecone index not available")
                return False
            
            # Read CSV
            df = pd.read_csv(csv_path)
            logger.info(f"Loaded {len(df)} products from {csv_path}")
            
            # Create documents and embeddings
            vectors_to_upsert = []
            
            for _, row in df.iterrows():
                # Create product text
                product_text = self._create_product_text(row)
                
                # Generate embedding
                embedding = self.embedder.get_embedding(product_text)
                
                # Create vector for upsert
                vector_id = str(uuid.uuid4())
                metadata = {
                    "product_id": str(row.get("id", "")),
                    "name": str(row.get("name", "")),
                    "price": str(row.get("price", "")),
                    "category": str(row.get("category", "")),
                    "url": str(row.get("url", "")),
                    "in_stock": str(row.get("in_stock", True)),
                    "text": product_text
                }
                
                vectors_to_upsert.append({
                    "id": vector_id,
                    "values": embedding,
                    "metadata": metadata
                })
            
            # Upsert vectors to Pinecone
            self.index.upsert(vectors=vectors_to_upsert)
            
            logger.info(f"Successfully uploaded {len(vectors_to_upsert)} products to Pinecone")
            self.vectorstore = True  # Mark as available
            return True
            
        except Exception as e:
            logger.error(f"Failed to load products from CSV: {e}")
            return False
    
    def _create_product_text(self, row) -> str:
        """Create searchable text from product row"""
        text_parts = []
        
        # Product name
        if pd.notna(row.get("name")):
            text_parts.append(f"Product: {row['name']}")
        
        # Description
        if pd.notna(row.get("description")):
            text_parts.append(f"Description: {row['description']}")
        
        # Category
        if pd.notna(row.get("category")):
            text_parts.append(f"Category: {row['category']}")
        
        # Price
        if pd.notna(row.get("price")):
            text_parts.append(f"Price: {row['price']}")
        
        # Features/tags
        if pd.notna(row.get("features")):
            text_parts.append(f"Features: {row['features']}")
        
        # Brand
        if pd.notna(row.get("brand")):
            text_parts.append(f"Brand: {row['brand']}")
        
        # Fragrance notes
        if pd.notna(row.get("fragrance_notes")):
            text_parts.append(f"Fragrance Notes: {row['fragrance_notes']}")
        
        # Unique advantages (this contains the natural ingredients info!)
        if pd.notna(row.get("unique_advantages")):
            text_parts.append(f"Advantages: {row['unique_advantages']}")
            
        # Prices info
        if pd.notna(row.get("prices_info")):
            text_parts.append(f"Pricing: {row['prices_info']}")
        
        return "\n".join(text_parts)
    
    def search_products(self, query: str, k: int = 5) -> List[Document]:
        """Search for products using similarity search"""
        if not self.index:
            logger.error("Pinecone index not available")
            return []
        
        try:
            # Generate query embedding
            query_embedding = self.embedder.get_embedding(query)
            
            # Search in Pinecone
            results = self.index.query(
                vector=query_embedding,
                top_k=k,
                include_metadata=True
            )
            
            # Convert to Document objects
            documents = []
            for match in results.matches:
                doc = Document(
                    page_content=match.metadata.get("text", ""),
                    metadata={
                        "product_id": match.metadata.get("product_id", ""),
                        "name": match.metadata.get("name", ""),
                        "price": match.metadata.get("price", ""),
                        "category": match.metadata.get("category", ""),
                        "url": match.metadata.get("url", ""),
                        "in_stock": match.metadata.get("in_stock", ""),
                        "score": match.score
                    }
                )
                documents.append(doc)
            
            logger.info(f"Found {len(documents)} products for query: {query}")
            return documents
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def delete_index(self):
        """Delete the Pinecone index (use with caution)"""
        try:
            if self.pinecone_client:
                self.pinecone_client.delete_index(self.index_name)
                logger.info(f"Deleted Pinecone index: {self.index_name}")
        except Exception as e:
            logger.error(f"Failed to delete index: {e}")


# Global instance
vector_store = LustVectorStore()
