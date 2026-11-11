# src/analysis/trend_analyzer_optimized.py
"""
Optimized trend analyzer with parallel processing and domain-agnostic keyword extraction
"""
import pandas as pd
import numpy as np
from collections import defaultdict, Counter
from typing import Dict, List, Optional
import re
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from src.utils.logging_utils import logger
from src.analysis.domain_agnostic_keyword_extractor import DomainAgnosticKeywordExtractor


class OptimizedTrendAnalyzer:
    """Optimized trend analyzer with parallel keyword extraction - DOMAIN AGNOSTIC"""
    
    def __init__(self, config: Dict, query: Optional[str] = None):
        self.config = config
        self.query = query or ""  # Store query for context-aware extraction
        self.min_frequency = config["analysis"]["trends"]["min_frequency"]
        self.max_keywords = config["analysis"]["trends"]["max_keywords"]
        self.max_workers = 4  # Parallel workers for keyword extraction
        
        # Use domain-agnostic extractor instead of hardcoded ML keywords
        self.keyword_extractor = DomainAgnosticKeywordExtractor(query=self.query)
        
        # Legacy ML keywords (kept for backward compatibility, but not used by default)
        self.ml_keywords = self._get_ml_keywords()
        # Use domain-agnostic extraction by default
        self.use_domain_agnostic = config.get("analysis", {}).get("trends", {}).get("use_domain_agnostic_extraction", True)
    
    def _get_ml_keywords(self) -> List[str]:
        """Get comprehensive ML/AI keywords (legacy, for fallback)"""
        return [
            # Core ML/AI
            "machine learning", "deep learning", "artificial intelligence", "neural network",
            "supervised learning", "unsupervised learning", "reinforcement learning",
            "transfer learning", "few-shot learning", "zero-shot learning",
            
            # Architectures
            "transformer", "bert", "gpt", "attention", "cnn", "rnn", "lstm", "gru",
            "autoencoder", "gan", "diffusion", "vae",
            
            # NLP
            "natural language processing", "nlp", "language model", "text classification",
            "sentiment analysis", "machine translation", "question answering",
            
            # Computer Vision  
            "computer vision", "image classification", "object detection", "segmentation",
            
            # Emerging
            "multimodal", "vision-language", "retrieval augmented", "in-context learning",
            "chain of thought", "instruction tuning", "parameter efficient"
        ]
    
    def _extract_keywords_parallel(self, papers: List[Dict]) -> Dict:
        """Extract keywords from papers in parallel - DOMAIN AGNOSTIC"""
        def process_paper(paper):
            year = self._extract_year(paper)
            if not year or year < 2000 or year > datetime.now().year + 1:
                return None, []
            
            keywords = self._extract_keywords(paper)
            return year, keywords
        
        trends_data = defaultdict(lambda: defaultdict(int))
        valid_papers = []
        
        # Process papers in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            results = list(executor.map(process_paper, papers))
        
        for paper, (year, keywords) in zip(papers, results):
            if year and keywords:
                valid_papers.append(paper)
                for keyword in keywords:
                    trends_data[keyword][year] += 1
        
        return trends_data, valid_papers
    
    def analyze_trends(self, papers: List[Dict]) -> Dict:
        """Analyze research trends with parallel processing"""
        try:
            if not papers or len(papers) == 0:
                return {
                    "keywords": {},
                    "years": [],
                    "total_papers": 0,
                    "keyword_count": 0,
                    "growth_analysis": {}
                }
            
            # Parallel keyword extraction
            trends_data, valid_papers = self._extract_keywords_parallel(papers)
            
            if not valid_papers:
                return {
                    "keywords": {},
                    "years": [],
                    "total_papers": len(papers),
                    "keyword_count": 0,
                    "growth_analysis": {}
                }
            
            # Filter trends
            filtered_trends = self._filter_trends(trends_data)
            
            if not filtered_trends:
                return {
                    "keywords": {},
                    "years": [],
                    "total_papers": len(papers),
                    "keyword_count": 0,
                    "growth_analysis": {}
                }
            
            # Get all years
            all_years = set()
            for keyword_data in filtered_trends.values():
                all_years.update(keyword_data.keys())
            
            # Calculate metrics
            analysis = {
                "keywords": {k: dict(v) for k, v in filtered_trends.items()},
                "years": sorted(list(all_years)),
                "total_papers": len(papers),
                "keyword_count": len(filtered_trends)
            }
            
            # Growth analysis (optimized)
            try:
                analysis["growth_analysis"] = self._calculate_growth_optimized(filtered_trends)
            except Exception as e:
                logger.error(f"Growth analysis failed: {e}")
                analysis["growth_analysis"] = {}
            
            # Enrichment: rolling averages, index base=100, and year totals (for index graphs)
            try:
                enrichment = self._enrich_trends(filtered_trends)
                analysis["enrichment"] = enrichment
            except Exception as e:
                logger.error(f"Trend enrichment failed: {e}")
                analysis["enrichment"] = {
                    "rolling_avg": {},
                    "index_base_100": {},
                    "year_totals": {}
                }
            
            logger.info(f"✅ Analyzed {len(papers)} papers, found {len(filtered_trends)} keywords")
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Trend analysis error: {e}")
            return {
                "keywords": {},
                "years": [],
                "total_papers": len(papers) if papers else 0,
                "keyword_count": 0,
                "growth_analysis": {}
            }
    
    def _extract_year(self, paper: Dict) -> int:
        """Extract year from paper date"""
        try:
            date = paper.get("date")
            if date is None:
                return None
            
            if isinstance(date, datetime):
                return date.year
            elif isinstance(date, str):
                if len(date) >= 4 and date[:4].isdigit():
                    year = int(date[:4])
                    return year if 2000 <= year <= datetime.now().year + 1 else None
            elif isinstance(date, (int, float)):
                year = int(date)
                return year if 2000 <= year <= datetime.now().year + 1 else None
            
            year = int(str(date)[:4])
            return year if 2000 <= year <= datetime.now().year + 1 else None
            
        except (ValueError, TypeError, AttributeError):
            return None
    
    def _extract_keywords(self, paper: Dict) -> List[str]:
        """Extract keywords from paper title and abstract - DOMAIN AGNOSTIC"""
        try:
            title = paper.get('title', '')
            abstract = paper.get('abstract', '')
            
            if not title and not abstract:
                return []
            
            if self.use_domain_agnostic:
                # Use domain-agnostic extractor (extracts from actual content)
                keywords = self.keyword_extractor.extract_keywords(paper, max_keywords=15)
                return keywords
            else:
                # Legacy: use hardcoded ML keywords (for backward compatibility)
                text = f"{title} {abstract}".lower()
                found_keywords = []
                for keyword in self.ml_keywords:
                    if keyword in text:
                        found_keywords.append(keyword)
                
                # Extract from categories
                categories = paper.get('categories', [])
                if categories and isinstance(categories, list):
                    arxiv_codes = {'cs.ai', 'cs.cv', 'cs.lg', 'cs.cl', 'cs.cr', 'cs.it', 'stat.ml', 'math.oc'}
                    for cat in categories:
                        if isinstance(cat, str):
                            cat_lower = cat.lower()
                            if cat_lower not in arxiv_codes and '.' not in cat_lower:
                                found_keywords.append(cat_lower)
                
                return found_keywords
            
        except Exception as e:
            logger.warning(f"Keyword extraction failed: {e}")
            return []
    
    def _filter_trends(self, trends_data: defaultdict) -> Dict:
        """Filter trends by frequency and limit count"""
        try:
            if not trends_data:
                return {}
            
            # Filter by minimum frequency
            filtered = {}
            for keyword, year_counts in trends_data.items():
                if not year_counts:
                    continue
                
                total = sum(year_counts.values())
                if total >= self.min_frequency:
                    filtered[keyword] = year_counts
            
            if not filtered:
                return {}
            
            # Keep only top keywords by total frequency
            if len(filtered) > self.max_keywords:
                sorted_keywords = sorted(
                    filtered.items(),
                    key=lambda x: sum(x[1].values()),
                    reverse=True
                )[:self.max_keywords]
                filtered = dict(sorted_keywords)
            
            return filtered
            
        except Exception as e:
            logger.error(f"Trend filtering failed: {e}")
            return {}
    
    def _calculate_growth_optimized(self, trends_data: Dict) -> Dict:
        """Optimized growth calculation"""
        growth_analysis = {}
        
        if not trends_data:
            return growth_analysis
        
        for keyword, year_counts in trends_data.items():
            try:
                if not year_counts or len(year_counts) < 2:
                    continue
                
                years = sorted([y for y in year_counts.keys() if isinstance(y, (int, str)) and str(y).isdigit()])
                if len(years) < 2:
                    continue
                
                values = []
                valid_years = []
                
                for year in years:
                    count = year_counts.get(year, 0)
                    if isinstance(count, (int, float)) and count >= 0:
                        values.append(float(count))
                        valid_years.append(year)
                
                if len(values) < 2:
                    continue
                
                values = np.array(values)
                
                # Simple growth rate calculation
                mid_point = len(values) // 2
                if mid_point > 0 and mid_point < len(values):
                    recent_avg = np.mean(values[mid_point:]) if len(values[mid_point:]) > 0 else 0
                    historical_avg = np.mean(values[:mid_point]) if len(values[:mid_point]) > 0 else 0
                    
                    if historical_avg > 0:
                        growth_rate = ((recent_avg - historical_avg) / historical_avg) * 100
                    else:
                        growth_rate = 0.0
                else:
                    growth_rate = 0.0
                
                # Find peak year
                if len(values) > 0 and len(valid_years) == len(values):
                    peak_idx = np.argmax(values)
                    peak_year = valid_years[peak_idx]
                else:
                    peak_year = valid_years[0] if valid_years else "Unknown"
                
                growth_analysis[keyword] = {
                    "total_papers": int(np.sum(values)),
                    "growth_rate": round(float(growth_rate), 2),
                    "peak_year": peak_year,
                    "trend": "rising" if growth_rate > 10 else "stable" if growth_rate > -10 else "declining"
                }
                
            except Exception as e:
                continue
        
        return growth_analysis
    
    def _enrich_trends(self, trends_data: Dict) -> Dict:
        """Add rolling averages and normalized index series per keyword, plus year totals (for index graphs)."""
        # Collect all years
        all_years = set()
        for year_counts in trends_data.values():
            all_years.update(year_counts.keys())
        years = sorted(int(y) for y in all_years)
        if not years:
            return {"rolling_avg": {}, "index_base_100": {}, "year_totals": {}}

        rolling_avg = {}
        index_base_100 = {}
        year_totals = {y: 0 for y in years}

        for keyword, year_counts in trends_data.items():
            # Build aligned series
            series = [int(year_counts.get(y, 0)) for y in years]
            for i, y in enumerate(years):
                year_totals[y] += series[i]

            # 3-year rolling average (centered on current with past two years)
            r = []
            for i in range(len(series)):
                window = series[max(0, i-2):i+1]
                r.append(float(np.mean(window)) if window else 0.0)
            rolling_avg[keyword] = {str(y): round(v, 2) for y, v in zip(years, r)}

            # Index base = 100 at first non-zero
            base = next((v for v in series if v > 0), None)
            if base is None:
                idx = [0.0 for _ in series]
            else:
                idx = [float(v) / base * 100.0 if base > 0 else 0.0 for v in series]
            index_base_100[keyword] = {str(y): round(v, 2) for y, v in zip(years, idx)}

        return {
            "rolling_avg": rolling_avg,
            "index_base_100": index_base_100,
            "year_totals": {str(y): int(year_totals[y]) for y in years}
        }

