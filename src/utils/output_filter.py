"""
Output filtering utilities to clean AI-generated text
Removes unwanted formatting, extracts only actual analysis content
"""
import re
from typing import Optional


class OutputFilter:
    """Filter and clean AI-generated output"""
    
    # Patterns to remove unwanted content
    REMOVAL_PATTERNS = [
        r'^(System|User|Assistant|AI|Model):\s*',  # Remove role prefixes
        r'^\[.*?\]\s*',  # Remove markdown-style tags
        r'^#+\s*',  # Remove markdown headers
        r'^\*\s*',  # Remove markdown bullets
        r'^-\s*',  # Remove markdown dashes
        r'^•\s*',  # Remove bullet points
        r'```[\s\S]*?```',  # Remove code blocks
        r'`[^`]+`',  # Remove inline code
        r'\[.*?\]\(.*?\)',  # Remove markdown links
        r'<[^>]+>',  # Remove HTML tags
        r'^\d+\.\s*',  # Remove numbered lists
        r'Note:\s*.*?$',  # Remove "Note:" sections
        r'Important:\s*.*?$',  # Remove "Important:" sections
        r'Warning:\s*.*?$',  # Remove "Warning:" sections
    ]
    
    # Patterns to extract actual content
    EXTRACTION_PATTERNS = [
        r'(?:Paragraph\s*\d+[:]?\s*)?([A-Z][^.!?]*[.!?])',  # Extract sentences
        r'([A-Z][^.!?]*[.!?])',  # Extract complete sentences
    ]
    
    # Patterns to detect and remove instruction text
    INSTRUCTION_PATTERNS = [
        r'Write\s+(?:exactly\s+)?\d+\s+paragraphs?',
        r'Use\s+technical\s+language',
        r'Reference\s+specific\s+metrics',
        r'Avoid\s+exclamation\s+marks',
        r'Focus\s+on\s+quantitative\s+insights',
        r'Return\s+only\s+the\s+.*?paragraphs?',
        r'Without\s+headings?',
        r'Without\s+formatting',
        r'Requirements?:',
        r'Instructions?:',
        r'Dataset\s+Metrics?:',
        r'Tone:',
        r'Paragraph\s+\d+:',
    ]
    
    @staticmethod
    def clean_text(text: str) -> str:
        """
        Clean AI-generated text to extract only actual analysis
        
        Args:
            text: Raw AI output
            
        Returns:
            Cleaned text with only actual analysis content
        """
        if not text:
            return ""
        
        # Remove common unwanted patterns
        cleaned = text
        for pattern in OutputFilter.REMOVAL_PATTERNS:
            cleaned = re.sub(pattern, '', cleaned, flags=re.MULTILINE | re.IGNORECASE)
        
        # Remove instruction text
        for pattern in OutputFilter.INSTRUCTION_PATTERNS:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        # Extract sentences (actual content)
        sentences = []
        for pattern in OutputFilter.EXTRACTION_PATTERNS:
            matches = re.findall(pattern, cleaned)
            if matches:
                sentences.extend(matches)
                break
        
        # If extraction didn't work, use cleaned text directly
        if not sentences:
            # Split by sentences and filter
            sentences = re.split(r'[.!?]+\s+', cleaned)
            sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 20]
        
        # Filter out sentences that look like instructions
        filtered_sentences = []
        for sentence in sentences:
            # Skip if it's too short or looks like an instruction
            if len(sentence) < 20:
                continue
            if any(keyword in sentence.lower() for keyword in ['write', 'use', 'avoid', 'focus', 'return', 'paragraph']):
                continue
            if sentence.lower().startswith(('note:', 'important:', 'warning:', 'requirement')):
                continue
            filtered_sentences.append(sentence)
        
        # Join sentences
        result = ' '.join(filtered_sentences)
        
        # Final cleanup
        result = re.sub(r'\s+', ' ', result)  # Normalize whitespace
        result = re.sub(r'\.{2,}', '.', result)  # Remove multiple periods
        result = result.strip()
        
        # Ensure it ends with proper punctuation
        if result and not result[-1] in '.!?':
            result += '.'
        
        return result
    
    @staticmethod
    def extract_paragraphs(text: str, min_paragraphs: int = 2) -> list[str]:
        """
        Extract paragraphs from text, ensuring minimum count
        
        Args:
            text: Input text
            min_paragraphs: Minimum number of paragraphs to return
            
        Returns:
            List of paragraph strings
        """
        if not text:
            return []
        
        # Split by double newlines or periods followed by space and capital
        paragraphs = re.split(r'\n\n+|\.\s+(?=[A-Z])', text)
        paragraphs = [p.strip() for p in paragraphs if p.strip() and len(p.strip()) > 50]
        
        # If we don't have enough, split by single sentences
        if len(paragraphs) < min_paragraphs:
            sentences = re.split(r'[.!?]+\s+', text)
            sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 30]
            
            # Group sentences into paragraphs
            if sentences:
                sentences_per_para = max(1, len(sentences) // min_paragraphs)
                paragraphs = []
                for i in range(0, len(sentences), sentences_per_para):
                    para = ' '.join(sentences[i:i+sentences_per_para])
                    if para:
                        paragraphs.append(para)
        
        # Clean each paragraph
        cleaned_paragraphs = [OutputFilter.clean_text(p) for p in paragraphs[:min_paragraphs]]
        
        return [p for p in cleaned_paragraphs if p and len(p) > 50]

