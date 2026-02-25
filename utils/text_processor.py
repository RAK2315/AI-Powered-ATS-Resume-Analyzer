"""
Text Processor Utility
Shared text preprocessing functionality used across all components.
"""

import re
from typing import Set


# Expanded stop words for professional context
PROFESSIONAL_STOP_WORDS = {
    'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
    'should', 'may', 'might', 'shall', 'can', 'this', 'that', 'these',
    'those', 'i', 'we', 'you', 'he', 'she', 'it', 'they', 'our', 'your',
    'their', 'my', 'his', 'her', 'its', 'not', 'no', 'as', 'if', 'so',
    'up', 'out', 'about', 'into', 'through', 'during', 'before', 'after',
    'above', 'below', 'between', 'each', 'all', 'both', 'few', 'more',
    'most', 'other', 'some', 'such', 'than', 'too', 'very', 'just',
    'also', 'well', 'even', 'back', 'any', 'good', 'new', 'first', 'last',
    'long', 'great', 'little', 'own', 'right', 'big', 'high', 'different',
    'small', 'large', 'next', 'early', 'young', 'important', 'public',
    'work', 'know', 'take', 'make', 'see', 'come', 'think', 'look',
    'want', 'give', 'use', 'find', 'tell', 'ask', 'seem', 'feel', 'try',
    'leave', 'call', 'keep', 'let', 'begin', 'show', 'hear', 'play',
    'run', 'move', 'live', 'believe', 'hold', 'bring', 'happen', 'write',
    'provide', 'sit', 'stand', 'lose', 'pay', 'meet', 'include', 'continue',
    'set', 'learn', 'change', 'lead', 'understand', 'watch', 'follow',
    'stop', 'create', 'speak', 'read', 'spend', 'grow', 'open', 'walk',
    'win', 'offer', 'remember', 'love', 'consider', 'appear', 'buy',
    'wait', 'serve', 'die', 'send', 'expect', 'build', 'stay', 'fall',
    'cut', 'reach', 'kill', 'remain', 'suggest', 'raise', 'pass', 'sell',
    'require', 'report', 'decide', 'pull', 'per', 'etc'
}


class TextProcessor:
    """Shared text preprocessing for all components."""

    def normalize(self, text: str) -> str:
        """Full normalization pipeline for analysis."""
        if not text:
            return ""
        text = text.lower()
        text = re.sub(r'[^\w\s\+\#\./]', ' ', text)  # keep tech chars
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        return text

    def tokenize(self, text: str) -> list:
        """Split text into meaningful tokens."""
        normalized = self.normalize(text)
        tokens = normalized.split()
        return [t for t in tokens if len(t) > 1 and t not in PROFESSIONAL_STOP_WORDS]

    def get_stop_words(self) -> Set[str]:
        """Return the stop word set."""
        return PROFESSIONAL_STOP_WORDS

    def remove_formatting_artifacts(self, text: str) -> str:
        """Remove common PDF and formatting artifacts."""
        # Remove page numbers
        text = re.sub(r'\n\s*\d+\s*\n', '\n', text)
        # Remove repeated dashes/lines
        text = re.sub(r'[-_=]{3,}', '', text)
        # Remove bullet variations
        text = re.sub(r'^[•●◦▪▸►\-\*]\s*', '', text, flags=re.MULTILINE)
        # Normalize whitespace
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    def extract_sentences(self, text: str) -> list:
        """Split text into sentences."""
        sentences = re.split(r'[.!?]\s+', text)
        return [s.strip() for s in sentences if len(s.strip()) > 10]
