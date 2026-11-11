# src/evaluation/evaluator.py
"""
Evaluation framework for quality assurance
"""
from typing import List, Dict, Optional, Tuple, Any
import numpy as np
from rouge_score import rouge_scorer
from src.utils.logging_utils import logger


class Evaluator:
    """Evaluation framework for research analysis quality"""
    
    def __init__(self):
        self.rouge_scorer = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)
    
    def evaluate_retrieval(
        self,
        query: str,
        retrieved_papers: List[Dict],
        ground_truth_papers: List[str],  # List of relevant paper URLs/IDs
        k: int = 10
    ) -> Dict[str, float]:
        """
        Evaluate retrieval quality
        
        Returns:
            Dict with precision@k, recall@k, MRR
        """
        if not retrieved_papers or not ground_truth_papers:
            return {
                "precision@k": 0.0,
                "recall@k": 0.0,
                "mrr": 0.0
            }
        
        # Get retrieved URLs
        retrieved_urls = [
            paper.get("url", paper.get("metadata", {}).get("url", ""))
            for paper in retrieved_papers[:k]
        ]
        
        # Calculate metrics
        relevant_retrieved = len(set(retrieved_urls) & set(ground_truth_papers))
        
        precision = relevant_retrieved / len(retrieved_urls) if retrieved_urls else 0.0
        recall = relevant_retrieved / len(ground_truth_papers) if ground_truth_papers else 0.0
        
        # MRR (Mean Reciprocal Rank)
        mrr = 0.0
        for i, url in enumerate(retrieved_urls, 1):
            if url in ground_truth_papers:
                mrr = 1.0 / i
                break
        
        return {
            "precision@k": precision,
            "recall@k": recall,
            "mrr": mrr,
            "relevant_retrieved": relevant_retrieved,
            "total_retrieved": len(retrieved_urls),
            "total_relevant": len(ground_truth_papers)
        }
    
    def evaluate_summary(
        self,
        generated_summary: str,
        reference_summary: str
    ) -> Dict[str, float]:
        """
        Evaluate summary quality using ROUGE scores
        
        Returns:
            Dict with ROUGE-1, ROUGE-2, ROUGE-L scores
        """
        if not generated_summary or not reference_summary:
            return {
                "rouge1": 0.0,
                "rouge2": 0.0,
                "rougeL": 0.0
            }
        
        scores = self.rouge_scorer.score(reference_summary, generated_summary)
        
        return {
            "rouge1": scores['rouge1'].fmeasure,
            "rouge2": scores['rouge2'].fmeasure,
            "rougeL": scores['rougeL'].fmeasure
        }
    
    def evaluate_semantic_similarity(
        self,
        generated_text: str,
        reference_text: str,
        embedding_model
    ) -> float:
        """
        Evaluate semantic similarity using embeddings
        
        Returns:
            Cosine similarity score (0-1)
        """
        try:
            gen_emb = embedding_model.encode(generated_text, convert_to_numpy=True)
            ref_emb = embedding_model.encode(reference_text, convert_to_numpy=True)
            
            # Cosine similarity
            similarity = np.dot(gen_emb, ref_emb) / (
                np.linalg.norm(gen_emb) * np.linalg.norm(ref_emb)
            )
            
            return float(similarity)
        except Exception as e:
            logger.error(f"Semantic similarity evaluation failed: {e}")
            return 0.0
    
    def run_evaluation_suite(
        self,
        test_cases: List[Dict],
        embedding_model=None
    ) -> Dict[str, Any]:
        """
        Run full evaluation suite on test cases
        
        Test case format:
        {
            "query": "transformer attention",
            "retrieved_papers": [...],
            "ground_truth_papers": ["url1", "url2"],
            "generated_summary": "...",
            "reference_summary": "..."
        }
        """
        results = {
            "retrieval_metrics": [],
            "summary_metrics": [],
            "overall": {}
        }
        
        for test_case in test_cases:
            # Evaluate retrieval
            if "retrieved_papers" in test_case and "ground_truth_papers" in test_case:
                retrieval_metrics = self.evaluate_retrieval(
                    query=test_case.get("query", ""),
                    retrieved_papers=test_case["retrieved_papers"],
                    ground_truth_papers=test_case["ground_truth_papers"]
                )
                results["retrieval_metrics"].append(retrieval_metrics)
            
            # Evaluate summary
            if "generated_summary" in test_case and "reference_summary" in test_case:
                summary_metrics = self.evaluate_summary(
                    generated_summary=test_case["generated_summary"],
                    reference_summary=test_case["reference_summary"]
                )
                results["summary_metrics"].append(summary_metrics)
        
        # Calculate averages
        if results["retrieval_metrics"]:
            results["overall"]["avg_precision@k"] = np.mean([
                m["precision@k"] for m in results["retrieval_metrics"]
            ])
            results["overall"]["avg_recall@k"] = np.mean([
                m["recall@k"] for m in results["retrieval_metrics"]
            ])
            results["overall"]["avg_mrr"] = np.mean([
                m["mrr"] for m in results["retrieval_metrics"]
            ])
        
        if results["summary_metrics"]:
            results["overall"]["avg_rouge1"] = np.mean([
                m["rouge1"] for m in results["summary_metrics"]
            ])
            results["overall"]["avg_rouge2"] = np.mean([
                m["rouge2"] for m in results["summary_metrics"]
            ])
            results["overall"]["avg_rougeL"] = np.mean([
                m["rougeL"] for m in results["summary_metrics"]
            ])
        
        return results


