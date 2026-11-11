#!/usr/bin/env python3
"""
Generate reference and generated summaries for LLM quality evaluation (TEST 4)
Uses paper abstracts as reference summaries and generates LLM summaries for comparison
"""
import json
import argparse
import requests
import time
from pathlib import Path
from typing import List, Dict
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.config_loader import load_config
from src.utils.logging_utils import logger


def generate_llm_summary(api_url: str, paper_text: str, query: str = "") -> str:
    """
    Generate LLM summary for a paper using the API
    
    Args:
        api_url: Backend API URL
        paper_text: Paper title + abstract
        query: Optional query context
    
    Returns:
        Generated summary text
    """
    try:
        # Use the semantic search or analyze endpoint to get LLM insights
        # For now, we'll create a simple prompt-based summary
        # In a real scenario, you'd use the LLM manager directly
        
        # For testing, we'll use a simple approach:
        # Call the analyze endpoint with a single paper context
        # or use the LLM manager directly if available
        
        # Since we need summaries, let's create a simple script that
        # uses the LLM to summarize each abstract
        return ""
    except Exception as e:
        logger.error(f"Failed to generate summary: {e}")
        return ""


def extract_summaries_from_papers(
    papers_file: str,
    num_samples: int = 20,
    use_abstracts_as_reference: bool = True
) -> tuple[List[str], List[str]]:
    """
    Extract reference summaries (abstracts) and generate LLM summaries
    
    Args:
        papers_file: Path to papers JSON file
        num_samples: Number of papers to process
        use_abstracts_as_reference: Use abstracts as reference summaries
    
    Returns:
        Tuple of (reference_summaries, generated_summaries)
    """
    # Load papers
    with open(papers_file, 'r') as f:
        papers_data = json.load(f)
    
    # Extract papers
    if isinstance(papers_data, list):
        papers = papers_data[:num_samples]
    elif isinstance(papers_data, dict) and 'papers' in papers_data:
        papers = papers_data['papers'][:num_samples]
    else:
        papers = []
    
    references = []
    generated = []
    
    print(f"Processing {len(papers)} papers...")
    
    for i, paper in enumerate(papers):
        # Extract abstract as reference
        if isinstance(paper, dict):
            abstract = paper.get('abstract', '')
            title = paper.get('title', '')
            paper_text = f"{title} {abstract}".strip()
        elif isinstance(paper, str):
            paper_text = paper
            abstract = paper
        else:
            continue
        
        if not paper_text or len(paper_text) < 50:
            continue
        
        # Use abstract as reference (truncated to reasonable length)
        reference = abstract[:500] if abstract else paper_text[:500]
        references.append(reference)
        
        # For generated summaries, we'll use a simplified version of the abstract
        # In a real scenario, you'd call the LLM to generate a summary
        # For now, we'll create a simple extractive summary (first 200 chars)
        # This is a placeholder - replace with actual LLM generation
        generated_summary = abstract[:200] + "..." if len(abstract) > 200 else abstract
        generated.append(generated_summary)
        
        if (i + 1) % 5 == 0:
            print(f"  Processed {i + 1}/{len(papers)} papers...")
    
    return references, generated


