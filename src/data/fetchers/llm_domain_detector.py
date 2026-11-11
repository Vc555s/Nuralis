"""
LLM-Powered Domain Detector - Uses reasoning to detect academic domains
Falls back to keyword-based detection if LLM unavailable
"""
from typing import List, Dict, Optional
import json
import re
from src.utils.logging_utils import logger
from src.data.fetchers.domain_detector import DomainDetector


class LLMDomainDetector:
    """
    Uses LLM reasoning to detect relevant academic domains from queries
    More accurate than keyword matching, especially for ambiguous queries
    """
    
    # Domain to ArXiv category mapping
    DOMAIN_TO_CATEGORIES = {
        'Computer Science': ['cs.AI', 'cs.LG', 'cs.CL', 'cs.CV', 'cs.NE', 'cs.RO', 'cs.SE', 'cs.DS'],
        'Electrical Engineering': ['eess.AS', 'eess.IV', 'eess.SP', 'eess.SY', 'cs.AR', 'cs.ET', 'physics.app-ph'],
        'Electronics': ['eess.AS', 'eess.IV', 'eess.SP', 'eess.SY', 'cs.AR', 'physics.app-ph'],
        'Physics': ['physics.app-ph', 'physics.comp-ph', 'physics.optics', 'cond-mat.mtrl-sci', 'physics.quant-ph'],
        'Mathematics': ['math.NA', 'math.OC', 'math.ST', 'math.PR', 'stat.ML', 'stat.TH'],
        'Biology': ['q-bio.BM', 'q-bio.GN', 'q-bio.NC', 'q-bio.CB', 'q-bio.MN'],
        'Medicine': ['q-bio.BM', 'q-bio.GN', 'q-bio.NC'],
        'Economics': ['econ.EM', 'econ.TH', 'q-fin.EC', 'q-fin.MF'],
        'Mechanical Engineering': ['physics.flu-dyn', 'physics.class-ph', 'cond-mat.mtrl-sci'],
        'Chemical Engineering': ['physics.chem-ph', 'cond-mat.mtrl-sci']
    }
    
    @classmethod
    def detect_with_llm(cls, query: str, llm_manager=None) -> List[str]:
        """
        Use LLM to reason about which domains are relevant
        
        Args:
            query: Search query
            llm_manager: Optional LLM manager instance
            
        Returns:
            List of ArXiv category codes
        """
        # Try LLM-based detection first
        if llm_manager and hasattr(llm_manager, 'generate') and llm_manager.is_available():
            try:
                return cls._llm_reasoning(query, llm_manager)
            except Exception as e:
                logger.warning(f"LLM domain detection failed: {e}, falling back to keyword-based")
        
        # Fallback to keyword-based detection
        return DomainDetector.detect_domains(query)
    
    @classmethod
    def _llm_reasoning(cls, query: str, llm_manager) -> List[str]:
        """
        Use LLM to reason about domain relevance
        """
        prompt = cls._create_prompt(query)
        
        # Generate with LLM
        response = llm_manager.generate(
            prompt,
            max_length=200,
            temperature=0.3,  # Lower temperature for more consistent reasoning
            do_sample=True
        )
        
        # Parse LLM response
        domains = cls._parse_llm_response(response, query)
        
        # Convert domains to categories
        categories = cls._domains_to_categories(domains)
        
        logger.info(f"🧠 LLM detected domains: {domains}")
        logger.info(f"📚 Selected {len(categories)} categories from LLM reasoning")
        
        return categories
    
    @classmethod
    def _create_prompt(cls, query: str) -> str:
        """Create prompt for LLM domain detection"""
        return f"""Analyze this research query and identify which academic domains are most relevant.

Query: "{query}"

Available domains:
- Computer Science (AI, ML, algorithms, software, computer vision, NLP)
- Electrical Engineering (circuits, electronics, VLSI, signal processing, power systems)
- Electronics (VLSI, chip design, semiconductors, CMOS, FPGA, ASIC)
- Physics (quantum, optics, materials, condensed matter, particle physics)
- Mathematics (statistics, optimization, probability, numerical methods)
- Biology (genetics, genomics, molecular biology, cell biology)
- Medicine (clinical, medical, healthcare, pharmaceuticals)
- Economics (econometrics, finance, markets, trading)
- Mechanical Engineering (robotics, manufacturing, fluid dynamics, thermodynamics)
- Chemical Engineering (reactions, catalysts, polymers, process engineering)

Instructions:
1. Identify the PRIMARY domain(s) most relevant to this query
2. Consider secondary domains if the query is interdisciplinary
3. Return ONLY a JSON list of domain names, e.g. ["Computer Science", "Electrical Engineering"]

Response (JSON only):"""
    
    @classmethod
    def _parse_llm_response(cls, response: str, query: str) -> List[str]:
        """
        Parse LLM response to extract domain names
        Handles various response formats
        """
        domains = []
        
        # Try to extract JSON from response
        json_match = re.search(r'\[.*?\]', response, re.DOTALL)
        if json_match:
            try:
                domains = json.loads(json_match.group())
                if isinstance(domains, list):
                    return [d.strip() for d in domains if isinstance(d, str)]
            except json.JSONDecodeError:
                pass
        
        # Fallback: look for domain names in text
        domain_names = list(cls.DOMAIN_TO_CATEGORIES.keys())
        for domain in domain_names:
            if domain.lower() in response.lower():
                domains.append(domain)
        
        # If still no domains found, use keyword-based as fallback
        if not domains:
            logger.warning(f"Could not parse LLM response, using keyword fallback")
            return []
        
        return domains
    
    @classmethod
    def _domains_to_categories(cls, domains: List[str]) -> List[str]:
        """Convert domain names to ArXiv categories"""
        categories = set()
        
        for domain in domains:
            if domain in cls.DOMAIN_TO_CATEGORIES:
                categories.update(cls.DOMAIN_TO_CATEGORIES[domain])
        
        # If no categories found, fallback to keyword-based
        if not categories:
            return DomainDetector.detect_domains("")  # Will use all categories
        
        return sorted(list(categories))
    
    @classmethod
    def detect_with_api(cls, query: str, api_key: Optional[str] = None, api_type: str = "openai") -> List[str]:
        """
        Use external API (OpenAI, Anthropic, etc.) for domain detection
        
        Args:
            query: Search query
            api_key: API key for external service
            api_type: "openai" or "anthropic"
            
        Returns:
            List of ArXiv category codes
        """
        if not api_key:
            logger.warning("No API key provided, falling back to keyword-based detection")
            return DomainDetector.detect_domains(query)
        
        try:
            if api_type == "openai":
                return cls._openai_detection(query, api_key)
            elif api_type == "anthropic":
                return cls._anthropic_detection(query, api_key)
            else:
                logger.warning(f"Unknown API type: {api_type}, falling back")
                return DomainDetector.detect_domains(query)
        except Exception as e:
            logger.error(f"API domain detection failed: {e}, falling back to keyword-based")
            return DomainDetector.detect_domains(query)
    
    @classmethod
    def _openai_detection(cls, query: str, api_key: str) -> List[str]:
        """Use OpenAI API for domain detection"""
        try:
            import openai
            
            openai.api_key = api_key
            
            prompt = cls._create_prompt(query)
            
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",  # Fast and cheap
                messages=[
                    {"role": "system", "content": "You are an expert at categorizing academic research queries into domains. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=100
            )
            
            domains_text = response.choices[0].message.content
            domains = cls._parse_llm_response(domains_text, query)
            
            return cls._domains_to_categories(domains)
            
        except ImportError:
            logger.error("OpenAI library not installed. Install with: pip install openai")
            return DomainDetector.detect_domains(query)
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return DomainDetector.detect_domains(query)
    
    @classmethod
    def _anthropic_detection(cls, query: str, api_key: str) -> List[str]:
        """Use Anthropic Claude API for domain detection"""
        try:
            import anthropic
            
            client = anthropic.Anthropic(api_key=api_key)
            
            prompt = cls._create_prompt(query)
            
            message = client.messages.create(
                model="claude-3-haiku-20240307",  # Fast and cheap
                max_tokens=100,
                temperature=0.3,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            domains_text = message.content[0].text
            domains = cls._parse_llm_response(domains_text, query)
            
            return cls._domains_to_categories(domains)
            
        except ImportError:
            logger.error("Anthropic library not installed. Install with: pip install anthropic")
            return DomainDetector.detect_domains(query)
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            return DomainDetector.detect_domains(query)

