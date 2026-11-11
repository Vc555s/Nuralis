"""
Smart Domain Detector - Analyzes queries and selects relevant ArXiv categories
"""
from typing import List, Set, Dict
import re
from src.utils.logging_utils import logger


class DomainDetector:
    """
    Detects relevant academic domains from query text
    Returns appropriate ArXiv categories for the query
    """
    
    # Domain keywords mapping to ArXiv categories
    DOMAIN_KEYWORDS = {
        # Computer Science
        'cs': {
            'keywords': [
                'machine learning', 'deep learning', 'neural network', 'ai', 'artificial intelligence',
                'computer vision', 'nlp', 'natural language', 'transformer', 'attention',
                'reinforcement learning', 'gan', 'cnn', 'rnn', 'lstm', 'bert', 'gpt',
                'algorithm', 'data structure', 'software', 'programming', 'code',
                'computer science', 'cs', 'ml', 'dl'
            ],
            'categories': ['cs.AI', 'cs.LG', 'cs.CL', 'cs.CV', 'cs.NE', 'cs.RO', 'cs.SE', 'cs.DS']
        },
        
        # Electrical Engineering & Electronics
        'eess': {
            'keywords': [
                'vlsi', 'very large scale integration', 'ic design', 'chip design',
                'circuit', 'electronics', 'electronic', 'semiconductor', 'cmos',
                'fpga', 'asic', 'digital design', 'analog design', 'mixed signal',
                'power electronics', 'power management', 'voltage', 'current',
                'signal processing', 'dsp', 'digital signal', 'audio processing',
                'image processing', 'video processing', 'communication', 'wireless',
                'rf', 'radio frequency', 'antenna', 'microwave', 'radar',
                'embedded system', 'microcontroller', 'sensor', 'actuator',
                'control system', 'automation', 'robotics hardware', 'iot device'
            ],
            'categories': [
                'eess.AS',  # Audio and Speech Processing
                'eess.IV',  # Image and Video Processing
                'eess.SP',  # Signal Processing
                'eess.SY',  # Systems and Control
                'cs.AR',    # Hardware Architecture
                'cs.ET',    # Emerging Technologies
                'physics.app-ph'  # Applied Physics (electronics)
            ]
        },
        
        # Physics
        'physics': {
            'keywords': [
                'physics', 'quantum', 'quantum computing', 'quantum mechanics',
                'optics', 'laser', 'photonics', 'electromagnetic', 'electromagnetism',
                'condensed matter', 'material science', 'nanotechnology', 'nano',
                'semiconductor physics', 'solid state', 'superconductor',
                'plasma', 'nuclear', 'particle', 'atomic', 'molecular'
            ],
            'categories': [
                'physics.app-ph', 'physics.comp-ph', 'physics.optics',
                'cond-mat.mtrl-sci', 'cond-mat.mes-hall', 'physics.quant-ph'
            ]
        },
        
        # Mathematics
        'math': {
            'keywords': [
                'mathematics', 'math', 'statistics', 'statistical', 'probability',
                'optimization', 'linear algebra', 'calculus', 'differential equation',
                'numerical', 'computation', 'algorithm theory', 'graph theory',
                'topology', 'geometry', 'number theory'
            ],
            'categories': ['math.NA', 'math.OC', 'math.ST', 'math.PR', 'stat.ML', 'stat.TH']
        },
        
        # Biology & Medicine
        'bio': {
            'keywords': [
                'biology', 'biological', 'genetics', 'genomics', 'protein', 'dna', 'rna',
                'cell', 'molecular', 'biochemistry', 'biomedical', 'medical',
                'medicine', 'clinical', 'health', 'disease', 'drug', 'pharmaceutical',
                'neuroscience', 'brain', 'neural', 'cognitive'
            ],
            'categories': [
                'q-bio.BM', 'q-bio.GN', 'q-bio.NC', 'q-bio.CB', 'q-bio.MN'
            ]
        },
        
        # Economics & Finance
        'econ': {
            'keywords': [
                'economics', 'economic', 'economy', 'finance', 'financial',
                'market', 'trading', 'investment', 'portfolio', 'risk',
                'econometrics', 'monetary', 'fiscal', 'banking'
            ],
            'categories': ['econ.EM', 'econ.TH', 'q-fin.EC', 'q-fin.MF']
        },
        
        # Mechanical Engineering
        'mechanical': {
            'keywords': [
                'mechanical', 'mechanics', 'robotics', 'robot', 'automation',
                'manufacturing', 'machining', 'fluid', 'thermodynamics', 'heat',
                'mechanical design', 'cad', 'cam', 'materials engineering'
            ],
            'categories': ['physics.flu-dyn', 'physics.class-ph', 'cond-mat.mtrl-sci']
        },
        
        # Chemical Engineering
        'chemical': {
            'keywords': [
                'chemical', 'chemistry', 'chemical engineering', 'reaction',
                'catalyst', 'polymer', 'materials chemistry', 'process engineering'
            ],
            'categories': ['physics.chem-ph', 'cond-mat.mtrl-sci']
        }
    }
    
    @classmethod
    def detect_domains(cls, query: str) -> List[str]:
        """
        Analyze query and return relevant ArXiv categories
        
        Args:
            query: Search query string
            
        Returns:
            List of ArXiv category codes
        """
        query_lower = query.lower()
        detected_categories = set()
        
        # Score each domain based on keyword matches
        domain_scores = {}
        
        for domain, info in cls.DOMAIN_KEYWORDS.items():
            score = 0
            matched_keywords = []
            
            for keyword in info['keywords']:
                # Whole-word match, tolerating a plural ("neural network" ~ "neural networks").
                # Multi-word keywords are more specific, so they weigh more than single words;
                # otherwise "graph neural networks" is claimed by biology via "neural".
                pattern = r'\b' + re.escape(keyword.lower()) + r's?\b'
                if re.search(pattern, query_lower):
                    score += 2 * len(keyword.split())
                    matched_keywords.append(keyword)
                elif keyword.lower() in query_lower:
                    score += 1  # Substring match
                    matched_keywords.append(keyword)
            
            if score > 0:
                domain_scores[domain] = {
                    'score': score,
                    'categories': info['categories'],
                    'matched': matched_keywords
                }
        
        # Select domains with score >= 2 (at least one exact match)
        # Or if no exact matches, use top scoring domain
        selected_domains = []
        
        if domain_scores:
            # Sort by score
            sorted_domains = sorted(domain_scores.items(), key=lambda x: x[1]['score'], reverse=True)
            
            # Always include top domain
            top_domain = sorted_domains[0]
            if top_domain[1]['score'] >= 1:
                selected_domains.append(top_domain[0])
                detected_categories.update(top_domain[1]['categories'])
                logger.info(f"🎯 Detected domain: {top_domain[0]} (score: {top_domain[1]['score']}, matched: {top_domain[1]['matched'][:3]})")
            
            # Include other domains with score >= 2
            for domain, info in sorted_domains[1:]:
                if info['score'] >= 2:
                    selected_domains.append(domain)
                    detected_categories.update(info['categories'])
                    logger.info(f"🎯 Detected domain: {domain} (score: {info['score']}, matched: {info['matched'][:3]})")
        
        # If no domain detected, use all categories (broad search)
        if not detected_categories:
            logger.warning(f"⚠️  No specific domain detected for query: '{query}'. Using all categories for broad search.")
            # Return all categories from all domains
            for info in cls.DOMAIN_KEYWORDS.values():
                detected_categories.update(info['categories'])
        
        categories_list = sorted(list(detected_categories))
        logger.info(f"📚 Selected {len(categories_list)} categories: {', '.join(categories_list[:5])}{'...' if len(categories_list) > 5 else ''}")
        
        return categories_list
    
    @classmethod
    def get_all_categories(cls) -> List[str]:
        """Get all available categories across all domains"""
        all_categories = set()
        for info in cls.DOMAIN_KEYWORDS.values():
            all_categories.update(info['categories'])
        return sorted(list(all_categories))
