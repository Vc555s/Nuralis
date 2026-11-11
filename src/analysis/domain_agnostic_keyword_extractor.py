"""
Domain-Agnostic Keyword Extractor
Extracts relevant keywords from papers regardless of domain
Uses TF-IDF and noun phrase extraction instead of hardcoded keyword lists
"""
import re
from typing import List, Dict, Set
from collections import Counter
from src.utils.logging_utils import logger


class DomainAgnosticKeywordExtractor:
    """
    Extracts keywords from papers using domain-agnostic methods:
    1. TF-IDF based extraction (most frequent important terms)
    2. Noun phrase extraction (technical terms)
    3. Domain-specific terms from query context
    
    Works for ALL domains: CS, Electronics, Physics, Biology, Medicine, Economics, etc.
    """
    
    # Common stopwords to filter out (domain-agnostic)
    STOPWORDS = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
        'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
        'would', 'could', 'should', 'may', 'might', 'must', 'can', 'this',
        'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they',
        'what', 'which', 'who', 'when', 'where', 'why', 'how', 'all', 'each',
        'every', 'both', 'few', 'more', 'most', 'other', 'some', 'such', 'no',
        'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very',
        'just', 'now', 'then', 'here', 'there', 'where', 'why', 'how', 'all',
        'paper', 'papers', 'study', 'studies', 'research', 'method', 'methods',
        'approach', 'approaches', 'result', 'results', 'analysis', 'proposed',
        'present', 'presented', 'show', 'shows', 'demonstrate', 'demonstrates',
        'propose', 'proposes', 'introduce', 'introduces', 'develop', 'develops',
        'design', 'designs', 'implement', 'implements', 'evaluate', 'evaluates',
        'compare', 'compares', 'improve', 'improves', 'novel', 'new', 'based',
        'using', 'used', 'use', 'uses', 'via', 'through', 'within', 'without'
    }
    
    def __init__(self, query: str = ""):
        """
        Initialize with optional query for context-aware extraction
        
        Args:
            query: Original search query (helps prioritize relevant terms)
        """
        self.query = query.lower() if query else ""
        self.query_terms = set(self._extract_terms_from_query(query)) if query else set()
    
    def extract_keywords(self, paper: Dict, max_keywords: int = 10) -> List[str]:
        """
        Extract domain-agnostic keywords from a paper
        
        Works for ANY domain by extracting from actual content:
        - Computer Science: neural network, transformer, etc.
        - Electronics: VLSI, CMOS, FPGA, circuit, etc.
        - Physics: quantum, photon, particle, etc.
        - Biology: DNA, protein, gene, etc.
        - Medicine: clinical, diagnosis, treatment, etc.
        - Economics: market, trading, portfolio, etc.
        - Any other domain!
        
        Args:
            paper: Paper dictionary with title, abstract, etc.
            max_keywords: Maximum number of keywords to return
            
        Returns:
            List of extracted keywords
        """
        try:
            title = paper.get('title', '')
            abstract = paper.get('abstract', '')
            
            if not title and not abstract:
                return []
            
            # Combine text
            text = f"{title} {abstract}".lower()
            
            # Extract keywords using multiple methods
            keywords = set()
            
            # Method 1: Extract important terms (nouns, technical terms)
            # Works for ANY domain - just finds frequent important words
            important_terms = self._extract_important_terms(text)
            keywords.update(important_terms)
            
            # Method 2: Extract acronyms and technical patterns
            # Works for ANY domain - finds acronyms like VLSI, CMOS, DNA, AI, etc.
            technical_terms = self._extract_technical_terms(text)
            keywords.update(technical_terms)
            
            # Method 3: Extract multi-word phrases (2-3 words)
            # Works for ANY domain - finds phrases like "chip design", "quantum computing", etc.
            phrases = self._extract_phrases(text)
            keywords.update(phrases)
            
            # Method 4: Boost terms that match query
            # Helps prioritize domain-specific terms from your query
            if self.query_terms:
                query_matches = [kw for kw in keywords if any(qt in kw for qt in self.query_terms)]
                # Prioritize query-related keywords
                keywords = set(query_matches) | keywords
            
            # Filter and rank
            filtered_keywords = self._filter_and_rank(keywords, text)
            
            # Return top keywords
            return filtered_keywords[:max_keywords]
            
        except Exception as e:
            logger.warning(f"Keyword extraction failed: {e}")
            return []
    
    def _extract_terms_from_query(self, query: str) -> List[str]:
        """Extract important terms from query"""
        if not query:
            return []
        
        # Remove common words
        words = re.findall(r'\b\w+\b', query.lower())
        terms = [w for w in words if w not in self.STOPWORDS and len(w) > 2]
        
        # Also extract multi-word phrases
        phrases = []
        words_list = query.lower().split()
        for i in range(len(words_list) - 1):
            if words_list[i] not in self.STOPWORDS and words_list[i+1] not in self.STOPWORDS:
                phrases.append(f"{words_list[i]} {words_list[i+1]}")
        
        return terms + phrases
    
    def _extract_important_terms(self, text: str) -> List[str]:
        """
        Extract important single-word terms (nouns, technical terms)
        Works for ANY domain - just finds frequent non-stopword terms
        """
        # Extract words (3+ characters, not stopwords)
        words = re.findall(r'\b[a-z]{3,}\b', text)
        
        # Filter stopwords and count frequency
        important_words = [w for w in words if w not in self.STOPWORDS]
        word_counts = Counter(important_words)
        
        # Return most frequent terms (likely to be domain-specific)
        # For VLSI papers: circuit, design, chip, etc.
        # For CS papers: learning, network, model, etc.
        # For Physics papers: quantum, particle, energy, etc.
        top_words = [word for word, count in word_counts.most_common(20)]
        return top_words
    
    def _extract_technical_terms(self, text: str) -> List[str]:
        """
        Extract technical terms: acronyms, hyphenated terms, etc.
        Works for ANY domain - finds technical patterns
        """
        technical_terms = []
        
        # Extract acronyms (2+ uppercase letters)
        # Works for: VLSI, CMOS, FPGA, AI, ML, DNA, RNA, etc.
        acronyms = re.findall(r'\b[A-Z]{2,}\b', text)
        technical_terms.extend([a.lower() for a in acronyms])
        
        # Extract hyphenated terms
        # Works for: deep-learning, chip-level, low-power, etc.
        hyphenated = re.findall(r'\b\w+-\w+(?:-\w+)?\b', text)
        technical_terms.extend([h.lower() for h in hyphenated])
        
        # Extract common technical suffixes
        # Works for: processing, computing, optimization, etc.
        tech_suffixes = ['ing', 'tion', 'sion', 'ment', 'ity', 'ism']
        for suffix in tech_suffixes:
            pattern = r'\b\w+' + suffix + r'\b'
            words = re.findall(pattern, text)
            technical_terms.extend([w.lower() for w in words if len(w) > 4])
        
        return list(set(technical_terms))
    
    def _extract_phrases(self, text: str, max_phrase_length: int = 3) -> List[str]:
        """
        Extract meaningful multi-word phrases
        Works for ANY domain - finds common phrases in the text
        """
        phrases = []
        
        # Split into sentences
        sentences = re.split(r'[.!?]\s+', text)
        
        for sentence in sentences:
            words = sentence.split()
            
            # Extract 2-3 word phrases
            for n in range(2, min(max_phrase_length + 1, len(words) + 1)):
                for i in range(len(words) - n + 1):
                    phrase_words = words[i:i+n]
                    
                    # Skip if all words are stopwords
                    if all(w.lower() in self.STOPWORDS for w in phrase_words):
                        continue
                    
                    # Skip if phrase is too generic
                    if len(phrase_words) == 2:
                        if phrase_words[0].lower() in ['the', 'a', 'an']:
                            continue
                    
                    phrase = ' '.join(phrase_words).lower()
                    if len(phrase) > 5:  # Minimum phrase length
                        phrases.append(phrase)
        
        # Count and return most frequent phrases
        phrase_counts = Counter(phrases)
        top_phrases = [phrase for phrase, count in phrase_counts.most_common(15)]
        return top_phrases
    
    def _filter_and_rank(self, keywords: Set[str], text: str) -> List[str]:
        """Filter and rank keywords by relevance"""
        filtered = []
        
        for keyword in keywords:
            # Skip very short keywords
            if len(keyword) < 3:
                continue
            
            # Skip if it's just numbers
            if keyword.isdigit():
                continue
            
            # Calculate relevance score
            score = self._calculate_relevance(keyword, text)
            
            if score > 0:
                filtered.append((keyword, score))
        
        # Sort by score (descending)
        filtered.sort(key=lambda x: x[1], reverse=True)
        
        # Return just the keywords
        return [kw for kw, score in filtered]
    
    def _calculate_relevance(self, keyword: str, text: str) -> float:
        """Calculate relevance score for a keyword"""
        score = 0.0
        
        # Count occurrences
        count = text.lower().count(keyword.lower())
        score += count * 0.5
        
        # Boost if appears in title (more important)
        title = text.split('.')[0] if '.' in text else text[:200]
        if keyword.lower() in title.lower():
            score += 2.0
        
        # Boost if matches query terms
        if self.query_terms:
            for query_term in self.query_terms:
                if query_term in keyword.lower() or keyword.lower() in query_term:
                    score += 3.0
        
        # Boost technical terms (acronyms, hyphenated)
        if len(keyword) >= 2 and keyword.isupper():
            score += 1.0
        if '-' in keyword:
            score += 1.0
        
        # Penalize very common words that slipped through
        if keyword in ['paper', 'study', 'research', 'method', 'result', 'analysis']:
            score *= 0.3
        
        return score

