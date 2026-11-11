# src/ai/advanced_insights.py
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from collections import Counter, defaultdict
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from src.utils.logging_utils import logger
from src.ai.llm_manager import LLMManager
from src.utils.output_filter import OutputFilter
import arxiv

class AdvancedInsightsGenerator:
    def __init__(self, config: Dict, llm_manager: Optional[LLMManager] = None):
        self.config = config
        self.llm_manager = llm_manager
        self.insights_cache = {}
        self.strict_research = bool(config.get("system", {}).get("strict_research_mode", True))
        self.allow_arxiv_heuristic = bool(config.get("insights", {}).get("allow_arxiv_heuristic_fallback", False))

    def _may_use_arxiv_heuristic(self) -> bool:
        """Non-LLM arXiv/keyword summaries — off by default for reproducible research runs."""
        return self.allow_arxiv_heuristic or not self.strict_research
        
    def generate_comprehensive_insights(self, papers: List[Dict], trends_data: Dict, query: str) -> Dict:
        """Generate comprehensive AI-powered insights with parallel execution for speed"""
        try:
            start_time = time.time()
            
            # Parallel execution for independent insights (much faster)
            with ThreadPoolExecutor(max_workers=4) as executor:
                # Submit all independent tasks in parallel
                futures = {
                    "trend_analysis": executor.submit(self._analyze_trends, papers, trends_data),
                    "research_gaps": executor.submit(self._identify_research_gaps, papers, trends_data),
                    "key_findings": executor.submit(self._extract_key_findings, papers, trends_data),
                    "methodology_insights": executor.submit(self._analyze_methodologies, papers),
                    "collaboration_insights": executor.submit(self._analyze_collaborations, papers),
                    "impact_analysis": executor.submit(self._analyze_impact, papers, trends_data),
                }
                
                # Get results as they complete
                results = {}
                for key, future in futures.items():
                    try:
                        results[key] = future.result(timeout=10)  # 10s timeout per task
                    except Exception as e:
                        logger.warning(f"Failed to generate {key}: {e}")
                        results[key] = {"error": str(e)} if key == "trend_analysis" else [{"error": str(e)}]
            
            # LLM-dependent insights (run sequentially but with timeout)
            llm_start = time.time()
            
            exec_summary = self._generate_executive_summary(papers, trends_data, query)
            
            try:
                exec_summary_structured = self._generate_structured_summary_with_citations(papers, trends_data, query)
            except Exception as structured_error:
                logger.warning(f"Structured summary generation failed: {structured_error}")
                if self._may_use_arxiv_heuristic():
                    exec_summary_structured = self._generate_structured_mock_summary_from_arxiv(trends_data, query, exec_summary)
                else:
                    exec_summary_structured = {
                        "paragraphs": [],
                        "coverage_percent": 0.0,
                        "references": [],
                        "error": f"structured_summary_failed: {structured_error}",
                    }
            
            try:
                future_directions = self._predict_future_directions(papers, trends_data)
            except Exception as fd_err:
                if self.strict_research:
                    future_directions = {"error": str(fd_err)}
                else:
                    future_directions = self._get_basic_future_directions(trends_data)
            
            # Recommendations
            recommendations = self._generate_recommendations(papers, trends_data, query)
            
            llm_time = time.time() - llm_start
            total_time = time.time() - start_time
            logger.info(f"⚡ Insights generated in {total_time:.1f}s (LLM: {llm_time:.1f}s)")
            
            insights = {
                "executive_summary": exec_summary,
                "executive_summary_structured": exec_summary_structured,
                **results,
                "future_directions": future_directions,
                "recommendations": recommendations
            }
            
            return insights
            
        except Exception as e:
            logger.error(f"Comprehensive insights generation failed: {e}")
            if self.strict_research:
                return {
                    "error": str(e),
                    "executive_summary": None,
                    "executive_summary_structured": None,
                    "trend_analysis": None,
                    "research_gaps": None,
                    "key_findings": None,
                    "methodology_insights": None,
                    "collaboration_insights": None,
                    "impact_analysis": None,
                    "future_directions": None,
                    "recommendations": None,
                }
            return self._get_fallback_insights(papers, trends_data, query)

    def _generate_structured_summary_with_citations(self, papers: List[Dict], trends_data: Dict, query: str) -> Dict:
        """Return a structured summary with inline citations and references.
        Ensures frontend can render markers and a coverage meter."""
        try:
            total_papers = len(papers)
            years = trends_data.get('years', [])
            growth = trends_data.get('growth_analysis', {})

            # Select up to 6 representative papers to cite: most recent, diverse keywords
            sorted_papers = sorted(papers, key=lambda p: p.get('date'), reverse=True)
            refs = []
            seen_urls = set()
            for p in sorted_papers:
                url = p.get('url') or ''
                if url and url not in seen_urls:
                    refs.append({
                        "title": p.get('title', 'Unknown Title'),
                        "authors": p.get('authors', []),
                        "url": url,
                        "year": p.get('year') or (p.get('date').year if p.get('date') else None)
                    })
                    seen_urls.add(url)
                if len(refs) >= 6:
                    break

            # Build prompt to request two paragraphs and explicit citation indices
            if self.llm_manager and self.llm_manager.is_available():
                top_keywords = list(trends_data.get('keywords', {}).keys())[:10]
                fastest = []
                if growth:
                    fastest = [k for k, _ in sorted(growth.items(), key=lambda x: x[1].get('growth_rate', 0), reverse=True)[:3]]

                numbered_refs = [f"[{i+1}] {r['title']}" for i, r in enumerate(refs)]

                prompt = (
                    "System: You are Nuralis Research Analyst, a senior research analyst. Ensure every non-obvious claim has a citation index.\n"
                    "User: Using the data below, write exactly two concise paragraphs. Use inline citation markers like [1], [2] that map to the provided references.\n\n"
                    f"Topic: {query}\n"
                    f"Total Papers: {total_papers}\n"
                    f"Years: {min(years) if years else 'N/A'}–{max(years) if years else 'N/A'}\n"
                    f"Top Keywords: {', '.join(top_keywords[:8])}\n"
                    f"Fastest Growing Topics: {', '.join(fastest) if fastest else 'N/A'}\n"
                    "References (use indices):\n" + "\n".join(numbered_refs) + "\n\n"
                    "Instructions: Keep claims grounded; prefer quantifiable statements; avoid generic fluff."
                )

                text = self.llm_manager.generate_text(prompt, max_new_tokens=300)
                if text and text.strip() not in ["", "No response generated.", "Model not available for text generation."]:
                    text = OutputFilter.clean_text(text)
                else:
                    text = "Research summary unavailable."
            else:
                text = None
            
            if not text or text == "Research summary unavailable.":
                if not self._may_use_arxiv_heuristic():
                    return {
                        "paragraphs": [],
                        "coverage_percent": 0.0,
                        "references": refs,
                        "error": "llm_unavailable_or_empty_response",
                    }
                mock = self._generate_structured_mock_summary_from_arxiv(trends_data, query)
                return mock

            # Estimate evidence coverage as fraction of sentences containing [n]
            sentences = [s.strip() for s in text.split('.') if s.strip()]
            cited = sum(1 for s in sentences if '[' in s and ']' in s)
            coverage = round(100.0 * cited / max(1, len(sentences)), 1)

            return {
                "paragraphs": text.split('\n\n')[:2],
                "coverage_percent": coverage,
                "references": refs
            }
        except Exception as e:
            logger.error(f"Structured summary failed: {e}")
            if self._may_use_arxiv_heuristic():
                return {
                    "paragraphs": [self._generate_mock_analysis_from_arxiv(trends_data, query)],
                    "coverage_percent": 0.0,
                    "references": [],
                }
            return {
                "paragraphs": [],
                "coverage_percent": 0.0,
                "references": [],
                "error": str(e),
            }

    def _search_arxiv_by_keyword(self, keyword: str, max_results: int = 3) -> List[Dict]:
        """Search arXiv for a keyword and return reliable entries with PDF links"""
        try:
            search = arxiv.Search(
                query=f'all:\"{keyword}\"',
                max_results=max_results,
                sort_by=arxiv.SortCriterion.Relevance,
                sort_order=arxiv.SortOrder.Descending
            )
            results = []
            for result in arxiv.Client().results(search):
                pdf_url = result.pdf_url
                url = result.entry_id
                title = result.title
                authors = [a.name for a in result.authors] if result.authors else []
                year = result.published.year if result.published else None
                results.append({
                    "title": title,
                    "authors": authors,
                    "url": url,
                    "pdf_url": pdf_url,
                    "year": year
                })
            return results
        except Exception as e:
            logger.warning(f"arXiv search failed for '{keyword}': {e}")
            return []

    def _generate_mock_analysis_from_arxiv(self, trends_data: Dict, query: str) -> str:
        """Generate a reliable, citation-friendly mock analysis using arXiv PDFs for each keyword"""
        keywords_data = trends_data.get('keywords', {}) or {}
        if not keywords_data:
            return self._generate_basic_summary([], trends_data, query)
        
        keywords = list(keywords_data.keys())[:8]
        refs_per_kw = {}
        for kw in keywords:
            refs_per_kw[kw] = self._search_arxiv_by_keyword(kw, max_results=2)
        
        lines = []
        lines.append(f"For the topic '{query}', we analyzed representative arXiv literature across core keywords with direct PDF access.")
        for kw in keywords:
            entries = refs_per_kw.get(kw, [])
            if not entries:
                continue
            cite_bits = []
            for e in entries:
                yr = f" ({e['year']})" if e.get('year') else ""
                cite_bits.append(f"{e['title']}{yr} [PDF]({e['pdf_url']})")
            if cite_bits:
                lines.append(f"For '{kw}', relevant works include " + "; ".join(cite_bits) + ".")
        
        if len(lines) <= 1:
            return self._generate_basic_summary([], trends_data, query)
        return " ".join(lines)

    def _generate_structured_mock_summary_from_arxiv(self, trends_data: Dict, query: str, fallback_text: Optional[str] = None) -> Dict:
        """Create a two-paragraph structured summary with accurate arXiv PDF references"""
        keywords_data = trends_data.get('keywords', {}) or {}
        keywords = list(keywords_data.keys())[:8]
        refs = []
        for kw in keywords:
            for e in self._search_arxiv_by_keyword(kw, max_results=2):
                refs.append({
                    "title": e["title"],
                    "authors": e.get("authors", []),
                    "url": e.get("url"),
                    "pdf_url": e.get("pdf_url"),
                    "year": e.get("year")
                })
        # Build two concise paragraphs
        if refs:
            p1 = f"This overview of '{query}' synthesizes reliable evidence from arXiv across key themes, ensuring all references link to primary PDF sources."
            kw_snippet = ", ".join(keywords[:3]) if keywords else "core topics"
            p2 = f"Coverage spans {kw_snippet} and adjacent areas, with each cited item providing a direct PDF link for deeper evaluation."
            return {
                "paragraphs": [p1, p2],
                "coverage_percent": 0.0,
                "references": refs[:12]
            }
        # Fallback to text if no refs found
        text = fallback_text or self._generate_basic_summary([], trends_data, query)
        return {
            "paragraphs": [text],
            "coverage_percent": 0.0,
            "references": []
        }
    
    def _build_executive_summary_prompt(self, papers: List[Dict], trends_data: Dict, query: str) -> str:
        """Build prompt for executive summary using the local LLM"""
        total_papers = len(papers)
        top_keywords = list(trends_data.get('keywords', {}).keys())[:10]
        years_covered = trends_data.get('years', [])
        growth_data = trends_data.get('growth_analysis', {})
        
        # Find fastest growing topics
        fastest_growing = []
        if growth_data:
            sorted_growth = sorted(growth_data.items(), 
                                 key=lambda x: x[1].get('growth_rate', 0), 
                                 reverse=True)
            fastest_growing = [item[0] for item in sorted_growth[:3]]
        
        return f"""You are Nuralis Research Analyst. Generate a concise, technical executive summary for "{query}" strictly based on the provided research dataset. Audience: senior analysts and decision-makers. Do not include any headings, bullets, numbered lists, disclaimers, meta-instructions, or JSON.

Dataset Metrics:
- Research Volume: {total_papers} papers published
- Analysis Period: {min(years_covered) if years_covered else 'N/A'} to {max(years_covered) if years_covered else 'N/A'}
- Primary Research Areas: {', '.join(top_keywords[:8])}
- Emerging Focus Areas: {', '.join(fastest_growing) if fastest_growing else 'N/A'}

Requirements:
- Write exactly 2 analytical paragraphs (5-7 sentences each), plain text only
- Use technical language appropriate for research analysts
- Reference specific metrics and data points
- Avoid exclamation marks, casual language, or incomplete sentences
- Focus on quantitative insights and strategic implications
- Do NOT include any labels like "Executive Summary", "Paragraph 1", "Paragraph 2", or section titles
- Do NOT include lists, bullets, or markdown
- Do NOT invent data; align claims to the dataset context

Paragraph 1: Current research landscape, methodological maturity, and concentration of effort across key areas. Include specific metrics and identify notable methodological shifts or paradigm changes.

Paragraph 2: Quantitative trend analysis, emerging research directions, identified limitations or gaps, and strategic recommendations for future research investment.

Tone: Professional, analytical, data-driven. Use precise technical terminology. Avoid generic statements without quantitative backing.

Return only the two complete analytical paragraphs without headings, bullet points, or formatting."""
    
    def _generate_executive_summary(self, papers: List[Dict], trends_data: Dict, query: str) -> str:
        """Generate executive summary using Eleuther AI with regex post-processing for perfect summaries"""
        try:
            prompt = self._build_executive_summary_prompt(papers, trends_data, query)
            
            # ALWAYS try local LLM (Eleuther) first when available
            if self.llm_manager and self.llm_manager.is_available():
                try:
                    logger.info("🤖 Generating summary with Eleuther LLM + Regex post-processing...")
                    response = self.llm_manager.generate_text(prompt, max_new_tokens=400)
                    
                    if response and response.strip() not in ["", "No response generated.", "Model not available for text generation."]:
                        # Apply STRICT regex-based cleanup for perfect summaries
                        cleaned = self._apply_perfect_summary_regex(response)
                        
                        # Extract paragraphs using OutputFilter
                        paragraphs = OutputFilter.extract_paragraphs(cleaned, min_paragraphs=1)
                        if paragraphs:
                            final_summary = ' '.join(paragraphs)
                            logger.info("✅ Perfect summary generated with Eleuther + Regex")
                            return final_summary
                        
                        # If paragraph extraction fails, return cleaned text
                        if cleaned:
                            logger.info("✅ Summary generated with Eleuther + Regex (no paragraph split)")
                            return cleaned
                            
                except Exception as gen_error:
                    logger.warning(f"Eleuther LLM generation failed: {gen_error}")
            else:
                logger.warning("⚠️ Eleuther LLM not available")
            
            if self._may_use_arxiv_heuristic():
                logger.info("📚 Using arXiv-based heuristic summary (allow_arxiv_heuristic_fallback)")
                return self._generate_mock_analysis_from_arxiv(trends_data, query)
            return ""
            
        except Exception as e:
            logger.error(f"Executive summary generation failed: {e}")
            if self._may_use_arxiv_heuristic():
                return self._generate_mock_analysis_from_arxiv(trends_data, query)
            raise
    
    def _apply_perfect_summary_regex(self, text: str) -> str:
        """Apply comprehensive regex patterns to create perfect summaries"""
        if not text:
            return ""
        
        # Remove all system/user/assistant prefixes and instructions
        patterns_to_remove = [
            r'^system\s+.*?user\s*:?\s*',
            r'^System\s*:.*?User\s*:?\s*',
            r'^You are .*?\.\s*',
            r'^As a .*?\.\s*',
            r'^Instructions\s*:.*?\n',
            r'^Dataset\s*:.*?Instructions\s*:',
            r'^Requirements\s*:.*?\n',
            r'^Paragraph \d+\s*:?\s*',
            r'^Executive Summary\s*:?\s*',
            r'^\*\*Executive Summary\*\*\s*:?\s*',
            r'^system\s+',
            r'^user\s+',
            r'^assistant\s+',
        ]
        
        for pattern in patterns_to_remove:
            text = re.sub(pattern, '', text, flags=re.DOTALL | re.IGNORECASE | re.MULTILINE)
        
        # Remove everything before "assistant" marker if present
        if 'assistant' in text.lower():
            parts = re.split(r'\bassistant\b', text, flags=re.IGNORECASE)
            if len(parts) > 1:
                text = parts[-1].strip()
        
        # Remove markdown headers and formatting artifacts
        text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'\*\*\*+', '', text)
        
        # Clean up whitespace
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)  # Max 2 newlines
        text = re.sub(r'[ \t]+', ' ', text)  # Normalize spaces
        
        # Remove incomplete sentences at the end
        sentences = text.split('.')
        if len(sentences) > 1:
            last_sentence = sentences[-1].strip()
            if len(last_sentence) < 10:  # Likely incomplete
                text = '.'.join(sentences[:-1]) + '.'
        
        # Ensure proper ending punctuation
        text = text.strip()
        if text and not text.endswith(('.', '!', '?')):
            text += '.'
        
        return text
    
    def _analyze_trends(self, papers: List[Dict], trends_data: Dict) -> Dict:
        """Analyze research trends in detail"""
        try:
            trends_analysis = {
                "emerging_topics": self._identify_emerging_topics(trends_data),
                "declining_topics": self._identify_declining_topics(trends_data),
                "stable_topics": self._identify_stable_topics(trends_data),
                "trend_velocity": self._calculate_trend_velocity(trends_data),
                "seasonal_patterns": self._analyze_seasonal_patterns(papers),
                "geographic_trends": self._analyze_geographic_trends(papers)
            }
            
            return trends_analysis
            
        except Exception as e:
            logger.error(f"Trend analysis failed: {e}")
            return {"error": f"Trend analysis failed: {str(e)}"}
    
    def _identify_emerging_topics(self, trends_data: Dict) -> List[Dict]:
        """Identify emerging research topics - Domain-specific based on actual data"""
        emerging = []
        growth_data = trends_data.get('growth_analysis', {})
        
        for keyword, data in growth_data.items():
            if isinstance(data, dict):
                growth_rate = data.get('growth_rate', 0)
                total_papers = data.get('total_papers', 0)
                
                # Emerging: meaningful growth, not yet saturated
                if growth_rate > 20 and 10 <= total_papers <= 300:
                    emerging.append({
                        "topic": keyword,
                        "growth_rate": growth_rate,
                        "total_papers": total_papers,
                        "trend": "emerging"
                    })
        
        # Sort by growth rate (highest first)
        emerging = sorted(emerging, key=lambda x: x['growth_rate'], reverse=True)
        
        return emerging[:5]
    
    def _identify_declining_topics(self, trends_data: Dict) -> List[Dict]:
        """Identify declining research topics - Domain-specific based on actual data"""
        declining = []
        growth_data = trends_data.get('growth_analysis', {})
        
        for keyword, data in growth_data.items():
            if isinstance(data, dict):
                growth_rate = data.get('growth_rate', 0)
                total_papers = data.get('total_papers', 0)
                
                # Declining: strong negative growth and non-trivial base
                if growth_rate < -10 and total_papers >= 50:
                    declining.append({
                        "topic": keyword,
                        "growth_rate": growth_rate,
                        "total_papers": total_papers,
                        "trend": "declining"
                    })
        
        # Sort by growth rate (most negative first)
        declining = sorted(declining, key=lambda x: x['growth_rate'])
        
        return declining[:5]
    
    def _identify_stable_topics(self, trends_data: Dict) -> List[Dict]:
        """Identify stable research topics"""
        stable = []
        growth_data = trends_data.get('growth_analysis', {})
        
        for keyword, data in growth_data.items():
            if isinstance(data, dict):
                growth_rate = data.get('growth_rate', 0)
                total_papers = data.get('total_papers', 0)
                
                # Stable: low growth rate, high total papers
                if -10 <= growth_rate <= 10 and total_papers > 20:
                    stable.append({
                        "topic": keyword,
                        "growth_rate": growth_rate,
                        "total_papers": total_papers,
                        "trend": "stable"
                    })
        
        return sorted(stable, key=lambda x: x['total_papers'], reverse=True)[:5]
    
    def _calculate_trend_velocity(self, trends_data: Dict) -> Dict:
        """Calculate trend velocity metrics"""
        try:
            keywords_data = trends_data.get('keywords', {})
            velocities = []
            
            for keyword, year_counts in keywords_data.items():
                if not year_counts or not isinstance(year_counts, dict):
                    continue
                
                # Handle year keys - they might be strings or integers
                # Convert all keys to strings first, then to ints for sorting
                year_keys = []
                for key in year_counts.keys():
                    try:
                        # Try to convert to int (handles both string '2020' and int 2020)
                        year_int = int(key)
                        year_keys.append((year_int, str(key)))  # Store both int and original key
                    except (ValueError, TypeError):
                        continue  # Skip non-numeric keys
                
                if len(year_keys) < 2:
                    continue
                
                # Sort by integer year
                year_keys.sort(key=lambda x: x[0])
                years = [y[0] for y in year_keys]  # Integer years for calculation
                original_keys = [y[1] for y in year_keys]  # Original keys for lookup
                
                # Get counts using original keys (which might be strings or ints)
                counts = []
                for orig_key in original_keys:
                    # Try original key first, then try as string, then as int
                    count = year_counts.get(orig_key) or year_counts.get(str(orig_key)) or year_counts.get(int(orig_key))
                    if count is not None:
                        counts.append(int(count))
                    else:
                        logger.warning(f"Could not find count for year {orig_key} in keyword {keyword}")
                        break
                
                if len(counts) != len(years):
                    continue  # Skip if we couldn't get all counts
                
                # Calculate velocity (rate of change)
                if len(counts) >= 2:
                    velocity = (counts[-1] - counts[0]) / (years[-1] - years[0])
                    velocities.append({
                        "keyword": keyword,
                        "velocity": velocity,
                        "acceleration": self._calculate_acceleration(counts, years)
                    })
            
            # Sort by velocity
            velocities.sort(key=lambda x: abs(x['velocity']), reverse=True)
            
            return {
                "fastest_accelerating": velocities[:3],
                "fastest_decelerating": velocities[-3:],
                "average_velocity": np.mean([v['velocity'] for v in velocities]) if velocities else 0
            }
            
        except Exception as e:
            logger.error(f"Trend velocity calculation failed: {e}")
            return {"error": f"Velocity calculation failed: {str(e)}"}
    
    def _calculate_acceleration(self, counts: List[int], years: List[int]) -> float:
        """Calculate acceleration (second derivative)"""
        if len(counts) < 3:
            return 0
        
        # Simple acceleration calculation
        velocities = []
        for i in range(1, len(counts)):
            vel = (counts[i] - counts[i-1]) / (years[i] - years[i-1])
            velocities.append(vel)
        
        if len(velocities) < 2:
            return 0
        
        # Calculate acceleration as change in velocity
        acceleration = (velocities[-1] - velocities[0]) / (len(velocities) - 1)
        return acceleration
    
    def _analyze_seasonal_patterns(self, papers: List[Dict]) -> Dict:
        """Analyze seasonal patterns in research"""
        try:
            monthly_counts = defaultdict(int)
            
            for paper in papers:
                if isinstance(paper, dict) and 'date' in paper:
                    date = paper['date']
                    if isinstance(date, str) and len(date) >= 7:
                        try:
                            month = date[:7]  # YYYY-MM
                            monthly_counts[month] += 1
                        except:
                            continue
            
            if not monthly_counts:
                return {"error": "No date data available"}
            
            # Find peak months
            sorted_months = sorted(monthly_counts.items(), key=lambda x: x[1], reverse=True)
            
            return {
                "peak_month": sorted_months[0] if sorted_months else None,
                "monthly_distribution": dict(sorted_months),
                "seasonal_variance": np.var(list(monthly_counts.values())) if monthly_counts else 0
            }
            
        except Exception as e:
            logger.error(f"Seasonal pattern analysis failed: {e}")
            return {"error": f"Seasonal analysis failed: {str(e)}"}
    
    def _analyze_geographic_trends(self, papers: List[Dict]) -> Dict:
        """Analyze geographic trends in research"""
        try:
            # Extract country information from authors (basic implementation)
            country_counts = defaultdict(int)
            
            for paper in papers:
                if isinstance(paper, dict) and 'authors' in paper:
                    authors = paper['authors']
                    if isinstance(authors, list):
                        for author in authors:
                            if isinstance(author, str):
                                # Simple country extraction (this could be enhanced)
                                if 'USA' in author or 'United States' in author:
                                    country_counts['USA'] += 1
                                elif 'China' in author:
                                    country_counts['China'] += 1
                                elif 'UK' in author or 'United Kingdom' in author:
                                    country_counts['UK'] += 1
                                elif 'Germany' in author:
                                    country_counts['Germany'] += 1
                                elif 'Japan' in author:
                                    country_counts['Japan'] += 1
            
            if not country_counts:
                return {"error": "No geographic data available"}
            
            sorted_countries = sorted(country_counts.items(), key=lambda x: x[1], reverse=True)
            
            return {
                "top_countries": sorted_countries[:5],
                "geographic_diversity": len(country_counts),
                "concentration_index": max(country_counts.values()) / sum(country_counts.values()) if country_counts else 0
            }
            
        except Exception as e:
            logger.error(f"Geographic trend analysis failed: {e}")
            return {"error": f"Geographic analysis failed: {str(e)}"}
    
    def _identify_research_gaps(self, papers: List[Dict], trends_data: Dict) -> List[Dict]:
        """Identify research gaps and opportunities - Domain-specific based on actual data"""
        try:
            gaps = []
            
            # Analyze keyword combinations (domain-agnostic)
            keyword_combinations = self._analyze_keyword_combinations(papers)
            
            # Find underrepresented combinations
            for combo, count in keyword_combinations.items():
                if count < 3:  # Underrepresented
                    gaps.append({
                        "gap_type": "keyword_combination",
                        "description": f"Limited research on {combo}",
                        "opportunity": f"Research combining {combo}",
                        "priority": "medium"
                    })
            
            # Analyze temporal gaps
            years = trends_data.get('years', [])
            if years:
                year_span = max(years) - min(years)
                if year_span > 5:
                    recent_years = [y for y in years if y >= max(years) - 2]
                    if len(recent_years) < len(years) * 0.3:
                        gaps.append({
                            "gap_type": "temporal",
                            "description": "Limited recent research activity",
                            "opportunity": "Focus on recent developments and applications",
                            "priority": "high"
                        })
            
            # Analyze keyword diversity gaps
            keywords_data = trends_data.get('keywords', {})
            if keywords_data:
                # Find keywords with low frequency (potential gaps)
                low_freq_keywords = []
                for keyword, year_counts in keywords_data.items():
                    if isinstance(year_counts, dict):
                        total_count = sum(year_counts.values())
                        if 1 <= total_count <= 5:  # Low frequency - potential gap
                            low_freq_keywords.append({
                                "gap_type": "low_frequency",
                                "description": f"Understudied area: {keyword}",
                                "opportunity": f"Expand research on {keyword}",
                                "priority": "medium"
                            })
                
                gaps.extend(low_freq_keywords[:2])
            
            return gaps[:5]  # Return top 5 gaps
            
        except Exception as e:
            logger.error(f"Research gap identification failed: {e}")
            return [{"error": f"Gap analysis failed: {str(e)}"}]
    
    def _analyze_keyword_combinations(self, papers: List[Dict]) -> Dict:
        """Analyze keyword combinations in papers"""
        combinations = defaultdict(int)
        
        for paper in papers:
            if isinstance(paper, dict):
                title = paper.get('title', '').lower()
                abstract = paper.get('abstract', '').lower()
                text = f"{title} {abstract}"
                
                # Simple keyword extraction (could be enhanced with NLP)
                keywords = ['machine learning', 'deep learning', 'neural network', 
                           'transformer', 'attention', 'nlp', 'computer vision']
                
                found_keywords = [kw for kw in keywords if kw in text]
                
                # Count combinations
                for i, kw1 in enumerate(found_keywords):
                    for kw2 in found_keywords[i+1:]:
                        combo = f"{kw1} + {kw2}"
                        combinations[combo] += 1
        
        return dict(combinations)
    
    def _predict_future_directions(self, papers: List[Dict], trends_data: Dict) -> List[Dict]:
        """Predict future research directions"""
        try:
            if not self.llm_manager or not self.llm_manager.is_available():
                return self._get_basic_future_directions(trends_data)
            
            # Prepare trend data for AI analysis
            emerging_topics = self._identify_emerging_topics(trends_data)
            growth_data = trends_data.get('growth_analysis', {})
            
            prompt = f"""As a research futurist, predict future directions for AI/ML research based on current trends.

Current Emerging Topics: {[t['topic'] for t in emerging_topics[:3]]}
Growth Data: {dict(list(growth_data.items())[:5])}

Predict 3-5 future research directions with:
1. Direction name
2. Rationale (why this will be important)
3. Timeline (short/medium/long term)
4. Key challenges to address

Format as structured predictions."""
            
            response = self.llm_manager.generate_text(prompt, max_new_tokens=400)
            
            # Clean and filter the response
            if response:
                response = OutputFilter.clean_text(response)
            
            # Parse AI response into structured format
            predictions = self._parse_future_predictions(response)
            
            return predictions if predictions else self._get_basic_future_directions(trends_data)
            
        except Exception as e:
            logger.error(f"Future direction prediction failed: {e}")
            return self._get_basic_future_directions(trends_data)
    
    def _parse_future_predictions(self, ai_response: str) -> List[Dict]:
        """Parse AI response into structured predictions"""
        predictions = []
        
        # Simple parsing (could be enhanced)
        lines = ai_response.split('\n')
        current_prediction = {}
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                if 'direction' in line.lower() or 'prediction' in line.lower():
                    if current_prediction:
                        predictions.append(current_prediction)
                    current_prediction = {"direction": line}
                elif 'rationale' in line.lower() or 'why' in line.lower():
                    current_prediction["rationale"] = line
                elif 'timeline' in line.lower() or 'time' in line.lower():
                    current_prediction["timeline"] = line
                elif 'challenge' in line.lower():
                    current_prediction["challenges"] = line
        
        if current_prediction:
            predictions.append(current_prediction)
        
        return predictions[:5]
    
    def _get_basic_future_directions(self, trends_data: Dict) -> List[Dict]:
        """Get basic future directions without AI - Domain-specific based on emerging topics"""
        directions = []
        
        # Use actual emerging topics from the data
        emerging = self._identify_emerging_topics(trends_data)
        
        for topic in emerging[:3]:
            directions.append({
                "direction": f"Advanced {topic['topic']}",
                "rationale": f"High growth rate ({topic['growth_rate']:.1f}%) indicates increasing interest",
                "timeline": "Medium term (2-3 years)",
                "challenges": "Scalability and real-world applications"
            })
        
        # If no emerging topics, use top keywords
        if not directions:
            keywords_data = trends_data.get('keywords', {})
            if keywords_data:
                sorted_keywords = sorted(
                    keywords_data.items(),
                    key=lambda x: sum(x[1].values()) if isinstance(x[1], dict) else 0,
                    reverse=True
                )
                for keyword, _ in sorted_keywords[:3]:
                    directions.append({
                        "direction": f"Expansion of {keyword} research",
                        "rationale": "Current research momentum suggests continued growth",
                        "timeline": "Short to medium term",
                        "challenges": "Integration with existing methods and validation"
                    })
        
        return directions
    
    def _extract_key_findings(self, papers: List[Dict], trends_data: Dict) -> List[Dict]:
        """Extract key findings from the research - Domain-specific based on actual papers"""
        findings = []
        
        # Analyze paper titles for common themes (domain-agnostic)
        title_themes = self._analyze_title_themes(papers)
        
        # Get top keywords from trends data (these are domain-specific)
        keywords_data = trends_data.get('keywords', {})
        if keywords_data:
            # Sort by total frequency across all years
            sorted_keywords = sorted(
                keywords_data.items(),
                key=lambda x: sum(x[1].values()) if isinstance(x[1], dict) else 0,
                reverse=True
            )
            
            # Add top keywords as findings
            for keyword, year_counts in sorted_keywords[:5]:
                if isinstance(year_counts, dict):
                    total_count = sum(year_counts.values())
                    if total_count >= 3:  # Significant theme
                        findings.append({
                            "finding": f"Strong focus on {keyword}",
                            "evidence": f"{total_count} papers mention this theme",
                            "significance": "high" if total_count >= 10 else "medium"
                        })
        
        # Also analyze title themes for additional insights
        for theme, count in title_themes.items():
            if count >= 3 and not any(f['finding'].lower().endswith(theme.lower()) for f in findings):
                findings.append({
                    "finding": f"Strong focus on {theme}",
                    "evidence": f"{count} papers mention this theme",
                    "significance": "high" if count >= 10 else "medium"
                })
        
        # Analyze growth patterns
        growth_data = trends_data.get('growth_analysis', {})
        if growth_data:
            fastest_growing = max(growth_data.items(), 
                                key=lambda x: x[1].get('growth_rate', 0) if isinstance(x[1], dict) else 0)
            if isinstance(fastest_growing[1], dict):
                findings.append({
                    "finding": f"Fastest growing area: {fastest_growing[0]}",
                    "evidence": f"Growth rate: {fastest_growing[1].get('growth_rate', 0):.1f}%",
                    "significance": "high"
                })
        
        return findings[:5]
    
    def _analyze_title_themes(self, papers: List[Dict]) -> Dict:
        """Analyze common themes in paper titles"""
        themes = defaultdict(int)
        
        for paper in papers:
            if isinstance(paper, dict) and 'title' in paper:
                title = paper['title'].lower()
                
                # Common AI/ML themes
                theme_keywords = {
                    'transformer': ['transformer', 'attention', 'bert', 'gpt'],
                    'deep learning': ['deep learning', 'neural network', 'cnn', 'rnn'],
                    'nlp': ['natural language', 'nlp', 'language model', 'text'],
                    'computer vision': ['computer vision', 'image', 'visual', 'object detection'],
                    'reinforcement learning': ['reinforcement learning', 'rl', 'agent'],
                    'multimodal': ['multimodal', 'vision-language', 'cross-modal']
                }
                
                for theme, keywords in theme_keywords.items():
                    if any(kw in title for kw in keywords):
                        themes[theme] += 1
        
        return dict(themes)
    
    def _analyze_methodologies(self, papers: List[Dict]) -> Dict:
        """Analyze research methodologies"""
        methodologies = defaultdict(int)
        
        for paper in papers:
            if isinstance(paper, dict):
                abstract = paper.get('abstract', '').lower()
                
                # Common methodologies
                method_keywords = {
                    'experimental': ['experiment', 'evaluation', 'benchmark', 'test'],
                    'theoretical': ['theory', 'theoretical', 'proof', 'analysis'],
                    'empirical': ['empirical', 'case study', 'real-world', 'practical'],
                    'survey': ['survey', 'review', 'overview', 'comprehensive'],
                    'simulation': ['simulation', 'synthetic', 'simulated', 'virtual']
                }
                
                for method, keywords in method_keywords.items():
                    if any(kw in abstract for kw in keywords):
                        methodologies[method] += 1
        
        return dict(methodologies)
    
    def _analyze_collaborations(self, papers: List[Dict]) -> Dict:
        """Analyze research collaborations"""
        collaboration_stats = {
            "avg_authors_per_paper": 0,
            "multi_author_papers": 0,
            "single_author_papers": 0,
            "collaboration_rate": 0
        }
        
        author_counts = []
        
        for paper in papers:
            if isinstance(paper, dict) and 'authors' in paper:
                authors = paper['authors']
                if isinstance(authors, list):
                    author_count = len(authors)
                    author_counts.append(author_count)
                    
                    if author_count > 1:
                        collaboration_stats["multi_author_papers"] += 1
                    else:
                        collaboration_stats["single_author_papers"] += 1
        
        if author_counts:
            collaboration_stats["avg_authors_per_paper"] = np.mean(author_counts)
            total_papers = len(author_counts)
            collaboration_stats["collaboration_rate"] = (
                collaboration_stats["multi_author_papers"] / total_papers * 100
            )
        
        return collaboration_stats
    
    def _analyze_impact(self, papers: List[Dict], trends_data: Dict) -> Dict:
        """Analyze research impact indicators"""
        impact_metrics = {
            "research_volume": len(papers),
            "keyword_diversity": len(trends_data.get('keywords', {})),
            "temporal_span": 0,
            "growth_momentum": 0
        }
        
        # Calculate temporal span
        years = trends_data.get('years', [])
        if years:
            impact_metrics["temporal_span"] = max(years) - min(years)
        
        # Calculate growth momentum
        growth_data = trends_data.get('growth_analysis', {})
        if growth_data:
            avg_growth = np.mean([data.get('growth_rate', 0) for data in growth_data.values() 
                                if isinstance(data, dict)])
            impact_metrics["growth_momentum"] = avg_growth
        
        return impact_metrics
    
    def _generate_recommendations(self, papers: List[Dict], trends_data: Dict, query: str) -> List[Dict]:
        """Generate actionable recommendations"""
        recommendations = []
        
        # Based on research gaps
        gaps = self._identify_research_gaps(papers, trends_data)
        for gap in gaps[:2]:
            recommendations.append({
                "type": "research_opportunity",
                "title": f"Explore {gap['description']}",
                "description": gap['opportunity'],
                "priority": gap['priority'],
                "action": "Consider research proposal in this area"
            })
        
        # Based on emerging trends
        emerging = self._identify_emerging_topics(trends_data)
        for topic in emerging[:2]:
            recommendations.append({
                "type": "trend_opportunity",
                "title": f"Investigate {topic['topic']}",
                "description": f"High growth rate ({topic['growth_rate']:.1f}%) indicates potential",
                "priority": "high",
                "action": "Monitor developments and consider early adoption"
            })
        
        # Based on collaboration analysis
        collab_stats = self._analyze_collaborations(papers)
        if collab_stats["collaboration_rate"] < 70:
            recommendations.append({
                "type": "collaboration",
                "title": "Increase research collaboration",
                "description": f"Current collaboration rate: {collab_stats['collaboration_rate']:.1f}%",
                "priority": "medium",
                "action": "Seek interdisciplinary partnerships"
            })
        
        return recommendations[:5]
    
    def _generate_basic_summary(self, papers: List[Dict], trends_data: Dict, query: str) -> str:
        """Generate basic summary without AI"""
        total_papers = len(papers)
        total_keywords = len(trends_data.get('keywords', {}))
        years = trends_data.get('years', [])
        
        summary = f"Research analysis on '{query}' reveals {total_papers} papers "
        summary += f"spanning {len(years)} years with {total_keywords} key research areas. "
        
        if years:
            summary += f"The research period covers {min(years)} to {max(years)}. "
        
        growth_data = trends_data.get('growth_analysis', {})
        if growth_data:
            fastest_growing = max(growth_data.items(), 
                                key=lambda x: x[1].get('growth_rate', 0))
            summary += f"The fastest growing area is {fastest_growing[0]} "
            summary += f"with a growth rate of {fastest_growing[1].get('growth_rate', 0):.1f}%. "
        
        summary += "This indicates an active and evolving research landscape with significant opportunities for innovation."
        
        return summary
    
    def _get_fallback_insights(self, papers: List[Dict], trends_data: Dict, query: str) -> Dict:
        """Get fallback insights when AI is not available"""
        return {
            "executive_summary": self._generate_basic_summary(papers, trends_data, query),
            "trend_analysis": {"error": "AI analysis not available"},
            "research_gaps": [{"error": "AI analysis not available"}],
            "future_directions": [{"error": "AI analysis not available"}],
            "key_findings": [{"error": "AI analysis not available"}],
            "methodology_insights": {"error": "AI analysis not available"},
            "collaboration_insights": {"error": "AI analysis not available"},
            "impact_analysis": {"error": "AI analysis not available"},
            "recommendations": [{"error": "AI analysis not available"}]
        }
