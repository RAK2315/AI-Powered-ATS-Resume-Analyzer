"""
Score Calculator Component
Computes ATS compatibility scores using TF-IDF similarity.
"""

from dataclasses import dataclass
from typing import Tuple
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from utils.text_processor import TextProcessor


@dataclass
class ScoreMetrics:
    raw_similarity: float
    normalized_score: int
    technical_match: float
    keyword_density: float
    length_ratio: float


class ScoreCalculator:
    """Computes ATS compatibility scores using TF-IDF cosine similarity."""

    # Calibrated thresholds — resumes naturally have lower similarity than docs
    # Raw cosine similarity between resume & JD typically ranges 0.05–0.35
    # 0.10 = decent match, 0.20 = good match, 0.30+ = strong match
    LOW_THRESHOLD  = 0.05   # below this → below 40
    MID_THRESHOLD  = 0.12   # around here → 50-60
    HIGH_THRESHOLD = 0.22   # around here → 70-80
    TOP_THRESHOLD  = 0.32   # above this → 85+

    def __init__(self):
        self.text_processor = TextProcessor()
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            max_features=5000,
            stop_words='english',
            sublinear_tf=True
        )

    def calculate_similarity(self, resume_text: str, job_desc: str) -> float:
        """Calculate TF-IDF cosine similarity between resume and job description."""
        if not resume_text or not job_desc:
            return 0.0

        processed_resume = self.text_processor.normalize(resume_text)
        processed_job = self.text_processor.normalize(job_desc)

        try:
            tfidf_matrix = self.vectorizer.fit_transform([processed_resume, processed_job])
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            return float(similarity)
        except Exception:
            return 0.0

    def normalize_score(self, similarity: float) -> int:
        """Normalize raw similarity to 0-100 scale using calibrated thresholds.
        
        Typical resume vs JD similarity: 0.05-0.35
        A score of 0.10 is actually decent — old code wrongly gave this ~37/100.
        """
        if similarity <= self.LOW_THRESHOLD:
            # 0 – 0.05  →  0 – 35
            normalized = (similarity / self.LOW_THRESHOLD) * 35
        elif similarity <= self.MID_THRESHOLD:
            # 0.05 – 0.12  →  35 – 55
            normalized = 35 + ((similarity - self.LOW_THRESHOLD) /
                               (self.MID_THRESHOLD - self.LOW_THRESHOLD)) * 20
        elif similarity <= self.HIGH_THRESHOLD:
            # 0.12 – 0.22  →  55 – 75
            normalized = 55 + ((similarity - self.MID_THRESHOLD) /
                               (self.HIGH_THRESHOLD - self.MID_THRESHOLD)) * 20
        elif similarity <= self.TOP_THRESHOLD:
            # 0.22 – 0.32  →  75 – 90
            normalized = 75 + ((similarity - self.HIGH_THRESHOLD) /
                               (self.TOP_THRESHOLD - self.HIGH_THRESHOLD)) * 15
        else:
            # > 0.32  →  90 – 100
            normalized = 90 + min((similarity - self.TOP_THRESHOLD) / 0.1 * 10, 10)

        return min(100, max(0, int(round(normalized))))

    def get_detailed_metrics(self, resume_text: str, job_desc: str) -> ScoreMetrics:
        """Get detailed scoring metrics."""
        similarity = self.calculate_similarity(resume_text, job_desc)
        score = self.normalize_score(similarity)

        # Technical match: ratio of technical terms found
        resume_words = set(resume_text.lower().split())
        job_words = set(job_desc.lower().split())
        tech_terms = self._get_technical_terms(job_words)
        tech_match = len(tech_terms & resume_words) / max(len(tech_terms), 1)

        # Keyword density
        job_keywords = job_words - self.text_processor.get_stop_words()
        resume_words_lower = set(resume_text.lower().split())
        keyword_density = len(job_keywords & resume_words_lower) / max(len(job_keywords), 1)

        # Length ratio (resumes shouldn't be too short vs job desc)
        length_ratio = min(len(resume_text) / max(len(job_desc), 1), 3.0)

        return ScoreMetrics(
            raw_similarity=similarity,
            normalized_score=score,
            technical_match=round(tech_match, 3),
            keyword_density=round(keyword_density, 3),
            length_ratio=round(length_ratio, 3)
        )

    def _get_technical_terms(self, words: set) -> set:
        """Identify likely technical terms (no common English words)."""
        common = self.text_processor.get_stop_words()
        return {w for w in words if w not in common and len(w) > 3 and w.isalpha()}
