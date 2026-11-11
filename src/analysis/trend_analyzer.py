# src/analysis/trend_analyzer.py
import pandas as pd
import numpy as np
from collections import defaultdict, Counter
from typing import Dict, List
import re
from datetime import datetime
from src.utils.logging_utils import logger

class TrendAnalyzer:
    def __init__(self, config: Dict):
        self.config = config
        self.ml_keywords = self._get_ml_keywords()
        self.min_frequency = config["analysis"]["trends"]["min_frequency"]
        self.max_keywords = config["analysis"]["trends"]["max_keywords"]
    
    def _get_ml_keywords(self) -> List[str]:
        """Get comprehensive ML/AI keywords"""
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
    
    def analyze_trends(self, papers: List[Dict]) -> Dict:
        """Analyze research trends from papers with robust error handling"""
        try:
            if not papers or len(papers) == 0:
                logger.warning("No papers provided for trend analysis")
                return {
                    "keywords": {},
                    "years": [],
                    "total_papers": 0,
                    "keyword_count": 0,
                    "growth_analysis": {}
                }

            # Extract keywords and years
            trends_data = defaultdict(lambda: defaultdict(int))
            valid_papers = []
            
            for paper in papers:
                year = self._extract_year(paper)
                if not year or year < 2000 or year > datetime.now().year + 1:
                    continue
                
                keywords = self._extract_keywords(paper)
                if keywords:  # Only process papers with valid keywords
                    valid_papers.append(paper)
                    for keyword in keywords:
                        trends_data[keyword][year] += 1
            
            if not valid_papers:
                logger.warning("No valid papers found with extractable keywords")
                return {
                    "keywords": {},
                    "years": [],
                    "total_papers": len(papers),
                    "keyword_count": 0,
                    "growth_analysis": {}
                }
            
            # Filter trends with validation
            filtered_trends = self._filter_trends(trends_data)
            
            if not filtered_trends:
                logger.warning("No trends found after filtering")
                return {
                    "keywords": {},
                    "years": [],
                    "total_papers": len(papers),
                    "keyword_count": 0,
                    "growth_analysis": {}
                }
            
            # Get all years from filtered data
            all_years = set()
            for keyword_data in filtered_trends.values():
                all_years.update(keyword_data.keys())
            
            # Calculate additional metrics
            analysis = {
                "keywords": {k: dict(v) for k, v in filtered_trends.items()},
                "years": sorted(list(all_years)),
                "total_papers": len(papers),
                "keyword_count": len(filtered_trends)
            }
            
            # Add growth analysis with error handling
            try:
                analysis["growth_analysis"] = self._calculate_growth(filtered_trends)
            except Exception as growth_error:
                logger.error(f"Growth analysis failed: {growth_error}")
                analysis["growth_analysis"] = {}

            # Enrichment: rolling averages, index base=100, and year totals
            try:
                enrichment = self._enrich_trends(filtered_trends)
                analysis["enrichment"] = enrichment
            except Exception as enrich_error:
                logger.error(f"Trend enrichment failed: {enrich_error}")
            
            logger.info(f"✅ Analyzed {len(papers)} papers, found {len(filtered_trends)} trending keywords")
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
        """Extract year from paper date with robust error handling"""
        try:
            date = paper.get("date")
            if date is None:
                return None
            
            if isinstance(date, datetime):
                return date.year
            elif isinstance(date, str):
                # Handle various string formats
                if len(date) >= 4 and date[:4].isdigit():
                    year = int(date[:4])
                    return year if 2000 <= year <= datetime.now().year + 1 else None
            elif isinstance(date, (int, float)):
                year = int(date)
                return year if 2000 <= year <= datetime.now().year + 1 else None
            
            # Try to convert whatever we got
            year = int(str(date)[:4])
            return year if 2000 <= year <= datetime.now().year + 1 else None
            
        except (ValueError, TypeError, AttributeError):
            return None
    
    def _extract_keywords(self, paper: Dict) -> List[str]:
        """Extract keywords from paper title and abstract"""
        try:
            title = paper.get('title', '')
            abstract = paper.get('abstract', '')
            
            if not title and not abstract:
                return []
            
            text = f"{title} {abstract}".lower()
            
            found_keywords = []
            for keyword in self.ml_keywords:
                if keyword in text:
                    found_keywords.append(keyword)
            
            # Also extract from categories - but filter out ArXiv category codes
            categories = paper.get('categories', [])
            if categories and isinstance(categories, list):
                # Filter out ArXiv category codes (cs.ai, cs.cv, etc.) and keep only meaningful keywords
                arxiv_codes = {'cs.ai', 'cs.cv', 'cs.lg', 'cs.cl', 'cs.cr', 'cs.it', 'stat.ml', 'math.oc'}
                category_keywords = []
                for cat in categories:
                    if isinstance(cat, str):
                        cat_lower = cat.lower()
                        # Skip ArXiv category codes
                        if cat_lower not in arxiv_codes and '.' not in cat_lower:
                            category_keywords.append(cat_lower)
                found_keywords.extend(category_keywords)
            
            return found_keywords
            
        except Exception as e:
            logger.warning(f"Keyword extraction failed for paper: {e}")
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
    
    def _calculate_growth(self, trends_data: Dict) -> Dict:
        """Calculate growth metrics for each keyword with robust error handling"""
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
                
                # Calculate year-over-year growth safely
                values = []
                valid_years = []
                
                for year in years:
                    count = year_counts.get(year, 0)
                    if isinstance(count, (int, float)) and count >= 0:
                        values.append(float(count))
                        valid_years.append(year)
                
                if len(values) < 2 or not valid_years:
                    continue
                
                # Convert to numpy array safely
                values = np.array(values)
                
                # Simple growth rate calculation
                mid_point = len(values) // 2
                if mid_point > 0 and mid_point < len(values):
                    recent_avg = np.mean(values[mid_point:]) if len(values[mid_point:]) > 0 else 0
                    historical_avg = np.mean(values[:mid_point]) if len(values[:mid_point]) > 0 else 0
                    
                    # Avoid division by zero
                    if historical_avg > 0:
                        growth_rate = ((recent_avg - historical_avg) / historical_avg) * 100
                    else:
                        growth_rate = 0.0
                else:
                    growth_rate = 0.0
                
                # Find peak year safely
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
                logger.warning(f"Growth calculation failed for keyword '{keyword}': {e}")
                continue
        
        return growth_analysis

    def _enrich_trends(self, trends_data: Dict) -> Dict:
        """Add rolling averages and normalized index series per keyword, plus year totals."""
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