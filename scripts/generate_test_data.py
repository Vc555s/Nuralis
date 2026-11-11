#!/usr/bin/env python3
"""
Helper script to generate test data for embedding throughput test
Fetches abstracts from arXiv and saves them in JSON format
"""
import json
import argparse
from pathlib import Path
from typing import Dict
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.config_loader import load_config
from src.data.fetchers.arxiv_fetcher import ArxivFetcher
from src.utils.logging_utils import logger


def generate_test_abstracts(
    config: Dict,
    query: str,
    max_results: int,
    output_file: str
):
    """
    Generate test abstracts from arXiv
    
    Args:
        config: Application config
        query: Search query
        max_results: Maximum number of papers to fetch
        output_file: Output JSON file path
    """
    print(f"🧠 Generating Test Data")
    print(f"   Query: {query}")
    print(f"   Max results: {max_results}")
    print()
    
    # Initialize fetcher
    fetcher = ArxivFetcher(config)
    
    # Fetch papers
    print("Fetching papers from arXiv...")
    papers = fetcher.search_with_date_distribution(
        query=query,
        start_year=2020,
        end_year=2024
    )
    
    if not papers:
        print("❌ No papers fetched")
        return False
    
    print(f"✅ Fetched {len(papers)} papers")
    
    # Extract abstracts
    abstracts = []
    for paper in papers[:max_results]:
        abstract = paper.get('abstract', '')
        if abstract and len(abstract) > 50:  # Filter very short abstracts
            abstracts.append({
                "abstract": abstract,
                "title": paper.get('title', ''),
                "url": paper.get('url', ''),
                "date": str(paper.get('date', ''))
            })
    
    print(f"✅ Extracted {len(abstracts)} valid abstracts")
    
    # Save to file
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Save in multiple formats for flexibility
    with open(output_file, 'w') as f:
        json.dump(abstracts, f, indent=2)
    
    # Also save as simple list of abstracts
    abstracts_only_file = output_file.replace('.json', '_abstracts_only.json')
    abstracts_only = [item["abstract"] for item in abstracts]
    with open(abstracts_only_file, 'w') as f:
        json.dump(abstracts_only, f, indent=2)
    
    print(f"✅ Saved to: {output_file}")
    print(f"✅ Also saved abstracts-only to: {abstracts_only_file}")
    
    return True


def main():
    parser = argparse.ArgumentParser(description="Generate test data for embedding throughput test")
    parser.add_argument("--query", default="machine learning", help="Search query")
    parser.add_argument("--max-results", type=int, default=2000, help="Maximum number of papers")
    parser.add_argument("--output", default="test_results/data/embeddings/abstracts_2k.json", help="Output file")
    parser.add_argument("--config", default="config/main_config.yaml", help="Config file path")
    
    args = parser.parse_args()
    
    # Load config
    try:
        config = load_config(args.config)
    except Exception as e:
        print(f"❌ Failed to load config: {e}")
        return 1
    
    # Generate test data
    success = generate_test_abstracts(
        config=config,
        query=args.query,
        max_results=args.max_results,
        output_file=args.output
    )
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

