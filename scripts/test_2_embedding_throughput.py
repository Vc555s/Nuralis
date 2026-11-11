#!/usr/bin/env python3
"""
TEST 2: Embedding Throughput Analysis
Determines how quickly the Embedding Manager encodes research papers on GPU
across different batch sizes.
"""
import time
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
from src.utils.logging_utils import logger


def load_abstracts(input_file: str) -> List[str]:
    """Load abstracts from JSON file"""
    with open(input_file, 'r') as f:
        data = json.load(f)
    
    abstracts = []
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                abstract = item.get('abstract', item.get('summary', ''))
                if abstract:
                    abstracts.append(abstract)
            elif isinstance(item, str):
                abstracts.append(item)
    elif isinstance(data, dict):
        if 'abstracts' in data:
            abstracts = data['abstracts']
        elif 'papers' in data:
            for paper in data['papers']:
                if isinstance(paper, dict):
                    abstract = paper.get('abstract', '')
                    if abstract:
                        abstracts.append(abstract)
    
    return abstracts


def test_embedding_throughput(
    config: Dict,
    abstracts: List[str],
    batch_sizes: List[int],
    num_runs: int = 3
) -> Dict:
    """
    Test embedding throughput for different batch sizes
    
    Args:
        config: Application config
        abstracts: List of abstract texts
        batch_sizes: List of batch sizes to test
        num_runs: Number of runs per batch size
    
    Returns:
        Dict with throughput results
    """
    print("🧠 Running Embedding Throughput Test")
    print(f"   Total abstracts: {len(abstracts)}")
    print(f"   Batch sizes: {batch_sizes}")
    print(f"   Runs per batch size: {num_runs}")
    print()
    
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
    
    results = {
        "test_name": "Embedding Throughput Analysis",
        "total_abstracts": len(abstracts),
        "batch_sizes": batch_sizes,
        "throughput_results": []
    }
    
    for batch_size in batch_sizes:
        print(f"\nTesting batch size: {batch_size}")
        batch_latencies = []
        batch_throughputs = []
        
        for run in range(num_runs):
            try:
                # Use all abstracts for testing (or a large subset)
                # The batch_size parameter controls internal GPU processing batch size
                test_abstracts = abstracts  # Use all abstracts
                total_docs = len(test_abstracts)
                
                if total_docs == 0:
                    print(f"  Run {run+1}/{num_runs}: ⚠️  No abstracts to process")
                    continue
                
                # Time the encoding with different internal batch sizes
                start_time = time.time()
                
                # Encode all abstracts with the specified internal batch size
                # This tests how the internal batch size affects GPU throughput
                embeddings = embedding_manager.model.encode(
                    test_abstracts,
                    batch_size=batch_size,  # Internal batch size for GPU processing
                    show_progress_bar=False,
                    convert_to_numpy=True,
                    normalize_embeddings=True,
                    device=embedding_manager.device
                )
                
                end_time = time.time()
                latency = end_time - start_time
                
                # Calculate throughput (documents per second)
                throughput = total_docs / latency if latency > 0 else 0
                
                batch_latencies.append(latency)
                batch_throughputs.append(throughput)
                
                print(f"  Run {run+1}/{num_runs}: {latency:.2f}s ({throughput:.1f} docs/s)")
                
            except Exception as e:
                print(f"  Run {run+1}/{num_runs}: ❌ Error - {e}")
                import traceback
                traceback.print_exc()
                continue
        
        if batch_latencies:
            avg_latency = sum(batch_latencies) / len(batch_latencies)
            avg_throughput = sum(batch_throughputs) / len(batch_throughputs)
            std_throughput = (
                (sum((t - avg_throughput) ** 2 for t in batch_throughputs) / len(batch_throughputs)) ** 0.5
                if len(batch_throughputs) > 1 else 0.0
            )
            
            results["throughput_results"].append({
                "batch_size": batch_size,
                "avg_latency_seconds": round(avg_latency, 3),
                "avg_throughput_docs_per_sec": round(avg_throughput, 2),
                "std_throughput": round(std_throughput, 2),
                "min_throughput": round(min(batch_throughputs), 2),
                "max_throughput": round(max(batch_throughputs), 2),
                "latencies": [round(l, 3) for l in batch_latencies],
                "throughputs": [round(t, 2) for t in batch_throughputs]
            })
            
            print(f"  Average: {avg_throughput:.1f} ± {std_throughput:.1f} docs/s")
    
    return results


def main():
    parser = argparse.ArgumentParser(description="TEST 2: Embedding Throughput Analysis")
    parser.add_argument("--input", required=True, help="Input JSON file with abstracts")
    parser.add_argument("--batches", type=int, nargs="+", default=[8, 16, 32, 64], help="Batch sizes to test")
    parser.add_argument("--num-runs", type=int, default=3, help="Number of runs per batch size")
    parser.add_argument("--output", default="test_results/data/embeddings/emb_throughput.json", help="Output file")
    parser.add_argument("--config", default="config/main_config.yaml", help="Config file path")
    
    args = parser.parse_args()
    
    # Load config
    try:
        config = load_config(args.config)
    except Exception as e:
        print(f"❌ Failed to load config: {e}")
        return 1
    
    # Load abstracts
    if not os.path.exists(args.input):
        print(f"❌ Input file not found: {args.input}")
        print("   Generate test data first using: python scripts/generate_test_data.py")
        return 1
    
    abstracts = load_abstracts(args.input)
    if not abstracts:
        print(f"❌ No abstracts found in {args.input}")
        return 1
    
    print(f"Loaded {len(abstracts)} abstracts from {args.input}")
    
    # Ensure output directory exists
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Run test
    results = test_embedding_throughput(
        config=config,
        abstracts=abstracts,
        batch_sizes=args.batches,
        num_runs=args.num_runs
    )
    
    if "error" in results:
        return 1
    
    # Save results
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Print summary
    print()
    print("=" * 60)
    print("📊 Embedding Throughput Test Results")
    print("=" * 60)
    for result in results["throughput_results"]:
        print(f"Batch Size {result['batch_size']:3d}: "
              f"{result['avg_throughput_docs_per_sec']:6.1f} ± {result['std_throughput']:5.1f} docs/s")
    print(f"Results saved to: {output_path}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

