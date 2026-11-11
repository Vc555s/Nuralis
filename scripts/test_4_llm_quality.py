#!/usr/bin/env python3
"""
TEST 4: LLM Output Quality Evaluation
Assesses the coherence, factual grounding, and utility of AI-generated summaries
using ROUGE metrics and human evaluation.
"""
import json
import argparse
from pathlib import Path
from typing import List, Dict
import sys
import os
import csv

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.evaluation.evaluator import Evaluator
from src.utils.logging_utils import logger


def load_text_file(file_path: str) -> List[str]:
    """Load text file, one summary per line"""
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f if line.strip()]
    return lines


def evaluate_rouge(
    references: List[str],
    generated: List[str],
    output_file: str
) -> Dict:
    """
    Evaluate ROUGE scores for generated summaries
    
    Args:
        references: List of reference summaries
        generated: List of generated summaries
        output_file: Output file path
    
    Returns:
        Dict with ROUGE metrics
    """
    if len(references) != len(generated):
        return {"error": f"Mismatch: {len(references)} references vs {len(generated)} generated"}
    
    print(f"🧠 Running ROUGE Evaluation")
    print(f"   Samples: {len(references)}")
    print()
    
    evaluator = Evaluator()
    
    results = {
        "test_name": "LLM Output Quality Evaluation (ROUGE)",
        "total_samples": len(references),
        "samples": [],
        "overall_metrics": {}
    }
    
    all_rouge1 = []
    all_rouge2 = []
    all_rougeL = []
    
    for i, (ref, gen) in enumerate(zip(references, generated)):
        try:
            metrics = evaluator.evaluate_summary(
                generated_summary=gen,
                reference_summary=ref
            )
            
            all_rouge1.append(metrics["rouge1"])
            all_rouge2.append(metrics["rouge2"])
            all_rougeL.append(metrics["rougeL"])
            
            results["samples"].append({
                "sample_id": i + 1,
                "rouge1": round(metrics["rouge1"], 4),
                "rouge2": round(metrics["rouge2"], 4),
                "rougeL": round(metrics["rougeL"], 4)
            })
            
            if (i + 1) % 5 == 0:
                print(f"Processed {i + 1}/{len(references)} samples...")
                
        except Exception as e:
            print(f"❌ Error evaluating sample {i+1}: {e}")
            logger.error(f"ROUGE evaluation failed for sample {i+1}: {e}")
            continue
    
    # Calculate overall metrics
    if all_rouge1:
        results["overall_metrics"] = {
            "avg_rouge1": round(sum(all_rouge1) / len(all_rouge1), 4),
            "avg_rouge2": round(sum(all_rouge2) / len(all_rouge2), 4),
            "avg_rougeL": round(sum(all_rougeL) / len(all_rougeL), 4),
            "std_rouge1": round(
                (sum((r - sum(all_rouge1)/len(all_rouge1))**2 for r in all_rouge1) / len(all_rouge1))**0.5,
                4
            ) if len(all_rouge1) > 1 else 0.0,
            "std_rouge2": round(
                (sum((r - sum(all_rouge2)/len(all_rouge2))**2 for r in all_rouge2) / len(all_rouge2))**0.5,
                4
            ) if len(all_rouge2) > 1 else 0.0,
            "std_rougeL": round(
                (sum((r - sum(all_rougeL)/len(all_rougeL))**2 for r in all_rougeL) / len(all_rougeL))**0.5,
                4
            ) if len(all_rougeL) > 1 else 0.0
        }
    else:
        results["overall_metrics"] = {
            "avg_rouge1": 0.0,
            "avg_rouge2": 0.0,
            "avg_rougeL": 0.0,
            "std_rouge1": 0.0,
            "std_rouge2": 0.0,
            "std_rougeL": 0.0
        }
    
    # Save results
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    return results


def create_human_evaluation_template(
    references: List[str],
    generated: List[str],
    output_file: str
):
    """
    Create CSV template for human evaluation
    
    Args:
        references: List of reference summaries
        generated: List of generated summaries
        output_file: Output CSV file path
    """
    if len(references) != len(generated):
        print(f"❌ Mismatch: {len(references)} references vs {len(generated)} generated")
        return
    
    print(f"Creating human evaluation template: {output_file}")
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            "sample_id",
            "reference_summary",
            "generated_summary",
            "coherence",  # 1-5 scale
            "factuality",  # 1-5 scale
            "usefulness"  # 1-5 scale
        ])
        
        for i, (ref, gen) in enumerate(zip(references, generated)):
            writer.writerow([
                i + 1,
                ref[:500],  # Truncate for readability
                gen[:500],
                "",  # To be filled by reviewers
                "",
                ""
            ])
    
    print(f"✅ Template created with {len(references)} samples")
    print("   Reviewers should rate each sample on 1-5 scale:")
    print("   - coherence: How coherent and readable is the summary?")
    print("   - factuality: How factually accurate is the summary?")
    print("   - usefulness: How useful is the summary for understanding the topic?")


def main():
    parser = argparse.ArgumentParser(description="TEST 4: LLM Output Quality Evaluation")
    parser.add_argument("--refs", required=True, help="Reference summaries file (one per line)")
    parser.add_argument("--hyps", required=True, help="Generated summaries file (one per line)")
    parser.add_argument("--output", default="test_results/data/llm_eval/rouge_results.json", help="ROUGE output file")
    parser.add_argument("--human-template", default="test_results/data/llm_eval/human_ratings_template.csv", help="Human evaluation template CSV")
    parser.add_argument("--create-template", action="store_true", help="Create human evaluation template")
    
    args = parser.parse_args()
    
    # Check input files
    if not os.path.exists(args.refs):
        print(f"❌ Reference file not found: {args.refs}")
        return 1
    
    if not os.path.exists(args.hyps):
        print(f"❌ Generated file not found: {args.hyps}")
        return 1
    
    # Load files
    references = load_text_file(args.refs)
    generated = load_text_file(args.hyps)
    
    if not references or not generated:
        print("❌ Empty reference or generated file")
        return 1
    
    # Ensure output directory exists
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Run ROUGE evaluation
    results = evaluate_rouge(
        references=references,
        generated=generated,
        output_file=args.output
    )
    
    if "error" in results:
        print(f"❌ {results['error']}")
        return 1
    
    # Print summary
    print()
    print("=" * 60)
    print("📊 ROUGE Evaluation Results")
    print("=" * 60)
    if "overall_metrics" in results:
        metrics = results["overall_metrics"]
        print(f"Average ROUGE-1: {metrics['avg_rouge1']:.4f} ± {metrics['std_rouge1']:.4f}")
        print(f"Average ROUGE-2: {metrics['avg_rouge2']:.4f} ± {metrics['std_rouge2']:.4f}")
        print(f"Average ROUGE-L: {metrics['avg_rougeL']:.4f} ± {metrics['std_rougeL']:.4f}")
    print(f"Results saved to: {args.output}")
    
    # Create human evaluation template if requested
    if args.create_template:
        human_template_path = Path(args.human_template)
        human_template_path.parent.mkdir(parents=True, exist_ok=True)
        create_human_evaluation_template(
            references=references,
            generated=generated,
            output_file=str(human_template_path)
        )
        print(f"Human evaluation template saved to: {args.human_template}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

