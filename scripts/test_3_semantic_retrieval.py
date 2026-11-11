#!/usr/bin/env python3
"""
TEST 3: Semantic Retrieval Evaluation
Quantifies retrieval accuracy and relevance of semantic search results
against a manually labeled ground-truth set.
"""
import json
import argparse
from pathlib import Path
from typing import List, Dict
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.config_loader import load_config
from src.ai.embeddings import EmbeddingManager
from src.evaluation.evaluator import Evaluator
from src.utils.logging_utils import logger


def extract_paper_id(url: str) -> str:
    """Extract paper ID from URL (e.g., arxiv ID)"""
    # Try to extract arxiv ID
    if "arxiv.org" in url:
        # Extract ID from URL like https://arxiv.org/abs/2023.01234
        parts = url.split("/")
        for part in parts:
            if part and (part.replace(".", "").replace("-", "").isdigit() or 
                        any(c.isdigit() for c in part)):
                return part
    # Return last part of URL as ID
    return url.split("/")[-1] if "/" in url else url


def normalize_paper_id(paper: Dict) -> str:
    """Extract normalized paper ID from paper dict"""
    # Try URL first
    url = paper.get("url", paper.get("metadata", {}).get("url", ""))
    if url:
        return extract_paper_id(url)
    
    # Try arxiv_id
    arxiv_id = paper.get("arxiv_id", paper.get("metadata", {}).get("arxiv_id", ""))
    if arxiv_id:
        return str(arxiv_id)
    
    # Try entry_id
    entry_id = paper.get("entry_id", paper.get("metadata", {}).get("entry_id", ""))
    if entry_id:
        return extract_paper_id(str(entry_id))
    
    # Fallback to hash of title
    title = paper.get("title", paper.get("metadata", {}).get("title", ""))
    return str(hash(title)) if title else "unknown"


