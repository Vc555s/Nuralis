# src/data/fetchers/arxiv_fetcher_optimized.py
"""
Optimized ArXiv fetcher with parallel processing and better query strategy
"""
import arxiv
from typing import List, Dict, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.utils.logging_utils import logger
from src.data.fetchers.domain_detector import DomainDetector
import time


class OptimizedArxivFetcher:
    """Optimized ArXiv fetcher with parallel processing and smart domain detection"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.max_results = config["data_sources"]["arxiv"]["max_results"]
        # Base categories from config (fallback)
        self.base_categories = config["data_sources"]["arxiv"]["categories"]
        # Enable smart domain detection by default
        self.use_domain_detection = config["data_sources"]["arxiv"].get("use_domain_detection", True)
        page_size = config["data_sources"]["arxiv"].get("page_size", 100)
        self.client = arxiv.Client(
            page_size=page_size,  # Fetch more per page
            delay_seconds=1.0,  # Rate limiting
            num_retries=3
        )
        # Increase parallel workers for faster fetching (respectful to ArXiv)
        # Will be adjusted dynamically based on year range in search_with_date_distribution
        self.max_workers = 5  # Up to 5 parallel workers
    
    def search_with_date_distribution(self, query: str, start_year: int = 2015, end_year: int = None, per_year: int = None, categories: Optional[List[str]] = None) -> List[Dict]:
        """Fetch papers with equal distribution across years
        
        Args:
            query: Search query
            start_year: Start year
            end_year: End year
            per_year: Fixed number of papers per year (e.g., 100). If None, divides max_results across years.
            categories: Optional list of categories to use. If None, uses smart domain detection or config categories.
        """
        if end_year is None:
            end_year = datetime.now().year
        
        # Validate date range
        if start_year > end_year or start_year < 2000:
            logger.warning(f"Invalid date range: {start_year} to {end_year}")
            return []
        
        span_years = (end_year - start_year + 1)
        
        # If per_year is specified, use it (top-N per year behavior)
        if per_year and per_year > 0:
            papers_per_year = per_year
            total_target = per_year * span_years
            logger.info(f"Fetching top-{per_year} papers per year across {span_years} years (total target: {total_target})")
        else:
            # Calculate papers per year for equal distribution
            papers_per_year = max(1, self.max_results // span_years)
            remainder = self.max_results % span_years
            total_target = self.max_results
            logger.info(f"Fetching {self.max_results} papers across {span_years} years ({papers_per_year} per year, {remainder} extra)")
        
        # Smart category selection: use provided, or detect from query, or use config
        if categories:
            selected_categories = categories
            logger.info(f"📋 Using provided categories: {', '.join(selected_categories[:5])}{'...' if len(selected_categories) > 5 else ''}")
        elif self.use_domain_detection:
            # Try LLM-based detection if available, otherwise use keyword-based
            detection_method = self.config.get("data_sources", {}).get("arxiv", {}).get("domain_detection_method", "keyword")
            
            if detection_method == "llm":
                # Try LLM-based reasoning (requires LLM to be loaded)
                try:
                    from src.data.fetchers.llm_domain_detector import LLMDomainDetector
                    # Get LLM manager if available (lazy import to avoid circular dependency)
                    llm_manager = None
                    try:
                        # Try to get LLM from global state or config
                        # This will be set when LLM is loaded
                        import sys
                        if hasattr(sys.modules.get('api_server', None), 'llm_manager'):
                            llm_manager = sys.modules['api_server'].llm_manager
                    except Exception:
                        pass
                    
                    selected_categories = LLMDomainDetector.detect_with_llm(query, llm_manager)
                    logger.info(f"🤖 LLM-based domain detection selected {len(selected_categories)} categories")
                except Exception as e:
                    logger.warning(f"LLM detection failed: {e}, falling back to keyword-based")
                    selected_categories = DomainDetector.detect_domains(query)
            elif detection_method == "api":
                # Use external API (OpenAI, Anthropic, etc.)
                try:
                    from src.data.fetchers.llm_domain_detector import LLMDomainDetector
                    api_key = self.config.get("data_sources", {}).get("arxiv", {}).get("api_key")
                    api_type = self.config.get("data_sources", {}).get("arxiv", {}).get("api_type", "openai")
                    selected_categories = LLMDomainDetector.detect_with_api(query, api_key, api_type)
                    logger.info(f"🌐 API-based domain detection selected {len(selected_categories)} categories")
                except Exception as e:
                    logger.warning(f"API detection failed: {e}, falling back to keyword-based")
                    selected_categories = DomainDetector.detect_domains(query)
            else:
                # Default: keyword-based detection
                selected_categories = DomainDetector.detect_domains(query)
                logger.info(f"🧠 Keyword-based domain detection selected {len(selected_categories)} categories")
        else:
            # Use base categories from config
            selected_categories = self.base_categories
            logger.info(f"📋 Using config categories: {', '.join(selected_categories)}")
        
        # Build category filter
        category_filter = " OR ".join(f"cat:{cat}" for cat in selected_categories)
        
        all_papers = []
        seen_urls = set()
        start_time = time.time()
        
        # Fetch papers per year for equal distribution
        years_to_fetch = list(range(end_year, start_year - 1, -1))
        
        # Calculate remainder if not using fixed per_year
        remainder = 0
        if not per_year or per_year <= 0:
            remainder = self.max_results % span_years
        
        for year_idx, year in enumerate(years_to_fetch):
            # Calculate target for this year
            if per_year and per_year > 0:
                # Fixed per_year: always fetch exactly per_year papers
                target_for_year = per_year
            else:
                # Divide max_results: distribute remainder to recent years
                target_for_year = papers_per_year
                if year_idx < remainder:
                    target_for_year += 1
            
            if target_for_year <= 0:
                continue
            
            try:
                # Build year-specific query
                date_from = f"{year}01010000"
                date_to = f"{year}12312359"
                date_filter = f"submittedDate:[{date_from} TO {date_to}]"
                search_query = f"({query}) AND ({category_filter}) AND {date_filter}"
                
                logger.info(f"Fetching {target_for_year} papers for year {year}...")
                
                search = arxiv.Search(
                    query=search_query,
                    max_results=min(target_for_year * 2, 500),  # Overfetch to account for filtering
                    sort_by=arxiv.SortCriterion.SubmittedDate,
                    sort_order=arxiv.SortOrder.Descending,
                )
                
                year_papers = []
                for result in self.client.results(search):
                    if len(year_papers) >= target_for_year:
                        break
                    
                    # Validate and process paper
                    if not result.title or not result.summary:
                        continue
                    
                    url = result.entry_id
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)
                    
                    pub = result.published
                    if not pub or pub.year != year:
                        continue
                    
                    paper = {
                        "title": result.title.strip(),
                        "abstract": result.summary.strip(),
                        "authors": [author.name for author in result.authors],
                        "date": pub,
                        "url": url,
                        "categories": result.categories,
                        "source": "arxiv",
                        "year": pub.year
                    }
                    year_papers.append(paper)
                
                all_papers.extend(year_papers)
                logger.info(f"Year {year}: Fetched {len(year_papers)}/{target_for_year} papers")
                
                # Check if we have enough total papers (only if not using fixed per_year)
                if not per_year or per_year <= 0:
                    if len(all_papers) >= self.max_results:
                        break
                
                # Small delay to be respectful to ArXiv (only between years)
                if year_idx < len(years_to_fetch) - 1:
                    time.sleep(0.5)
                    
            except Exception as e:
                logger.warning(f"Failed to fetch papers for year {year}: {e}")
                continue
        
        elapsed = time.time() - start_time
        
        # Sort by date (most recent first)
        all_papers.sort(key=lambda x: x.get('date', datetime.min), reverse=True)
        
        # Return papers: if per_year was specified, return all; otherwise limit to max_results
        if per_year and per_year > 0:
            final_papers = all_papers  # Return all fetched papers (per_year * span_years)
        else:
            final_papers = all_papers[:self.max_results]  # Limit to max_results
        
        # Log year distribution
        year_counts = {}
        for paper in final_papers:
            year = paper.get('year')
            if year:
                year_counts[year] = year_counts.get(year, 0) + 1
        
        logger.info(f"✅ Fetched {len(final_papers)} papers in {elapsed:.1f}s")
        logger.info(f"Year distribution: {dict(sorted(year_counts.items()))}")
        
        return final_papers
    
    def search(self, query: str) -> List[Dict]:
        """Default search method"""
        try:
            current_year = datetime.now().year
            return self.search_with_date_distribution(query, current_year - 5, current_year)
        except Exception as e:
            logger.error(f"Default search failed: {e}")
            return []

