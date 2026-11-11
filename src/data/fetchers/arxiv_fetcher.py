# src/data/fetchers/arxiv_fetcher.py
import arxiv
from typing import List, Dict
from datetime import datetime, timedelta
from src.utils.logging_utils import logger
import time
import random

class ArxivFetcher:
    def __init__(self, config: Dict):
        self.config = config
        self.max_results = config["data_sources"]["arxiv"]["max_results"]
        self.categories = config["data_sources"]["arxiv"]["categories"]
        self.client = arxiv.Client()
    
    def search_with_date_distribution(self, query: str, start_year: int = 2015, end_year: int = None, per_year: int = None) -> List[Dict]:
        """Fetch papers with better temporal distribution and error handling
        
        Args:
            query: Search query
            start_year: Start year
            end_year: End year (defaults to current year)
            per_year: Fixed number of papers per year (e.g., 100). If None, divides max_results across years.
        """
        if end_year is None:
            end_year = datetime.now().year
        
        # Validate date range
        if start_year > end_year or start_year < 2000:
            logger.warning(f"Invalid date range: {start_year} to {end_year}")
            return []
        
        papers = []
        span_years = (end_year - start_year + 1)
        
        # If per_year is specified, use it (equal sampling per year)
        if per_year and per_year > 0:
            papers_per_year = per_year
            total_target = per_year * span_years
            logger.info(f"Fetching top-{per_year} papers per year across {span_years} years (total target: {total_target})")
        else:
            # Divide max_results across years
            papers_per_year = max(20, self.max_results // max(1, span_years))
            logger.info(f"Fetching ~{papers_per_year} papers per year from {start_year} to {end_year}")
        
        # Start from recent years for better results
        for year in range(end_year, start_year - 1, -1):
            try:
                year_papers = self._search_by_year(query, year, papers_per_year)
                if year_papers:
                    papers.extend(year_papers)
                    logger.info(f"Year {year}: Found {len(year_papers)} papers")
                
                # Stop if we have enough papers (only if not using fixed per_year)
                if not per_year or per_year <= 0:
                    if len(papers) >= self.max_results:
                        break
                
                # Rate limiting - be respectful to arXiv
                time.sleep(random.uniform(0.5, 1.0))
                
            except Exception as e:
                logger.warning(f"Failed to fetch papers for year {year}: {e}")
                continue
        
        # Sort by date (most recent first)
        papers.sort(key=lambda x: x.get('date', datetime.min), reverse=True)
      
        # If per_year was specified, return all fetched papers; otherwise limit to max_results
        if per_year and per_year > 0:
            final_papers = papers  # Return all fetched papers (per_year * span_years)
        else:
            final_papers = papers[:self.max_results]
        
        logger.info(f"Total papers collected: {len(final_papers)}")
        return final_papers
    
    def _search_by_year(self, query: str, year: int, limit: int) -> List[Dict]:
        """Search papers for a specific year with improved query construction"""
        try:
            # Build search query
            category_filter = ""
            if isinstance(self.categories, list) and len(self.categories) > 0:
                category_filter = " OR ".join(f"cat:{cat}" for cat in self.categories)
            # arXiv date range uses yyyymmddhhmm format
            date_from = f"{year}01010000"
            date_to = f"{year}12312359"
            date_filter = f"submittedDate:[{date_from} TO {date_to}]"
            
            # Try different query formats for better results
            if category_filter:
                query_variations = [
                    f"({query}) AND ({category_filter}) AND {date_filter}",
                    f'ti:"{query}" AND ({category_filter}) AND {date_filter}',
                    f'abs:"{query}" AND ({category_filter}) AND {date_filter}'
                ]
            else:
                # No category constraint: broader search across arXiv
                query_variations = [
                    f"({query}) AND {date_filter}",
                    f'ti:"{query}" AND {date_filter}',
                    f'abs:"{query}" AND {date_filter}'
                ]
            
            all_papers = []
            
            for search_query in query_variations:
                try:
                    search = arxiv.Search(
                        query=search_query,
                        max_results=limit,  # allow overfetch; we'll cap below
                        sort_by=arxiv.SortCriterion.SubmittedDate,
                        sort_order=arxiv.SortOrder.Descending,
                    )
                    
                    papers = []
                    for result in self.client.results(search):
                        # Double-check year bounds
                        pub = result.published
                        if not pub or pub.year != year:
                            continue
                        
                        # Validate paper data
                        if not result.title or not result.summary:
                            continue
                        
                        paper = {
                            "title": result.title.strip(),
                            "abstract": result.summary.strip(),
                            "authors": [author.name for author in result.authors],
                            "date": pub,
                            "url": result.entry_id,
                            "categories": result.categories,
                            "source": "arxiv",
                            "year": pub.year
                        }
                        papers.append(paper)
                        
                        # Stop if we hit the limit for this year overall
                        if len(all_papers) + len(papers) >= limit * 2:  # soft cap to avoid over-looping
                            break
                    
                    all_papers.extend(papers)
                    
                    # Small delay between query variations
                    time.sleep(0.3)
                    
                except Exception as variation_error:
                    logger.warning(f"Query variation failed: {variation_error}")
                    continue
            
            # Remove duplicates based on URL
            unique_papers = {}
            for paper in all_papers:
                url = paper.get('url', '')
                if url and url not in unique_papers:
                    unique_papers[url] = paper
            
            # Keep most recent within the year
            deduped = list(unique_papers.values())
            deduped.sort(key=lambda x: x.get('date') or datetime(year,1,1), reverse=True)
            final_papers = deduped[:limit]
            return final_papers
            
        except Exception as e:
            logger.error(f"Error fetching papers for year {year}: {e}")
            return []
    
    def search(self, query: str) -> List[Dict]:
        """Default search method - backwards compatible"""
        try:
            current_year = datetime.now().year
            return self.search_with_date_distribution(query, current_year - 5, current_year)
        except Exception as e:
            logger.error(f"Default search failed: {e}")
            return []