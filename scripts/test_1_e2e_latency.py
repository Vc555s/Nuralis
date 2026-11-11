#!/usr/bin/env python3
"""
TEST 1: End-to-End Latency Evaluation
Measures total time from user query submission → backend API processing → response delivery
"""
import time
import requests
import json
import argparse
from pathlib import Path
from typing import List, Dict
from statistics import mean, stdev
import sys


def test_e2e_latency(
    api_url: str,
    query: str,
    start_year: int,
    end_year: int,
    max_papers: int,
    num_runs: int = 5,
    enable_llm: bool = True,
    enable_embeddings: bool = True
) -> Dict:
    """
    Run end-to-end latency test
    
    Args:
        api_url: Backend API URL
        query: Research query
        start_year: Start year
        end_year: End year
        max_papers: Maximum papers to fetch
        num_runs: Number of test runs
        enable_llm: Enable LLM processing
        enable_embeddings: Enable embeddings generation
    
    Returns:
        Dict with latency statistics
    """
    latencies = []
    errors = []
    
    payload = {
        "query": query,
        "startYear": start_year,
        "endYear": end_year,
        "maxPapers": max_papers,
        "enableLLM": enable_llm,
        "enableEmbeddings": enable_embeddings
    }
    
    print(f"🧠 Running E2E Latency Test ({num_runs} runs)")
    print(f"   Query: {query}")
    print(f"   Years: {start_year}-{end_year}")
    print(f"   Max Papers: {max_papers}")
    print(f"   LLM: {enable_llm}, Embeddings: {enable_embeddings}")
    print()
    
    for i in range(num_runs):
        try:
            print(f"Run {i+1}/{num_runs}...", end=" ", flush=True)
            t0 = time.time()
            
            response = requests.post(
                f"{api_url}/api/analyze",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=600  # 10 minute timeout
            )
            
            t1 = time.time()
            latency = t1 - t0
            
            if response.status_code == 200:
                data = response.json()
                latencies.append(latency)
                print(f"✅ {latency:.2f}s")
                
                # Log paper count for verification
                papers_count = len(data.get("papers", []))
                print(f"   Papers fetched: {papers_count}")
            else:
                error_msg = f"HTTP {response.status_code}: {response.text[:100]}"
                errors.append(error_msg)
                print(f"❌ Failed: {error_msg}")
                
        except requests.exceptions.Timeout:
            error_msg = "Request timeout (>600s)"
            errors.append(error_msg)
            print(f"❌ {error_msg}")
        except Exception as e:
            error_msg = str(e)
            errors.append(error_msg)
            print(f"❌ Error: {error_msg}")
        
        # Small delay between runs
        if i < num_runs - 1:
            time.sleep(2)
    
    # Calculate statistics
    if latencies:
        avg_latency = mean(latencies)
        std_latency = stdev(latencies) if len(latencies) > 1 else 0.0
        min_latency = min(latencies)
        max_latency = max(latencies)
    else:
        avg_latency = std_latency = min_latency = max_latency = 0.0
    
    results = {
        "test_name": "End-to-End Latency Evaluation",
        "query": query,
        "start_year": start_year,
        "end_year": end_year,
        "max_papers": max_papers,
        "num_runs": num_runs,
        "enable_llm": enable_llm,
        "enable_embeddings": enable_embeddings,
        "latencies": latencies,
        "statistics": {
            "mean": round(avg_latency, 3),
            "std": round(std_latency, 3),
            "min": round(min_latency, 3),
            "max": round(max_latency, 3),
            "median": round(sorted(latencies)[len(latencies)//2], 3) if latencies else 0.0
        },
        "errors": errors,
        "success_rate": len(latencies) / num_runs if num_runs > 0 else 0.0
    }
    
    return results


def main():
    parser = argparse.ArgumentParser(description="TEST 1: End-to-End Latency Evaluation")
    parser.add_argument("--api-url", default="http://localhost:8010", help="Backend API URL")
    parser.add_argument("--query", default="transformer attention mechanisms", help="Research query")
    parser.add_argument("--start-year", type=int, default=2020, help="Start year")
    parser.add_argument("--end-year", type=int, default=2024, help="End year")
    parser.add_argument("--max-papers", type=int, default=500, help="Maximum papers")
    parser.add_argument("--num-runs", type=int, default=5, help="Number of test runs")
    parser.add_argument("--enable-llm", action="store_true", default=True, help="Enable LLM")
    parser.add_argument("--disable-llm", action="store_false", dest="enable_llm", help="Disable LLM")
    parser.add_argument("--enable-embeddings", action="store_true", default=True, help="Enable embeddings")
    parser.add_argument("--disable-embeddings", action="store_false", dest="enable_embeddings", help="Disable embeddings")
    parser.add_argument("--output", default="test_results/data/e2e/e2e_summary.json", help="Output file")
    
    args = parser.parse_args()
    
    # Ensure output directory exists
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Run test
    results = test_e2e_latency(
        api_url=args.api_url,
        query=args.query,
        start_year=args.start_year,
        end_year=args.end_year,
        max_papers=args.max_papers,
        num_runs=args.num_runs,
        enable_llm=args.enable_llm,
        enable_embeddings=args.enable_embeddings
    )
    
    # Save results
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Print summary
    print()
    print("=" * 60)
    print("📊 E2E Latency Test Results")
    print("=" * 60)
    print(f"Average Latency: {results['statistics']['mean']:.3f}s ± {results['statistics']['std']:.3f}s")
    print(f"Min: {results['statistics']['min']:.3f}s")
    print(f"Max: {results['statistics']['max']:.3f}s")
    print(f"Median: {results['statistics']['median']:.3f}s")
    print(f"Success Rate: {results['success_rate']*100:.1f}%")
    print(f"Results saved to: {output_path}")
    
    if results['errors']:
        print(f"\n⚠️  Errors encountered: {len(results['errors'])}")
        for error in results['errors']:
            print(f"   - {error}")
    
    return 0 if results['success_rate'] > 0.8 else 1


if __name__ == "__main__":
    sys.exit(main())