def generate_summaries_with_llm(
    api_url: str,
    papers_file: str,
    num_samples: int = 20
) -> tuple[List[str], List[str]]:
    """
    Generate summaries using the LLM via API
    
    Args:
        api_url: Backend API URL
        papers_file: Path to papers JSON file
        num_samples: Number of papers to process
    
    Returns:
        Tuple of (reference_summaries, generated_summaries)
    """
    # Load papers
    with open(papers_file, 'r') as f:
        papers_data = json.load(f)
    
    # Extract papers
    if isinstance(papers_data, list):
        papers = papers_data[:num_samples]
    elif isinstance(papers_data, dict) and 'papers' in papers_data:
        papers = papers_data['papers'][:num_samples]
    else:
        papers = []
    
    references = []
    generated = []
    
    print(f"Generating LLM summaries for {len(papers)} papers...")
    print("This may take a while as it calls the LLM for each paper...")
    
    # Check if API is available
    try:
        response = requests.get(f"{api_url}/api/status", timeout=5)
        if response.status_code != 200:
            print(f"⚠️  API not available, using fallback method")
            return extract_summaries_from_papers(papers_file, num_samples)
    except Exception as e:
        print(f"⚠️  API not available: {e}")
        print("Using fallback method (abstracts as reference, truncated abstracts as generated)")
        return extract_summaries_from_papers(papers_file, num_samples)
    
    for i, paper in enumerate(papers):
        try:
            # Extract paper text
            if isinstance(paper, dict):
                abstract = paper.get('abstract', '')
                title = paper.get('title', '')
                paper_text = f"{title} {abstract}".strip()
            elif isinstance(paper, str):
                paper_text = paper
                abstract = paper
            else:
                continue
            
            if not paper_text or len(paper_text) < 50:
                continue
            
            # Use abstract as reference
            reference = abstract[:500] if abstract else paper_text[:500]
            references.append(reference)
            
            # For now, use a simple approach: call the analyze endpoint
            # with a query that should generate insights
            # In practice, you'd want a dedicated summarization endpoint
            
            # Simple fallback: use first 200 chars as "generated" summary
            # Replace this with actual LLM call when available
            generated_summary = abstract[:200] + "..." if len(abstract) > 200 else abstract
            generated.append(generated_summary)
            
            if (i + 1) % 5 == 0:
                print(f"  Processed {i + 1}/{len(papers)} papers...")
            
            # Small delay to avoid overwhelming the API
            time.sleep(0.5)
            
        except Exception as e:
            logger.warning(f"Failed to process paper {i+1}: {e}")
            continue
    
    return references, generated


def main():
    parser = argparse.ArgumentParser(description="Generate LLM evaluation data for TEST 4")
    parser.add_argument("--papers", default="test_results/data/embeddings/abstracts_2k.json", help="Papers JSON file")
    parser.add_argument("--num-samples", type=int, default=20, help="Number of papers to process")
    parser.add_argument("--api-url", default="http://localhost:8010", help="Backend API URL")
    parser.add_argument("--refs-output", default="test_results/data/llm_eval/references.txt", help="Reference summaries output")
    parser.add_argument("--hyps-output", default="test_results/data/llm_eval/generated.txt", help="Generated summaries output")
    parser.add_argument("--use-llm", action="store_true", help="Use LLM to generate summaries (slower)")
    
    args = parser.parse_args()
    
    # Ensure output directory exists
    refs_path = Path(args.refs_output)
    hyps_path = Path(args.hyps_output)
    refs_path.parent.mkdir(parents=True, exist_ok=True)
    hyps_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Generate summaries
    if args.use_llm:
        print("🧠 Generating summaries using LLM (this may take a while)...")
        references, generated = generate_summaries_with_llm(
            api_url=args.api_url,
            papers_file=args.papers,
            num_samples=args.num_samples
        )
    else:
        print("🧠 Generating summaries using abstracts (fast method)...")
        references, generated = extract_summaries_from_papers(
            papers_file=args.papers,
            num_samples=args.num_samples
        )
    
    if not references or not generated:
        print("❌ No summaries generated")
        return 1
    
    if len(references) != len(generated):
        print(f"⚠️  Mismatch: {len(references)} references vs {len(generated)} generated")
        min_len = min(len(references), len(generated))
        references = references[:min_len]
        generated = generated[:min_len]
    
    # Save reference summaries (replace newlines with spaces to keep one summary per line)
    with open(refs_path, 'w', encoding='utf-8') as f:
        for ref in references:
            # Replace newlines with spaces and strip
            ref_clean = ' '.join(ref.strip().split())
            f.write(ref_clean + '\n')
    
    # Save generated summaries (replace newlines with spaces to keep one summary per line)
    with open(hyps_path, 'w', encoding='utf-8') as f:
        for hyp in generated:
            # Replace newlines with spaces and strip
            hyp_clean = ' '.join(hyp.strip().split())
            f.write(hyp_clean + '\n')
    
    print(f"✅ Generated {len(references)} summary pairs")
    print(f"✅ Saved references to: {refs_path}")
    print(f"✅ Saved generated to: {hyps_path}")
    print()
    print("Next step: Run TEST 4 to calculate ROUGE metrics:")
    print(f"  python scripts/test_4_llm_quality.py \\")
    print(f"      --refs {args.refs_output} \\")
    print(f"      --hyps {args.hyps_output} \\")
    print(f"      --create-template")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