def test_semantic_retrieval(
    config: Dict,
    ground_truth_file: str,
    top_k: int = 10
) -> Dict:
    """
    Test semantic retrieval accuracy
    
    Args:
        config: Application config
        ground_truth_file: Path to ground truth JSON file
        top_k: Number of top results to retrieve
    
    Returns:
        Dict with evaluation metrics
    """
    print("🧠 Running Semantic Retrieval Evaluation")
    print(f"   Ground truth file: {ground_truth_file}")
    print(f"   Top-K: {top_k}")
    print()
    
    # Load ground truth
    with open(ground_truth_file, 'r') as f:
        ground_truth_data = json.load(f)
    
    queries = ground_truth_data.get("queries", [])
    if not queries:
        return {"error": "No queries found in ground truth file"}
    
    print(f"Loaded {len(queries)} test queries")
    
    # Initialize embedding manager
    try:
        print("Loading embedding model...")
        embedding_manager = EmbeddingManager(config)
        if not embedding_manager.is_available():
            raise Exception("Embedding manager not available")
        print("✅ Embedding model loaded")
    except Exception as e:
        print(f"❌ Failed to load embedding model: {e}")
        return {"error": str(e)}
    
    # Initialize evaluator
    evaluator = Evaluator()
    
    # Evaluate each query
    results = {
        "test_name": "Semantic Retrieval Evaluation",
        "top_k": top_k,
        "total_queries": len(queries),
        "queries": []
    }
    
    all_precisions = []
    all_recalls = []
    all_mrrs = []
    
    for i, query_data in enumerate(queries):
        question = query_data.get("question", "")
        expected_ids = query_data.get("expected", [])
        
        if not question or not expected_ids:
            print(f"Query {i+1}: ⚠️  Skipping (missing question or expected IDs)")
            continue
        
        print(f"\nQuery {i+1}/{len(queries)}: {question[:60]}...")
        
        try:
            # Perform semantic search
            retrieved_papers = embedding_manager.semantic_search(question, k=top_k)
            
            # Normalize expected IDs (they might be URLs or IDs)
            expected_normalized = [extract_paper_id(str(eid)) for eid in expected_ids]
            
            # Evaluate retrieval
            metrics = evaluator.evaluate_retrieval(
                query=question,
                retrieved_papers=retrieved_papers,
                ground_truth_papers=expected_normalized,
                k=top_k
            )
            
            # Also check by URL matching (more flexible)
            retrieved_ids = [normalize_paper_id(paper) for paper in retrieved_papers]
            retrieved_urls = [
                paper.get("url", paper.get("metadata", {}).get("url", ""))
                for paper in retrieved_papers
            ]
            
            # Match against expected (try both ID and URL matching)
            relevant_count = 0
            first_relevant_rank = None
            for rank, paper in enumerate(retrieved_papers, 1):
                paper_id = normalize_paper_id(paper)
                paper_url = paper.get("url", paper.get("metadata", {}).get("url", ""))
                
                # Check if this paper matches any expected
                is_relevant = False
                for expected in expected_ids:
                    expected_str = str(expected).lower()
                    if (expected_str in paper_id.lower() or 
                        expected_str in paper_url.lower() or
                        paper_id.lower() in expected_str or
                        any(extract_paper_id(str(expected)) == paper_id for _ in [1])):
                        is_relevant = True
                        break
                
                if is_relevant:
                    relevant_count += 1
                    if first_relevant_rank is None:
                        first_relevant_rank = rank
            
            precision = relevant_count / len(retrieved_papers) if retrieved_papers else 0.0
            recall = relevant_count / len(expected_ids) if expected_ids else 0.0
            mrr = 1.0 / first_relevant_rank if first_relevant_rank else 0.0
            
            all_precisions.append(precision)
            all_recalls.append(recall)
            all_mrrs.append(mrr)
            
            query_result = {
                "query": question,
                "expected_count": len(expected_ids),
                "retrieved_count": len(retrieved_papers),
                "relevant_retrieved": relevant_count,
                "precision@k": round(precision, 4),
                "recall@k": round(recall, 4),
                "mrr": round(mrr, 4),
                "first_relevant_rank": first_relevant_rank,
                "retrieved_ids": retrieved_ids[:5]  # First 5 for inspection
            }
            
            results["queries"].append(query_result)
            
            print(f"  Precision@10: {precision:.3f}")
            print(f"  Recall@10: {recall:.3f}")
            print(f"  MRR: {mrr:.3f}")
            print(f"  Relevant found: {relevant_count}/{len(expected_ids)}")
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
            logger.error(f"Query evaluation failed: {e}")
            continue
    
    # Calculate overall metrics
    if all_precisions:
        results["overall_metrics"] = {
            "avg_precision@k": round(sum(all_precisions) / len(all_precisions), 4),
            "avg_recall@k": round(sum(all_recalls) / len(all_recalls), 4),
            "avg_mrr": round(sum(all_mrrs) / len(all_mrrs), 4),
            "std_precision": round(
                (sum((p - sum(all_precisions)/len(all_precisions))**2 for p in all_precisions) / len(all_precisions))**0.5,
                4
            ) if len(all_precisions) > 1 else 0.0
        }
    else:
        results["overall_metrics"] = {
            "avg_precision@k": 0.0,
            "avg_recall@k": 0.0,
            "avg_mrr": 0.0,
            "std_precision": 0.0
        }
    
    return results


def main():
    parser = argparse.ArgumentParser(description="TEST 3: Semantic Retrieval Evaluation")
    parser.add_argument("--input", required=True, help="Ground truth JSON file")
    parser.add_argument("--top-k", type=int, default=10, help="Number of top results to retrieve")
    parser.add_argument("--output", default="test_results/data/relevance/relevance_eval.json", help="Output file")
    parser.add_argument("--config", default="config/main_config.yaml", help="Config file path")
    
    args = parser.parse_args()
    
    # Load config
    try:
        config = load_config(args.config)
    except Exception as e:
        print(f"❌ Failed to load config: {e}")
        return 1
    
    # Check input file
    if not os.path.exists(args.input):
        print(f"❌ Ground truth file not found: {args.input}")
        print("   Create a ground truth file with the following format:")
        print('   {"queries": [{"question": "...", "expected": ["id1", "id2"]}]}')
        return 1
    
    # Ensure output directory exists
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Run test
    results = test_semantic_retrieval(
        config=config,
        ground_truth_file=args.input,
        top_k=args.top_k
    )
    
    if "error" in results:
        print(f"❌ {results['error']}")
        return 1
    
    # Save results
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Print summary
    print()
    print("=" * 60)
    print("📊 Semantic Retrieval Evaluation Results")
    print("=" * 60)
    if "overall_metrics" in results:
        metrics = results["overall_metrics"]
        print(f"Average Precision@10: {metrics['avg_precision@k']:.4f} ± {metrics['std_precision']:.4f}")
        print(f"Average Recall@10: {metrics['avg_recall@k']:.4f}")
        print(f"Average MRR: {metrics['avg_mrr']:.4f}")
    print(f"Results saved to: {output_path}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

