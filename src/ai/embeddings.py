# src/ai/embeddings.py
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Dict
import chromadb
from pathlib import Path
import shutil
import os
from src.utils.logging_utils import logger
from src.utils.gpu_utils import gpu_manager

class EmbeddingManager:
    def __init__(self, config: Dict):
        self.config = config
        self.device = gpu_manager.device
        self.model = None
        self.vector_store = None
        self.client = None
        self.load_embeddings_model()
        self.setup_vector_store()
    
    def load_embeddings_model(self):
        """Load sentence transformer model with error handling"""
        try:
            model_name = self.config["models"]["embeddings"]["name"]
            logger.info(f"Loading embeddings model: {model_name}")
            
            self.model = SentenceTransformer(model_name, device=self.device)
            logger.info("✅ Embeddings model loaded successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to load embeddings model: {e}")
            self.model = None
    
    def _reset_vector_store(self, persist_directory: str):
        """Reset vector store by removing corrupted database"""
        try:
            if os.path.exists(persist_directory):
                logger.info("Removing corrupted ChromaDB database...")
                shutil.rmtree(persist_directory)
            
            # Recreate directory
            Path(persist_directory).mkdir(parents=True, exist_ok=True)
            logger.info("ChromaDB database reset successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to reset vector store: {e}")
            return False
    
    def setup_vector_store(self):
        """Setup ChromaDB vector store with automatic recovery"""
        persist_directory = str(Path(__file__).parent.parent.parent / "chroma_db")
        
        # Try to initialize ChromaDB
        max_attempts = 2
        for attempt in range(max_attempts):
            try:
                # Ensure directory exists
                Path(persist_directory).mkdir(parents=True, exist_ok=True)
                
                # Initialize ChromaDB client
                self.client = chromadb.PersistentClient(path=persist_directory)
                
                # Try to create or get collection
                collection_name = "research_papers"
                
                try:
                    # Try to get existing collection first
                    self.vector_store = self.client.get_collection(collection_name)
                    logger.info("📚 Loaded existing vector store")
                    return
                    
                except Exception:
                    # Collection doesn't exist or is corrupted, create new one
                    try:
                        self.vector_store = self.client.create_collection(
                            name=collection_name,
                            metadata={"hnsw:space": "cosine"}
                        )
                        logger.info("📚 Created new vector store")
                        return
                        
                    except Exception as create_error:
                        logger.warning(f"Failed to create collection: {create_error}")
                        if attempt == 0:  # First attempt failed, try reset
                            logger.info("Attempting to reset corrupted database...")
                            if self._reset_vector_store(persist_directory):
                                continue  # Try again with fresh database
                        raise create_error
                        
            except Exception as e:
                logger.error(f"❌ Vector store setup attempt {attempt + 1} failed: {e}")
                
                if attempt == 0:  # First attempt failed, try database reset
                    logger.info("Attempting database recovery...")
                    if not self._reset_vector_store(persist_directory):
                        break  # Reset failed, give up
                else:
                    # Final attempt failed
                    break
        
        # If we get here, all attempts failed
        logger.error("❌ All vector store setup attempts failed")
        self.vector_store = None
        self.client = None
    
    def is_available(self) -> bool:
        """Check if embeddings system is available"""
        return self.model is not None and self.vector_store is not None
    
    def add_papers_to_store(self, papers: List[Dict]):
        """Add papers to vector store with embeddings"""
        if not self.is_available():
            logger.warning("⚠️ Embeddings system not available - skipping vector store update")
            return
        
        try:
            if not papers:
                logger.warning("No papers to add to vector store")
                return
            
            # Clear existing data to avoid duplicates - in batches to avoid ChromaDB limits
            try:
                # Get all existing IDs and delete them in batches
                existing_data = self.vector_store.get()
                if existing_data and existing_data.get('ids'):
                    existing_ids = existing_data['ids']
                    # ChromaDB has a limit, delete in batches of 10,000
                    delete_batch_size = 10000
                    deleted_count = 0
                    for i in range(0, len(existing_ids), delete_batch_size):
                        batch_ids = existing_ids[i:i + delete_batch_size]
                        try:
                            self.vector_store.delete(ids=batch_ids)
                            deleted_count += len(batch_ids)
                        except Exception as batch_error:
                            logger.warning(f"Could not delete batch {i//delete_batch_size + 1}: {batch_error}")
                            continue
                    logger.info(f"Cleared {deleted_count} existing vector store entries")
            except Exception as e:
                logger.warning(f"Could not clear existing data: {e}")
            
            # Prepare documents for embedding
            valid_papers = []
            documents = []
            metadatas = []
            ids = []
            
            for i, paper in enumerate(papers):
                try:
                    # Create document text
                    title = paper.get('title', '').strip()
                    abstract = paper.get('abstract', '').strip()
                    doc_text = f"{title} {abstract}".strip()
                    
                    if len(doc_text) < 10:  # Skip very short documents
                        continue
                    
                    documents.append(doc_text)
                    
                    # Prepare metadata (all values must be strings)
                    authors = paper.get('authors', [])
                    if isinstance(authors, list):
                        authors_str = ', '.join(str(a) for a in authors[:5])  # Limit authors
                    else:
                        authors_str = str(authors)
                    
                    categories = paper.get('categories', [])
                    if isinstance(categories, list):
                        categories_str = ', '.join(str(c) for c in categories[:3])  # Limit categories
                    else:
                        categories_str = str(categories)
                    
                    # Ensure metadata values are reasonable length
                    metadata = {
                        "title": title[:200],  # Limit title length
                        "authors": authors_str[:200],  # Limit authors length
                        "date": str(paper.get("date", ""))[:50],
                        "url": paper.get("url", "")[:200],
                        "categories": categories_str[:200]
                    }
                    
                    metadatas.append(metadata)
                    ids.append(f"paper_{i}_{hash(doc_text[:50]) % 100000}")
                    valid_papers.append(paper)
                    
                except Exception as e:
                    logger.warning(f"Skipping paper {i} due to processing error: {e}")
                    continue
            
            if not documents:
                logger.warning("No valid documents found to add")
                return
            
            # Generate embeddings in batches optimized for GPU
            # ChromaDB has a limit of 41,666 embeddings per batch, so we use smaller batches
            # Use larger batches for GPU to maximize throughput
            if self.device and 'cuda' in str(self.device):
                embedding_batch_size = 200  # Larger batches for GPU
                encode_batch_size = 64  # Larger encode batch for GPU
                logger.info("🚀 Using GPU-optimized embedding batch sizes")
            else:
                embedding_batch_size = 100  # Smaller batches for CPU
                encode_batch_size = 32  # Smaller encode batch for CPU
            
            chromadb_batch_size = 1000  # Add to ChromaDB in batches of 1000 (well under 41,666 limit)
            total_added = 0
            
            # Generate embeddings in batches
            all_embeddings = []
            for i in range(0, len(documents), embedding_batch_size):
                batch_docs = documents[i:i + embedding_batch_size]
                try:
                    # Generate embeddings for this batch with GPU-optimized batch size
                    batch_embeddings = self.model.encode(
                        batch_docs,
                        batch_size=encode_batch_size,  # GPU-optimized batch size
                        show_progress_bar=False,
                        convert_to_numpy=True,
                        normalize_embeddings=True,
                        device=self.device  # Explicitly use GPU if available
                    )
                    all_embeddings.extend(batch_embeddings.tolist())
                    logger.debug(f"Generated embeddings for batch {i//embedding_batch_size + 1} ({len(batch_docs)} docs)")
                except Exception as e:
                    logger.error(f"Failed to generate embeddings for batch {i//embedding_batch_size + 1}: {e}")
                    # Add empty embeddings for failed batch
                    all_embeddings.extend([[0.0] * 384] * len(batch_docs))  # Default embedding dimension
                    continue
            
            # Now add to ChromaDB in batches (with embeddings)
            for i in range(0, len(documents), chromadb_batch_size):
                batch_docs = documents[i:i + chromadb_batch_size]
                batch_metas = metadatas[i:i + chromadb_batch_size]
                batch_ids = ids[i:i + chromadb_batch_size]
                batch_embeddings = all_embeddings[i:i + chromadb_batch_size]
                
                try:
                    # Use add with embeddings to avoid ChromaDB generating them
                    self.vector_store.add(
                        documents=batch_docs,
                        metadatas=batch_metas,
                        ids=batch_ids,
                        embeddings=batch_embeddings
                    )
                    total_added += len(batch_docs)
                    logger.debug(f"Added batch {i//chromadb_batch_size + 1} to vector store ({len(batch_docs)} docs)")
                    
                except Exception as e:
                    logger.error(f"Failed to add batch {i//chromadb_batch_size + 1} to ChromaDB: {e}")
                    # Try without embeddings (let ChromaDB generate them)
                    try:
                        self.vector_store.add(
                            documents=batch_docs,
                            metadatas=batch_metas,
                            ids=batch_ids
                        )
                        total_added += len(batch_docs)
                        logger.info(f"Added batch {i//chromadb_batch_size + 1} without pre-computed embeddings")
                    except Exception as e2:
                        logger.error(f"Failed to add batch even without embeddings: {e2}")
                        continue
            
            logger.info(f"✅ Added {total_added} papers to vector store")
            
        except Exception as e:
            logger.error(f"❌ Error adding papers to store: {e}")
    
    def semantic_search(self, query: str, k: int = 10) -> List[Dict]:
        """Perform semantic search with improved error handling"""
        if not self.is_available():
            logger.warning("⚠️ Embeddings system not available for search")
            return []
        
        try:
            # Clean and validate query
            query = query.strip()
            if not query:
                logger.warning("Empty search query")
                return []
            
            # Limit results to reasonable number
            k = max(1, min(k, 50))
            
            results = self.vector_store.query(
                query_texts=[query],
                n_results=k
            )
            
            papers = []
            if results and results.get('documents') and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    try:
                        metadata = results['metadatas'][0][i] if results.get('metadatas') else {}
                        distance = results['distances'][0][i] if results.get('distances') else 0.5
                        
                        paper = {
                            'document': doc,
                            'metadata': metadata,
                            'distance': float(distance),
                            'relevance_score': 1.0 - float(distance)
                        }
                        papers.append(paper)
                    except (IndexError, ValueError, TypeError) as e:
                        logger.warning(f"Error processing search result {i}: {e}")
                        continue
            
            logger.info(f"Found {len(papers)} relevant papers for query: '{query[:50]}...'")
            return papers
            
        except Exception as e:
            logger.error(f"❌ Semantic search error: {e}")
            return []
    
    def get_collection_info(self) -> Dict:
        """Get information about the vector store collection"""
        if not self.is_available():
            return {"status": "unavailable", "count": 0}
        
        try:
            data = self.vector_store.get()
            count = len(data.get('ids', [])) if data else 0
            
            return {
                "status": "available",
                "count": count,
                "collection_name": "research_papers"
            }
            
        except Exception as e:
            logger.error(f"Error getting collection info: {e}")
            return {"status": "error", "count": 0, "error": str(e)}
